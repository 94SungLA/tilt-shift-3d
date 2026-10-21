import json
from pathlib import Path
import os

def data_dir():
    path=Path(os.environ.get('TILTSHIFT_DATA_DIR', '.local')).resolve()
    path.mkdir(parents=True,exist_ok=True)
    return path

def read(name,default):
    try:
        value=json.loads((data_dir()/name).read_text())
        return value if isinstance(value,type(default)) else default
    except (OSError,ValueError): return default

def write(name,value):
    path=data_dir()/name; tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,indent=2)); tmp.replace(path)
