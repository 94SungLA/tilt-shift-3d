"""Headless geometry and deterministic simulation; X right, Y depth, Z up."""
from dataclasses import dataclass
from math import sin, cos, radians, pi, atan2
import random

ROD_LENGTH, ROD_THICKNESS, ROD_DEPTH = 3.0, .22, .22
WALL_DEPTH = .55


def extents(angle):
    a = radians(angle)
    return (ROD_LENGTH*abs(cos(a))+ROD_THICKNESS*abs(sin(a)),
            ROD_LENGTH*abs(sin(a))+ROD_THICKNESS*abs(cos(a)))


def fits(angle, vertical, tolerance=.025):
    w, h = (.9,3.6) if vertical else (3.6,.9)
    x, z = extents(angle)
    return x <= w+tolerance and z <= h+tolerance


def swept_fits(a, b, vertical):
    """Exact extrema of each projected extent over a linear angular interval."""
    lo, hi = sorted((a,b))
    critical = [lo,hi]
    alpha = atan2(ROD_THICKNESS, ROD_LENGTH)*180/pi
    for turn in range(int(lo//90)-2, int(hi//90)+3):
        for delta in (0,alpha,90-alpha):
            t = turn*90+delta
            if lo <= t <= hi: critical.append(t)
    return all(fits(t,vertical) for t in critical)


@dataclass
class Wall:
    id: int
    vertical: bool
    y: float = 32
    scored: bool = False


def crossing(wall, old_y, new_y, old_angle, new_angle):
    half = (WALL_DEPTH+ROD_DEPTH)/2
    if old_y < -half or new_y > half: return 'none'
    movement = old_y-new_y
    if movement <= 0: return 'none'
    enter = max(0., min(1., (old_y-half)/movement))
    leave = max(0., min(1., (old_y+half)/movement))
    a = old_angle+(new_angle-old_angle)*enter
    b = old_angle+(new_angle-old_angle)*leave
    if not swept_fits(a,b,wall.vertical): return 'collision'
    if new_y < -half and not wall.scored:
        wall.scored = True
        return 'pass'
    return 'none'


def difficulty(score):
    return ('EASY',4.,3.4) if score < 5 else (('NORMAL',5.5,3.) if score < 15 else ('HARD',7.,2.6))


class Game:
    def __init__(self, seed=None, speed=None, interval=None):
        self.seed, self.speed_override, self.interval_override = seed,speed,interval
        self.state = 'menu'; self.walls=[]; self.score=0

    def start(self):
        self.rng=random.Random(self.seed); self.walls=[]; self.score=0
        self.elapsed=0.; self.until_spawn=0.; self.next_id=0; self.state='playing'
        self.last_vertical=False

    def pause(self):
        if self.state=='playing': self.state='paused'

    def resume(self):
        if self.state=='paused': self.state='playing'

    def update(self, dt, old_angle, angle):
        if self.state!='playing': return []
        events=[]
        # Fixed small time slices keep obstacle scheduling independent of render rate.
        remaining=dt; progressed=0.
        while remaining>1e-9 and self.state=='playing':
            step=min(remaining,1/120); remaining-=step
            label,speed,interval=difficulty(self.score)
            speed=self.speed_override or speed; interval=self.interval_override or interval
            self.until_spawn-=step
            if self.until_spawn<=0:
                vertical=self.rng.choice([True,False]) if label=='EASY' else not self.last_vertical
                self.last_vertical=vertical
                self.walls.append(Wall(self.next_id,vertical)); self.next_id+=1
                self.until_spawn+=interval
            a=old_angle+(angle-old_angle)*(progressed/dt)
            progressed+=step
            b=old_angle+(angle-old_angle)*(progressed/dt)
            for wall in self.walls:
                old=wall.y; wall.y-=speed*step
                result=crossing(wall,old,wall.y,a,b)
                if result=='collision': self.state='over'; events.append('collision'); break
                if result=='pass': self.score+=1; events.append('pass')
            self.walls=[w for w in self.walls if w.y>-9]
            self.elapsed+=step
        return events
