import argparse
import logging
import os
from pathlib import Path


def load_env():
    path=Path('.env')
    if path.is_file():
        for line in path.read_text().splitlines():
            line=line.strip()
            if line and not line.startswith('#') and '=' in line:
                key,value=line.split('=',1); os.environ.setdefault(key.strip(),value.strip().strip('"\''))


def main():
    load_env()
    parser=argparse.ArgumentParser(description='TiltShift 3D — Smartphone-controlled survival arcade')
    parser.add_argument('--mode',choices=['keyboard','iottalk'],default='keyboard')
    parser.add_argument('--seed',type=int)
    parser.add_argument('--speed',type=float)
    parser.add_argument('--interval',type=float)
    parser.add_argument('--smoke',action='store_true',help='Scripted 14-second graphical check; keyboard only')
    parser.add_argument('--diagnose',type=float,metavar='SECONDS',help='Receive real IoTtalk data without rendering')
    args=parser.parse_args()
    if args.speed is not None and not .5<=args.speed<=12: parser.error('--speed must be 0.5..12')
    if args.interval is not None and args.interval<2.6: parser.error('--interval must be at least 2.6 seconds')
    if args.smoke and args.mode!='keyboard': parser.error('--smoke uses explicit keyboard demo input only')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(levelname)s %(message)s')
    try:
        from tiltshift.input.controller import LatestBuffer
        buffer=LatestBuffer()
        if args.diagnose is not None:
            if not 1<=args.diagnose<=3600: parser.error('--diagnose must be 1..3600 seconds')
            from tiltshift.iottalk.receiver import Receiver
            import time
            receiver=Receiver(buffer); receiver.start(); deadline=time.monotonic()+args.diagnose; last=None
            try:
                while time.monotonic()<deadline:
                    samples=buffer.snapshot()
                    if samples and samples[-1]!=last:
                        last=samples[-1]
                        print(f'REAL RECEIVER xyz={last.xyz} source={last.source_time} quality={buffer.quality()}',flush=True)
                    time.sleep(.1)
            finally: receiver.close()
            print(f'Valid samples={len(buffer.snapshot())}; rejected={buffer.rejected}')
        else:
            from tiltshift.ui.app import TiltShift
            TiltShift(args,buffer).run()
    except KeyboardInterrupt: pass
    except (ImportError,ValueError,RuntimeError,OSError) as exc:
        parser.exit(1,f'TiltShift: {exc}\nInstall with: .venv/bin/python -m pip install -e ".[dev]"\n')

if __name__=='__main__': main()
