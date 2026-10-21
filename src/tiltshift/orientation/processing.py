from math import isfinite, sqrt, exp


def alignment(xyz, normal_axis=2):
    if len(xyz)!=3 or normal_axis not in (0,1,2): raise ValueError('Expected 3 axes and normal axis 0..2')
    if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v) for v in xyz):
        raise ValueError('Acceleration must be finite numbers')
    magnitude=sqrt(sum(v*v for v in xyz))
    if not .5 <= magnitude <= 40: raise ValueError('Implausible gravity magnitude; use m/s² including gravity')
    return abs(xyz[normal_axis])/magnitude


def target_angle(value, upright=0., flat=1.):
    if flat-upright<.35: raise ValueError('Calibration poses too close')
    return 90*(1-max(0.,min(1.,(value-upright)/(flat-upright))))


def smooth(current,target,dt,tau=.14):
    return current+(target-current)*(1-exp(-max(0,dt)/tau))


class GravityFilter:
    def __init__(self,axis=2): self.axis=axis; self.value=None; self.at=None
    def feed(self,xyz,at):
        value=alignment(xyz,self.axis)
        if self.at is not None and at<=self.at: raise ValueError('Non-monotonic sensor receive time')
        # Filter normalized gravity alignment, preserving screen-up/down equivalence.
        self.value=value if self.at is None or at-self.at>2 else smooth(self.value,value,at-self.at,.22)
        self.at=at
        return self.value
