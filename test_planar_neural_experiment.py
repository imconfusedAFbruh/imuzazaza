import numpy as np
import torch
from planar_neural_experiment import PlanarResNet, predict_windows, body_pose, planar_loss
from planar_experiment import planar_features


def check():
    class Echo(torch.nn.Module):
        def forward(self,x): return x[:,:3]
    x=np.random.default_rng(42).normal(size=(777,28)).astype(np.float32)
    np.testing.assert_array_equal(predict_windows(Echo(),x,'cpu'),x[:,:3])
    motion=torch.zeros(1,3,100); motion[:,1]=1
    position,angle=body_pose(motion)
    torch.testing.assert_close(position[0,:,-1],torch.tensor([0.,.99])); assert not angle.any()
    turning=torch.zeros(1,3,101); turning[:,1]=1; turning[:,2]=np.pi/2
    curved,_=body_pose(turning)
    torch.testing.assert_close(curved[0,:,-1],torch.tensor([-2/np.pi,2/np.pi]),atol=1e-5,rtol=1e-5)
    model=PlanarResNet(); xx=torch.randn(2,28,512); pred=model(xx)
    target=torch.randn(2,3,512); base=torch.zeros_like(target); mask=torch.ones(2,512,dtype=torch.bool); scale=torch.ones(1,3,1)
    loss=planar_loss(pred,target,base,mask,scale); changed=target.clone(); changed[:,:,:128]=999; changed[:,:,384:]=-999
    torch.testing.assert_close(loss,planar_loss(pred,changed,base,mask,scale)); loss.backward()
    assert model.output.weight.grad.abs().sum()>0
    assert all(torch.isfinite(p.grad).all() for p in model.parameters() if p.grad is not None)
    class SensorOnly(dict):
        def __getitem__(self,key):
            if key.startswith('gt_') or key=='label_valid': raise AssertionError('Reference input in feature path')
            return super().__getitem__(key)
    calibration={'demo':dict(terms=[dict(column=3,scale=.1,intercept=0),dict(column=9,scale=.1,intercept=0),dict(column=17,scale=.1,intercept=0)],
        track_width_m=.52,wheel_radius_m=.3,accel_counts_per_g=[1,1,1],gyro_bias_counts=[[0,0,0]]*3,center_gravity_direction=[0,0,1])}
    data=SensorOnly(setup=np.array('demo'),raw=np.random.default_rng(42).normal(size=(100,18)))
    assert planar_features(data,np.zeros((100,2)),np.zeros((100,2)),calibration).shape==(100,28)
    print('Planar neural stitching, lateral rotation, context-label exclusion and backward checks passed')


if __name__=='__main__': check()
