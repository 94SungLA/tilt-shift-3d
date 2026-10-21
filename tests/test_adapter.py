"""Synthetic adapter tests, deliberately distinct from real-phone evidence."""
import importlib.util
import json
from pathlib import Path
import signal
import sys
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from tiltshift.input.controller import LatestBuffer
from tiltshift.utils.storage import read,write


def test_official_custom_sa_callback(monkeypatch,capsys):
    monkeypatch.setenv('IOTTALK_DEVICE_ID','test-only-device')
    monkeypatch.setenv('IOTTALK_ODF','Dummy-Control')
    monkeypatch.setitem(sys.modules,'DAN',SimpleNamespace(timestamp={'Dummy-Control':'recorded-source-time'}))
    path=Path(__file__).resolve().parents[1]/'scripts/tiltshift_sa.py'
    spec=importlib.util.spec_from_file_location('test_sa',path); sa=importlib.util.module_from_spec(spec)
    saved={s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    try:
        spec.loader.exec_module(sa)
        assert sa.IDF_list==[]; assert sa.ODF_list==['Dummy-Control']
        sa.Dummy_Control([[0,0,9.81]])
        sa.on_register({'d_name':'test-receiver','server':'https://test.invalid'})
        events=[json.loads(line[10:]) for line in capsys.readouterr().out.splitlines()]
        assert events[0]=={'kind':'sample','data':[[0,0,9.81]],'source_time':'recorded-source-time'}
        assert events[1]['kind']=='registered'
    finally:
        for s,handler in saved.items(): signal.signal(s,handler)


def test_concurrent_latest_buffer():
    b=LatestBuffer()
    def producer():
        for _ in range(1000): b.put([0,9.81,0])
    def consumer():
        for _ in range(1000):
            samples=b.snapshot()
            assert len(samples)<=128
            assert all(a.received<b.received for a,b in zip(samples,samples[1:]))
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(producer),pool.submit(consumer)]
        for job in jobs: job.result()
    assert len(b.snapshot())==128


def test_atomic_local_storage(tmp_path,monkeypatch):
    monkeypatch.setenv('TILTSHIFT_DATA_DIR',str(tmp_path))
    write('best.json',{'score':9}); assert read('best.json',{})=={'score':9}
    (tmp_path/'best.json').write_text('broken'); assert read('best.json',{})=={}
    (tmp_path/'best.json').write_text('[]'); assert read('best.json',{})=={}
