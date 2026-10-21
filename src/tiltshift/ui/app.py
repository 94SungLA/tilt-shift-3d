import math
import logging
import os
from pathlib import Path
import random
from time import monotonic
from direct.showbase.ShowBase import ShowBase
from direct.gui.DirectGui import DirectFrame, DirectButton, DirectLabel, DirectSlider
from panda3d.core import loadPrcFileData, TextNode, LineSegs, TransparencyAttrib, Fog, ClockObject, Filename, AudioSound
from tiltshift.game.core import Game, difficulty
from tiltshift.input.controller import Controller
from tiltshift.calibration.wizard import Calibration, stable_reference
from tiltshift.utils.storage import read,write
from tiltshift.ui.scene import cube,wall

CYAN=(.25,.95,1,1); MUTED=(.46,.56,.72,1); WHITE=(.9,.95,1,1)

class TiltShift(ShowBase):
    def __init__(self,args,buffer):
        loadPrcFileData('', 'window-title TiltShift 3D\nwin-size 1280 800\nsync-video true\nshow-frame-rate-meter false\naudio-library-name p3openal_audio')
        super().__init__(); self.disableMouse(); self.setBackgroundColor(.012,.017,.04)
        self.args=args; self.buffer=buffer; self.receiver=None
        self.bgm=None; self.bgm_muted=False
        self.start_music()
        self.sounds={}
        self.load_effects()
        self.profile=os.getenv('TILTSHIFT_PROFILE','phone-1'); self.axis=int(os.getenv('TILTSHIFT_NORMAL_AXIS','2'))
        if self.axis not in (0,1,2): raise ValueError('TILTSHIFT_NORMAL_AXIS must be 0, 1, or 2')
        self.controller=Controller(args.mode,buffer,self.axis)
        self.game=Game(args.seed,args.speed,args.interval)
        self.best=read('best.json',{}).get('score',0); self.calibrated=False
        self.nodes={}; self.widgets=[]; self.effects=[]; self.flash=0.; self.message_until=0.
        self.capture_start=None; self.cal_step=0; self.cal_upright=None
        self.smoke_started=monotonic(); self.smoke_stage=0; self.stale_pause=False
        self.camera.setPos(0,-12,0); self.camera.lookAt(0,16,0)
        self.camLens.setFov(62); self.camLens.setNearFar(.1,110)
        self.world=self.render.attachNewNode('world')
        from direct.filter.CommonFilters import CommonFilters
        self.filters=CommonFilters(self.win,self.cam)
        self.filters.setBloom(blend=(.25,.25,.25,0),mintrigger=.55,maxtrigger=1.0,desat=.15,intensity=.7,size='medium')
        self.environment()
        self.rod=self.world.attachNewNode('player rod')
        cube(self.rod,'core',(0,0,0),(3,.22,.22),(.25,.95,1,1))
        cube(self.rod,'highlight',(0,-.116,.065),(2.88,.012,.045),(.85,1,1,1))
        for thickness,alpha in ((.32,.12),(.44,.045)):
            halo=cube(self.rod,'halo',(0,0,0),(3.1,thickness,thickness),(.1,.9,1,alpha))
            halo.setTransparency(TransparencyAttrib.MAlpha); halo.setDepthWrite(False)
        for x in (-1.5,1.5): cube(self.rod,'cap',(x,0,0),(.08,.28,.28),(.7,.4,1,1))
        self.rod.setR(-90)
        self.hud=DirectLabel(parent=self.a2dTopLeft,text='',text_align=TextNode.ALeft,
                             pos=(.12,0,-.13),scale=.043,frameColor=(0,0,0,0),text_fg=WHITE)
        self.next_label=DirectLabel(parent=self.a2dTopRight,text='',text_align=TextNode.ARight,
                                   pos=(-.12,0,-.13),scale=.044,frameColor=(0,0,0,0),text_fg=CYAN)
        self.footer=DirectLabel(parent=self.a2dBottomCenter,text='',pos=(0,0,.09),scale=.031,
                               frameColor=(0,0,0,0),text_fg=MUTED)
        self.popup=DirectLabel(text='',pos=(0,0,.42),scale=.065,frameColor=(0,0,0,0),text_fg=CYAN)
        self.veil=DirectFrame(frameColor=(1,.12,.3,0),frameSize=(-2,2,-1,1))
        self.veil.setTransparency(TransparencyAttrib.MAlpha)
        for key in ('1','2','a','d','arrow_left','arrow_right'):
            self.accept(key,self.controller.key,[key])
            self.accept(key+'-repeat',self.controller.key,[key])
        self.accept('m',self.toggle_music)
        self.accept('space',self.space); self.accept('r',self.start)
        self.accept('escape',self.escape); self.accept('window-event',self.window_event)
        self.connect_if_needed(); self.load_calibration(); self.menu()
        self.taskMgr.add(self.frame,'tiltshift-frame')

    def start_music(self):
        root=Path(__file__).resolve().parents[3]
        if not (root/'bgm.mp3').is_file():
            root=Path(os.getenv('TILTSHIFT_ROOT',str(Path.cwd())))
        path=root/'bgm.mp3'
        if not path.is_file():
            logging.warning('Background music missing: %s',path)
            return
        self.bgm=self.loader.loadMusic(Filename.fromOsSpecific(str(path)))
        if self.bgm is None or self.bgm.status()==AudioSound.BAD:
            logging.warning('Could not load bgm.mp3; continuing without music')
            self.bgm=None
            return
        self.bgm.setLoop(True)
        self.bgm.setVolume(.3)
        self.bgm.play()
        logging.info('Background music loaded: %.1f seconds, looping at 30%% volume',self.bgm.length())

    def load_effects(self):
        root=Path(__file__).resolve().parents[3]
        if not (root/'success.mp3').is_file():
            root=Path(os.getenv('TILTSHIFT_ROOT',str(Path.cwd())))
        for name in ('success','fail'):
            path=root/(name+'.mp3')
            if not path.is_file():
                logging.warning('Sound effect missing: %s',path)
                continue
            sound=self.loader.loadSfx(Filename.fromOsSpecific(str(path)))
            if sound is None or sound.status()==AudioSound.BAD:
                logging.warning('Could not load %s.mp3',name)
                continue
            sound.setLoop(False)
            sound.setVolume(.7)
            self.sounds[name]=sound
            logging.info('Sound effect loaded: %s (%.2f seconds)',name,sound.length())

    def play_effect(self,name):
        sound=self.sounds.get(name)
        if sound:
            sound.stop()
            sound.play()
            if self.args.smoke: logging.info('Sound effect triggered: %s',name)

    def toggle_music(self):
        self.bgm_muted=not self.bgm_muted
        if self.bgm: self.bgm.setVolume(0 if self.bgm_muted else .3)
        self.toast('MUSIC OFF' if self.bgm_muted else 'MUSIC ON')

    def environment(self):
        fog=Fog('atmosphere'); fog.setColor(.012,.017,.04); fog.setExpDensity(.023); self.world.setFog(fog)
        cube(self.world,'floor',(0,28,-3.65),(20,90,.15),(.022,.035,.065,1))
        lines=LineSegs(); lines.setThickness(1)
        lines.setColor(.07,.27,.35,1)
        for x in range(-8,9): lines.moveTo(x,-8,-3.55); lines.drawTo(x,75,-3.55)
        for y in range(-8,76,3): lines.moveTo(-8,y,-3.55); lines.drawTo(8,y,-3.55)
        self.world.attachNewNode(lines.create())
        for y in range(0,77,6):
            for x in (-4.5,4.5):
                cube(self.world,'rail',(x,y,-3.5),(.035,5.8,.035),(.2,.45,.65,1))
                cube(self.world,'arch',(x,y,0),(.035,.06,7),(.12,.1,.28,1))
            cube(self.world,'roof',(0,y,3.5),(9,.06,.035),(.12,.1,.28,1))
        rng=random.Random(10)
        for _ in range(85):
            cube(self.world,'dust',(rng.uniform(-7,7),rng.uniform(4,75),rng.uniform(-3,4)),(.025,.025,.025),(.3,.48,.6,1))

    def connect_if_needed(self):
        if self.controller.mode=='iottalk' and self.receiver is None:
            from tiltshift.iottalk.receiver import Receiver
            self.receiver=Receiver(self.buffer); self.receiver.start()

    def calibration_key(self):
        # Include receiver identity, server, payload layout, profile and normal axis.
        identity=os.getenv('IOTTALK_DEVICE_ID') or read('device.json',{}).get('id','')
        return '|'.join([os.getenv('IOTTALK_SERVER','https://class.iottalk.tw'),identity,
                         self.profile,str(self.axis),os.getenv('TILTSHIFT_AXES','0,1,2')])

    def load_calibration(self):
        self.calibrated=False
        try:
            raw=read('calibration.json',{}).get(self.calibration_key())
            if raw:
                c=Calibration(**raw); self.controller.upright=c.upright; self.controller.flat=c.flat
                self.calibrated=True
        except (ValueError,TypeError): pass

    def clear_panel(self):
        for widget in self.widgets: widget.destroy()
        self.widgets=[]
        for attr in ('speed_slider','interval_slider'):
            if hasattr(self,attr): delattr(self,attr)

    def label(self,text,z,scale=.045,color=WHITE,parent=None):
        widget=DirectLabel(parent=parent or self.panel,text=text,pos=(0,0,z),scale=scale,
                           frameColor=(0,0,0,0),text_fg=color)
        return widget

    def panel_start(self,title,subtitle):
        self.clear_panel()
        self.panel=DirectFrame(frameColor=(.02,.035,.075,.97),frameSize=(-.7,.7,-.71,.75),pos=(-.68,0,0))
        self.widgets.append(self.panel)
        self.label('T I L T S H I F T   /   3 D',.58,.039,CYAN)
        self.label(title,.39,.085)
        self.label(subtitle,.23,.031,MUTED)
        self.label('ROTATE. ALIGN. SURVIVE.',-.59,.027,MUTED)

    def button(self,text,z,callback):
        return DirectButton(parent=self.panel,text=text,pos=(0,0,z),scale=.047,
                            frameSize=(-11,11,-.58,1.02),frameColor=(.065,.12,.19,1),
                            text_fg=WHITE,relief=1,command=callback,rolloverSound=None,clickSound=None)

    def menu(self):
        self.game.state='menu'; self.stale_pause=False; self.capture_start=None
        self.panel_start('Find your angle.', 'A phone, a glowing rod, an endless tunnel.')
        self.button('PLAY / SMARTPHONE',.06,self.phone_play)
        self.button('CALIBRATE PHONE',-.065,self.calibrate)
        self.button('KEYBOARD DEMO',-.19,self.keyboard_demo)
        self.button('SETTINGS',-.315,self.settings)
        self.button('QUIT',-.44,self.userExit)

    def phone_play(self):
        self.controller.mode='iottalk'; self.connect_if_needed(); self.load_calibration(); self.start()

    def keyboard_demo(self):
        self.controller.mode='keyboard'; self.start()

    def start(self):
        if self.controller.mode=='iottalk':
            self.connect_if_needed()
            if not self.calibrated: self.calibrate(); return
            if self.buffer.quality()[0]!='LIVE': self.toast('Waiting for fresh phone data'); return
        self.clear_panel(); self.game.start(); self.stale_pause=False
        self.capture_start=None; self.controller.angle=self.controller.target
        for node in self.nodes.values(): node.removeNode()
        self.nodes={}; self.toast('ALIGN WITH THE OPENING')

    def space(self):
        if self.game.state in ('menu','over'): self.start()
        elif self.game.state=='paused': self.resume()

    def escape(self):
        if self.game.state=='playing': self.pause()
        elif self.game.state=='paused': self.resume()
        else: self.menu()

    def pause(self):
        self.game.pause(); self.panel_start('Take a breath.', 'Gameplay is paused.')
        self.button('RESUME',.05,self.resume); self.button('RESTART',-.09,self.start)
        self.button('RECALIBRATE',-.23,self.calibrate); self.button('MAIN MENU',-.37,self.menu)

    def resume(self):
        if self.controller.mode=='iottalk' and self.buffer.quality()[0]!='LIVE':
            self.toast('Resume requires fresh smartphone data'); return
        self.stale_pause=False; self.clear_panel(); self.game.resume()

    def settings(self):
        self.game.state='settings'; self.panel_start('Your setup.', 'Session speed and obstacle spacing')
        self.label('Speed: default = progressive difficulty',.07,.033)
        self.speed_slider=DirectSlider(parent=self.panel,range=(2,9),value=self.game.speed_override or 4,
                                       pos=(0,0,-.02),scale=.48,command=self.change_settings)
        self.label('Spacing: minimum 2.6 seconds',-.16,.033)
        self.interval_slider=DirectSlider(parent=self.panel,range=(2.6,5),value=self.game.interval_override or 3.4,
                                          pos=(0,0,-.25),scale=.48,command=self.change_settings)
        self.button('RESET PROGRESSIVE DEFAULTS',-.38,self.reset_settings)
        self.button('BACK',-.49,self.menu)

    def change_settings(self):
        if hasattr(self,'speed_slider') and hasattr(self,'interval_slider'):
            self.game.speed_override=float(self.speed_slider['value'])
            self.game.interval_override=float(self.interval_slider['value'])

    def reset_settings(self):
        self.game.speed_override=None; self.game.interval_override=None; self.menu()

    def calibrate(self):
        self.controller.mode='iottalk'; self.connect_if_needed(); self.game.state='calibration'
        self.cal_step=0; self.capture_start=None; self.cal_page()

    def cal_page(self):
        self.panel_start('Meet your phone.', 'REAL SENSOR CALIBRATION / '+('01 UPRIGHT' if self.cal_step==0 else '02 FLAT'))
        instruction='Hold your phone upright\nin a comfortable position.' if self.cal_step==0 else 'Hold your phone flat,\nscreen facing up or down.'
        self.label(instruction,.01,.044)
        self.cal_status=self.label('Press collect, then hold steady for 2 seconds.',-.20,.028,MUTED)
        self.button('COLLECT POSE',-.34,self.collect); self.button('MAIN MENU',-.47,self.menu)

    def collect(self):
        if self.buffer.quality()[0]!='LIVE': self.toast('No recent real sensor data'); return
        self.capture_start=monotonic(); self.cal_status['text']='Collecting fresh samples...'

    def update_calibration(self,now):
        if self.capture_start is None: return
        samples=[s for s in self.buffer.snapshot() if s.received>=self.capture_start]
        self.cal_status['text']=f'Collected {len(samples)} samples / hold steady'
        if now-self.capture_start<2.2: return
        if len(samples)<8 and now-self.capture_start<4.5: return
        self.capture_start=None
        try:
            value=stable_reference(samples,now,self.axis)
            if self.cal_step==0:
                self.cal_upright=value; self.cal_step=1; self.cal_page()
            else:
                calibration=Calibration(self.cal_upright,value,self.profile,self.axis)
                all_profiles=read('calibration.json',{}); all_profiles[self.calibration_key()]=calibration.to_dict()
                write('calibration.json',all_profiles); self.load_calibration(); self.menu()
                self.toast('Calibration saved / Play with your phone')
        except ValueError as exc: self.cal_status['text']=str(exc)+'\nCollect again to retry.'

    def toast(self,text):
        self.popup['text']=text; self.message_until=monotonic()+2.1

    def particles(self,color):
        rng=random.Random(self.game.score)
        for _ in range(24):
            n=cube(self.world,'spark',(0,-.4,0),(.055,.055,.055),color)
            self.effects.append([n,(rng.uniform(-4,4),rng.uniform(-1,2),rng.uniform(-4,4)),.65])

    def game_over(self):
        if self.game.score>self.best:
            self.best=self.game.score
            if not self.args.smoke: write('best.json',{'score':self.best})
        self.flash=1.; self.particles((1,.2,.45,1))
        self.panel_start('Out of alignment.', f'FINAL {self.game.score:03d}     /     BEST {self.best:03d}')
        self.button('TRY AGAIN',.01,self.start); self.button('MAIN MENU',-.16,self.menu)
        self.button('QUIT',-.33,self.userExit)

    def window_event(self,window):
        if window and window.isClosed(): self.userExit()
        elif window and not self.args.smoke and not window.getProperties().getForeground() and self.game.state=='playing': self.pause()

    def frame(self,task):
        dt=ClockObject.getGlobalClock().getDt(); now=monotonic()
        # A stalled rendering frame pauses instead of burning the player's reaction window.
        if dt>.3 and not self.args.smoke and self.game.state=='playing': self.pause(); self.toast('Frame interrupted / press Space to resume')
        dt=min(dt,.1)
        old,angle=self.controller.update(dt,now); self.rod.setR(-angle)
        quality,age,hz=self.buffer.quality(now)
        if self.controller.mode=='iottalk' and quality in ('WAITING','STALE') and self.game.state=='playing':
            self.pause(); self.stale_pause=True; self.toast('Phone signal stale / reconnect, then Space')
        events=self.game.update(dt,old,angle)
        if 'pass' in events:
            self.toast('+1 / CLEAN PASS'); self.particles(CYAN)
            self.play_effect('success')
        if 'collision' in events:
            self.play_effect('fail')
            self.game_over()
        active={w.id for w in self.game.walls}
        for ident in list(self.nodes):
            if ident not in active and not (ident==-1 and self.game.state=='menu'): self.nodes.pop(ident).removeNode()
        for w in self.game.walls:
            if w.id not in self.nodes: self.nodes[w.id]=wall(self.world,w.vertical)
            self.nodes[w.id].setY(w.y)
        if not self.game.walls and self.game.state=='menu':
            if -1 not in self.nodes: self.nodes[-1]=wall(self.world,True)
            self.nodes[-1].setY(13+math.sin(task.time*.5)*1.5)
        label,speed,interval=difficulty(self.game.score)
        mode='KEYBOARD DEMO MODE' if self.controller.mode=='keyboard' else f'IOTTALK / {quality}'
        self.hud['text']=f'T I L T S H I F T\n\n{self.game.score:03d}   /   BEST {self.best:03d}\n{label}   /   {mode}'
        incoming=next((w for w in self.game.walls if not w.scored),None)
        opening=('UPRIGHT |' if incoming.vertical else 'FLAT --') if incoming else 'READY'
        self.next_label['text']=f'NEXT / {opening}\n\n{angle:04.1f} deg / {self.controller.confirmed}'
        if self.controller.mode=='keyboard': footer='1  UPRIGHT    2  FLAT    A / D  FINE ROTATION    SPACE  PLAY    ESC  PAUSE'
        else:
            transport=self.receiver.status if self.receiver else 'NOT STARTED'
            age_text=f'{age:.2f}s' if math.isfinite(age) else '--'
            footer=f'{transport} / {quality}    {hz:.1f} Hz    SAMPLE AGE {age_text}    Rejected {self.buffer.rejected}'
        self.footer['text']=footer+'    M  MUSIC '+('OFF' if self.bgm_muted else 'ON')
        if now>self.message_until: self.popup['text']=''
        self.flash=max(0,self.flash-dt*2); self.veil['frameColor']=(1,.12,.3,self.flash*.25)
        for effect in list(self.effects):
            node,velocity,life=effect; effect[2]-=dt
            node.setPos(node.getPos()+tuple_vec(velocity,dt))
            node.setScale(max(0,effect[2])*.08)
            if effect[2]<=0: node.removeNode(); self.effects.remove(effect)
        if self.game.state=='calibration': self.update_calibration(now)
        if self.args.smoke: self.smoke(now-self.smoke_started)
        return task.cont

    def smoke(self,t):
        if self.smoke_stage==0 and t>.5:
            Path('docs/screenshots').mkdir(parents=True,exist_ok=True)
            self.screenshot('docs/screenshots/menu.png',defaultFilename=False)
            self.keyboard_demo(); self.smoke_stage=1
        if self.game.state=='playing' and self.smoke_stage<3:
            incoming=next((w for w in self.game.walls if not w.scored),None)
            if incoming: self.messenger.send('1' if incoming.vertical else '2')
        if self.smoke_stage==1 and t>6:
            self.screenshot('docs/screenshots/gameplay.png',defaultFilename=False); self.smoke_stage=2
        if self.smoke_stage==2 and t>10:
            assert self.game.score>=1, 'Graphical pass did not score'
            incoming=next(w for w in self.game.walls if not w.scored)
            self.controller.angle=0 if incoming.vertical else 90
            self.controller.target=self.controller.angle; incoming.y=.4; self.smoke_stage=3
        if self.smoke_stage==3 and t>11:
            assert self.game.state=='over', 'Graphical mismatch did not collide'
            self.screenshot('docs/screenshots/game-over.png',defaultFilename=False)
            self.messenger.send('r'); assert self.game.score==0
            self.messenger.send('escape'); assert self.game.state=='paused'
            self.smoke_stage=4
        if self.smoke_stage==4 and t>12:
            self.screenshot('docs/screenshots/pause.png',defaultFilename=False)
            self.messenger.send('space'); assert self.game.state=='playing'
            self.settings(); self.smoke_stage=5
        if self.smoke_stage==5 and t>13:
            self.screenshot('docs/screenshots/settings.png',defaultFilename=False)
            self.reset_settings(); self.smoke_stage=6
        if t>14:
            assert self.game.state=='menu'
            print('GRAPHICAL SMOKE PASS: menu, keyboard rotation, pass + score, collision, restart, pause/resume, settings',flush=True)
            self.userExit()

    def userExit(self):
        if getattr(self,'bgm',None): self.bgm.stop()
        for sound in getattr(self,'sounds',{}).values(): sound.stop()
        if self.receiver: self.receiver.close()
        super().userExit()


def tuple_vec(velocity,dt):
    from panda3d.core import Vec3
    return Vec3(*(v*dt for v in velocity))
