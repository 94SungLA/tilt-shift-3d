import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from direct.showbase.ShowBase import ShowBase
from panda3d.core import loadPrcFileData
from tiltshift.ui.scene import cube, wall
loadPrcFileData('', 'window-title TiltShift 3D - Rendering smoke test\nwin-size 1000 700\naudio-library-name null')
app = ShowBase(); app.disableMouse(); app.setBackgroundColor(.015,.02,.06)
app.camera.setPos(0,-12,2); app.camera.lookAt(0,10,0)
rod = cube(app.render,'rod',(0,0,0),(3,.22,.22),(.1,1,1,1))
gate = wall(app.render, True); gate.setY(16)
def frame(task):
    rod.setR(task.time*30); gate.setY(16-task.time*2)
    if task.time > 4:
        Path('docs/screenshots').mkdir(parents=True, exist_ok=True)
        app.screenshot('docs/screenshots/smoke.png', defaultFilename=False)
        app.userExit(); return task.done
    return task.cont
app.taskMgr.add(frame,'smoke'); app.run()
