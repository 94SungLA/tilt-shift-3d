"""Custom SA loaded by the unmodified official DAI.py; no sensor publisher."""
import json
import os
import signal
import sys

ServerURL=os.getenv('IOTTALK_SERVER','https://class.iottalk.tw')
device_model=os.getenv('IOTTALK_MODEL','Dummy_Device')
device_name=os.getenv('IOTTALK_DEVICE_NAME','TiltShift-3D')
device_id=os.environ['IOTTALK_DEVICE_ID']
IDF_list=[]
ODF_list=[os.getenv('IOTTALK_ODF','Dummy_Control')]
exec_interval=.1
MQTT_broker=None

def emit(kind,**fields):
    print('TILTSHIFT '+json.dumps({'kind':kind,**fields}),flush=True)

def receive(data):
    try:
        import DAN
        emit('sample',data=data,source_time=DAN.timestamp.get(ODF_list[0]))
    except Exception as exc:
        emit('error',message=str(exc))

globals()[ODF_list[0].replace('-','_')]=receive

def on_register(result): emit('registered',name=result['d_name'],server=result['server'])

def stop(signum,frame):
    # Official deregistration uses an unbounded delete; parent has a shutdown deadline.
    try:
        import DAN
        DAN.deregister()
    finally: sys.exit(0)

signal.signal(signal.SIGINT,stop)
signal.signal(signal.SIGTERM,stop)
