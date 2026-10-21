"""Isolate official DAI network threads in a managed child process."""
import json
import logging
import os
from pathlib import Path
import signal
import subprocess
import sys
from threading import Thread, Lock
from uuid import uuid4
from tiltshift.utils.storage import read, write

SOURCE_ROOT=Path(__file__).resolve().parents[3]
ROOT=Path(os.environ.get('TILTSHIFT_ROOT', str(SOURCE_ROOT if (SOURCE_ROOT/'iottalk-reference').is_dir() else Path.cwd()))).resolve()

class Receiver:
    def __init__(self,buffer):
        self.buffer=buffer; self.process=None; self.lock=Lock()
        self.status='NOT STARTED'; self.name=None
        self.axes=tuple(int(x) for x in os.getenv('TILTSHIFT_AXES','0,1,2').split(','))
        if len(self.axes)!=3 or min(self.axes)<0: raise ValueError('TILTSHIFT_AXES requires 3 nonnegative indices')
    def start(self):
        if self.process is not None: return
        if not (ROOT/'iottalk-reference/DAI.py').is_file():
            raise RuntimeError('Official iottalk-reference/DAI.py is missing; run from a source checkout')
        env=os.environ.copy(); identity=read('device.json',{})
        device_id=env.get('IOTTALK_DEVICE_ID') or identity.get('id') or uuid4().hex
        write('device.json',{'id':device_id}); env['IOTTALK_DEVICE_ID']=device_id
        env['PYTHONPATH']=str(ROOT/'scripts')+os.pathsep+env.get('PYTHONPATH','')
        self.status='REGISTERING'
        self.process=subprocess.Popen([sys.executable,'-u',str(ROOT/'iottalk-reference/DAI.py'),'tiltshift_sa'],
                                      env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        self.reader=Thread(target=self._read,daemon=True); self.reader.start()
    def _read(self):
        for line in self.process.stdout:
            if not line.startswith('TILTSHIFT '):
                logging.info('Official DAI: %s',line.rstrip()); continue
            try:
                msg=json.loads(line[10:])
                if msg['kind']=='registered':
                    with self.lock: self.status='REGISTERED'; self.name=msg['name']
                elif msg['kind']=='sample':
                    if not self.buffer.put(msg['data'],self.axes,source_time=msg.get('source_time')):
                        logging.warning('Rejected malformed Dummy_Control payload')
                elif msg['kind']=='error': logging.error('SA callback: %s',msg['message'])
            except Exception: logging.exception('Invalid receiver event')
        with self.lock: self.status='STOPPED'
    def close(self):
        if self.process is None: return
        if self.process.poll() is None:
            self.process.send_signal(signal.SIGTERM)
            try: self.process.wait(timeout=2)
            except subprocess.TimeoutExpired: self.process.kill(); self.process.wait()
        self.reader.join(timeout=1)
