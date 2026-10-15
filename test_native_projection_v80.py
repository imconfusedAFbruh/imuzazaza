"""One runnable crop-invariance regression check; no optical inputs."""
import numpy as np
from projected_yaw_folds_v52 import proxy


def check(project):
    t=np.arange(1800)/100
    raw=np.zeros((len(t),18)); raw[:,12]=3000*np.sin(.6*t)
    raw[:,14]=8000; raw[:,15]=100*np.cos(t); raw[:,17]=50
    full=dict(t=t,raw=raw,imu_valid=np.ones(len(t),bool))
    cal=dict(center_gravity_direction=[0.,0.,1.],gyro_bias_counts=[[0.]*3]*3)
    expected=proxy(full,cal)
    for lo,hi in [(0,1800),(237,1432),(431,1799)]:
        actual,valid=project(full,cal,t[lo:hi])
        assert valid.all() and np.allclose(actual,expected[lo:hi],atol=1e-9,rtol=0), 'optical crop changed sensor projection'
    _,valid=project(full,cal,np.array([-1.,t[-1]+1]))
    assert not valid.any(), 'extrapolation must remain unsupported'
    gap=dict(full,imu_valid=full['imu_valid'].copy());gap['imu_valid'][600:610]=False
    _,valid=project(gap,cal,np.array([t[601],t[609]+.005,t[650]]))
    assert np.array_equal(valid,[False,False,True]), 'sensor gaps must stay unsupported'


if __name__=='__main__':
    import sys
    if '--legacy' in sys.argv:
        def legacy(full,cal,times):
            ix=np.searchsorted(full['t'],times)
            return proxy(dict(raw=full['raw'][ix],imu_valid=full['imu_valid'][ix]),cal),np.ones(len(ix),bool)
        check(legacy)
    else:
        from native_projection_v80 import sample_projection
        check(sample_projection)
        print('Native projection crop-invariance check passed')
