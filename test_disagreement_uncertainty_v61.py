"""Synthetic check: no optical truth in disagreement predictors or gap bridges."""
import copy
import numpy as np
from disagreement_uncertainty_v61 import diagnostic_blocks


def main():
    t=np.arange(100)/100.; raw=np.zeros((100,18)); raw[:,3]=t; raw[:,9]=t
    raw[:,12]=8196*np.sin(t); raw[:,14]=8196
    data=dict(t=t,raw=raw,imu_valid=np.ones(100,bool),label_valid=np.ones(100,bool),gt_v=.1*t)
    row=dict(id='synthetic',participant='synthetic',condition='synthetic',setup='s')
    cal={'s':dict(terms=[dict(column=c,scale=.1,intercept=0) for c in (3,9,15)],accel_counts_per_g=[8196]*3,center_gravity_direction=[0,0,1])}
    model={'s':dict(mean=[0,0,0],std=[1,1,1],coef=[.1,0,0,0])}
    original=diagnostic_blocks(row,data,cal,model)
    altered=copy.deepcopy(data); altered['gt_v']+=999
    changed=diagnostic_blocks(row,altered,cal,model)
    np.testing.assert_equal([r['features'] for r in original],[r['features'] for r in changed])
    assert changed[0]['squared_error']>original[0]['squared_error']
    altered=copy.deepcopy(data); altered['imu_valid'][40:50]=False
    rows=diagnostic_blocks(row,altered,cal,model)
    assert all(not (r['start_s']<.5 and r['start_s']+.2>=.4) for r in rows)
    print('v61 truth-feature invariance and no-IMU-gap-bridge checks passed')


if __name__=='__main__':main()
