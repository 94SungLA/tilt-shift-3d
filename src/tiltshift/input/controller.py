from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from tiltshift.orientation.processing import alignment, GravityFilter, target_angle, smooth

@dataclass(frozen=True)
class Sample:
    xyz: tuple
    received: float
    source_time: str | None = None


class LatestBuffer:
    def __init__(self):
        self.lock=Lock(); self.samples=deque(maxlen=128); self.rejected=0
    def put(self,payload,axes=(0,1,2),at=None,source_time=None):
        try:
            if not isinstance(payload,(tuple,list)): raise ValueError('Payload must be a list')
            if len(payload)==1 and isinstance(payload[0],(tuple,list)): payload=payload[0]
            xyz=tuple(payload[i] for i in axes); alignment(xyz)
            sample=Sample(xyz,monotonic() if at is None else at,source_time)
            with self.lock:
                if self.samples and sample.received<=self.samples[-1].received: raise ValueError('Out of order sample')
                self.samples.append(sample)
            return True
        except (ValueError,TypeError,IndexError,OverflowError):
            with self.lock: self.rejected+=1
            return False
    def snapshot(self):
        with self.lock: return tuple(self.samples)
    def quality(self,now=None):
        samples=self.snapshot(); now=monotonic() if now is None else now
        if not samples: return 'WAITING',float('inf'),0.
        age=max(0,now-samples[-1].received)
        recent=[s for s in samples if now-s.received<5]
        hz=(len(recent)-1)/(recent[-1].received-recent[0].received) if len(recent)>1 else 0.
        return ('STALE' if age>2 else 'DELAYED' if age>.65 else 'LIVE'),age,hz


class Controller:
    def __init__(self,mode,buffer,axis=2):
        self.mode=mode; self.buffer=buffer; self.filter=GravityFilter(axis)
        self.angle=90.; self.target=90.; self.confirmed='UPRIGHT'; self.candidate='UPRIGHT'; self.since=0.
        self.upright=0.; self.flat=1.; self.last=None
    def key(self,key):
        if self.mode!='keyboard': return
        if key=='1': self.target=90.
        elif key=='2': self.target=0.
        elif key in ('a','arrow_left'): self.target=min(90,self.target+8)
        elif key in ('d','arrow_right'): self.target=max(0,self.target-8)
    def update(self,dt,now=None):
        now=monotonic() if now is None else now
        if self.mode=='iottalk':
            samples=self.buffer.snapshot()
            for sample in samples:
                if self.last is None or sample.received>self.last:
                    value=self.filter.feed(sample.xyz,sample.received)
                    self.target=target_angle(value,self.upright,self.flat); self.last=sample.received
        old=self.angle; self.angle=smooth(self.angle,self.target,dt)
        candidate='UPRIGHT' if self.target>65 else 'FLAT' if self.target<25 else 'TILTING'
        if candidate!=self.candidate: self.candidate=candidate; self.since=now
        if now-self.since>=.3: self.confirmed=candidate
        return old,self.angle
