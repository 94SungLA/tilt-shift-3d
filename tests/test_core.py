import math
import pytest
from tiltshift.game.core import Wall, fits, extents, crossing, swept_fits, Game, difficulty
from tiltshift.orientation.processing import alignment, target_angle, smooth, GravityFilter
from tiltshift.input.controller import LatestBuffer, Controller, Sample
from tiltshift.calibration.wizard import Calibration,stable_reference

@pytest.mark.parametrize('xyz,result',[((0,9.81,0),0),((9.81,0,0),0),((0,0,9.81),1),((0,0,-9.81),1),((0,7,7),2**-.5)])
def test_alignment(xyz,result): assert alignment(xyz)==pytest.approx(result)

@pytest.mark.parametrize('xyz',[(0,0,0),(math.nan,0,9),(0,0,math.inf),('9',0,0),(True,0,9),(100,0,0)])
def test_invalid(xyz):
    with pytest.raises(ValueError): alignment(xyz)

def test_normal_axis(): assert alignment((9.81,0,0),0)==1

def test_in_plane_independence(): assert alignment((7,7,0))==alignment((0,9.81,0))

@pytest.mark.parametrize('value,angle',[(0,90),(1,0),(.5,45),(-1,90),(2,0)])
def test_mapping(value,angle): assert target_angle(value)==angle

def test_filter_time_aware():
    a=smooth(0,90,.2); b=smooth(smooth(0,90,.1),90,.1)
    assert a==pytest.approx(b)

def test_filter_slow_input():
    f=GravityFilter(); assert f.feed((0,9.81,0),0)==0
    assert 0<f.feed((0,0,9.81),.25)<1
    assert f.feed((0,0,-9.81),3)==1

def samples(xyz): return [Sample(xyz,i*.25) for i in range(9)]

def test_stable_calibration(): assert stable_reference(samples((0,9.81,0)),2.1)==0

@pytest.mark.parametrize('kind',['short','stale','moving','units'])
def test_bad_calibration(kind):
    s=samples((0,9.81,0)); now=2.1
    if kind=='short': s=s[:2]
    if kind=='stale': now=4
    if kind=='moving': s=[Sample((0,0,9.81) if i%2 else (0,9.81,0),i*.25) for i in range(9)]
    if kind=='units': s=samples((0,1,0))
    with pytest.raises(ValueError): stable_reference(s,now)

def test_separation():
    with pytest.raises(ValueError): Calibration(.4,.6,'phone',2)
    assert Calibration(.1,.9,'phone',2).flat==.9

def test_buffer_bounded_and_stale():
    b=LatestBuffer()
    for i in range(200): assert b.put([0,9.81,0],at=i*.25)
    assert len(b.snapshot())==128
    assert b.quality(49.8)[0]=='LIVE'; assert b.quality(50.5)[0]=='DELAYED'
    assert b.quality(52)[0]=='STALE'; assert b.quality(49.8)[2]==pytest.approx(4)
    assert not b.put([0],at=53); assert b.rejected==1

def test_nested_join_payload():
    b=LatestBuffer(); assert b.put([[1,2,9]],at=0)
    assert b.snapshot()[-1].xyz==(1,2,9)

def test_malformed_and_reordered():
    b=LatestBuffer(); assert b.quality(0)[0]=='WAITING'
    assert not b.put('oops'); assert not b.put([0,0,0])
    assert b.put([0,9,0],at=3); assert not b.put([0,9,0],at=2)

def test_keyboard():
    c=Controller('keyboard',LatestBuffer()); c.key('2'); c.update(.5,1)
    assert c.angle<3
    c.key('1'); c.update(.5,2); assert c.angle>87
    c.key('d'); assert c.target==82

def test_phone_independent_and_real():
    b=LatestBuffer(); c=Controller('iottalk',b); c.key('2'); assert c.target==90
    b.put([0,0,-9.81],at=0); c.update(.2,.2); assert c.target==0
    assert len(b.snapshot())==1

def test_dimensions():
    assert extents(0)==pytest.approx((3,.22)); assert extents(90)==pytest.approx((.22,3))

@pytest.mark.parametrize('angle,vertical,result',[(90,True,True),(0,False,True),(0,True,False),(90,False,False),(45,True,False),(45,False,False),(80,True,True),(10,False,True)])
def test_geometry(angle,vertical,result): assert fits(angle,vertical)==result

def test_swept_and_score_once():
    w=Wall(1,True)
    assert crossing(w,15,-15,90,90)=='pass'
    assert crossing(w,-15,-30,90,90)=='none'
    assert crossing(Wall(2,False),15,-15,90,90)=='collision'

def test_rotating_inside_wall():
    assert crossing(Wall(0,True),.2,-.2,90,0)=='collision'
    assert not swept_fits(0,180,False)
    assert crossing(Wall(0,True),1,.5,0,0)=='none'

def test_difficulty():
    assert [difficulty(i)[0] for i in (0,5,15)]==['EASY','NORMAL','HARD']
    assert min(difficulty(i)[2] for i in range(30))>=2.6

def test_game_transitions():
    g=Game(1); assert g.state=='menu'; g.start(); g.pause()
    assert not g.update(5,0,0); assert g.elapsed==0
    g.resume(); g.update(.1,90,90); assert len(g.walls)==1
    g.update(8,0 if g.walls[0].vertical else 90,0 if g.walls[0].vertical else 90)
    assert g.state=='over'; g.start(); assert g.score==0 and g.state=='playing'

def test_deterministic_schedule():
    a,b=Game(3),Game(3); a.start(); b.start()
    for _ in range(400): a.update(.01,90,90)
    for _ in range(40): b.update(.1,90,90)
    assert [w.vertical for w in a.walls]==[w.vertical for w in b.walls]
    assert [w.y for w in a.walls]==pytest.approx([w.y for w in b.walls],abs=.04)

def test_successful_game():
    g=Game(2); g.start(); angle=90
    for _ in range(1600):
        next_wall=next((w for w in g.walls if not w.scored),None)
        angle=90 if next_wall is None or next_wall.vertical else 0
        g.update(.01,angle,angle)
    assert g.score>=3 and g.state=='playing'


def test_recorded_real_phone_axes_and_calibration():
    """Replay a cropped real feed with relative receive times, not a live calibration."""
    import json
    from pathlib import Path
    recorded=json.loads((Path(__file__).parent/'fixtures/phone_92_recorded.json').read_text())
    references=[]
    for pose in ('upright','flat'):
        data=[Sample(tuple(row['xyz']),i*.36) for i,row in enumerate(recorded[pose])]
        references.append(stable_reference(data,data[-1].received+.03))
    calibration=Calibration(*references,'recorded-92',2)
    assert calibration.upright<.15 and calibration.flat>.95
    assert target_angle(calibration.upright,*references)==90
    assert target_angle(calibration.flat,*references)==0
