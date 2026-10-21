from dataclasses import dataclass, asdict
from statistics import mean, pstdev
from tiltshift.orientation.processing import alignment

@dataclass
class Calibration:
    upright: float
    flat: float
    profile: str
    axis: int
    def __post_init__(self):
        if not 0<=self.upright<=1 or not 0<=self.flat<=1 or self.flat-self.upright<.35:
            raise ValueError('Poses must be separated by at least 0.35; check normal axis')
        if self.axis not in (0,1,2): raise ValueError('Invalid normal axis')
    def to_dict(self): return asdict(self)


def stable_reference(samples,now,axis=2):
    if len(samples)<8: raise ValueError('Need at least 8 fresh samples (about 2 seconds)')
    if now-samples[-1].received>.65: raise ValueError('Sensor data is delayed')
    if samples[-1].received-samples[0].received<1.4: raise ValueError('Hold pose for at least 1.4 seconds')
    if now-samples[0].received>6: raise ValueError('Collection expired; hold pose and retry')
    values=[alignment(s.xyz,axis) for s in samples]
    if pstdev(values)>.065: raise ValueError('Phone moved; hold steady and retry')
    magnitudes=[sum(v*v for v in s.xyz)**.5 for s in samples]
    if any(not 5<m<15 for m in magnitudes) or pstdev(magnitudes)>1.2:
        raise ValueError('Expected stable acceleration including gravity in m/s²')
    return mean(values)
