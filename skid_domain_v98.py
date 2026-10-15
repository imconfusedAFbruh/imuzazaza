"""Literal published weights on conditional sensor-only proxies; no prediction."""
import json
import numpy as np
import pipeline as p
from basin_completeness_v91 import verify
from native_projection_v80 import OUT as SENSOR
from fold_seedless_clock_v84 import OUT as MODELS
from audit_fold_routes_v59 import verified_json

OUT=p.ROOT/'outputs_skid_domain_v98'
DOC=p.ROOT/'research_docs/skid_source_domain_v97_v99.md'
RELATIVE_NEAR=1e-10


def literal_weights(right,left,dr,dl):
    speed=right+left;acceleration=dr+dl
    with np.errstate(divide='ignore',invalid='ignore',over='ignore'):
        s=right/speed;a=dl/acceleration
        denominator=s*a+(1-s)*(1-a);w=s*a/denominator
    finite=np.isfinite(w)&np.isfinite(s)&np.isfinite(a)
    w=np.where(finite,w,np.nan)
    speed_near=np.abs(speed)<=RELATIVE_NEAR*np.maximum(np.abs(right)+np.abs(left),np.finfo(float).tiny)
    accel_near=np.abs(acceleration)<=RELATIVE_NEAR*np.maximum(np.abs(dr)+np.abs(dl),np.finfo(float).tiny)
    third_near=np.abs(denominator)<=RELATIVE_NEAR*np.maximum(np.abs(s*a)+np.abs((1-s)*(1-a)),np.finfo(float).tiny)
    return dict(weight=w,finite=finite,outside=finite&((w<0)|(w>1)),speed_zero=speed==0,
        acceleration_zero=acceleration==0,third_zero=denominator==0,speed_near=speed_near,
        acceleration_near=accel_near,third_near=third_near,safe=finite&~speed_near&~accel_near&~third_near)


def main():
    assert not (p.ROOT/'research_state/STOP').exists()
    hashes=sum(verify(q) for q in (SENSOR,MODELS,p.ROOT/'outputs_skid_source_v97'))
    models=verified_json(MODELS,'models.json')
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    by_id={i:(fold,q) for fold,q in models.items() for i in q['held_ids']}
    assert len(by_id)==207
    for q in models.values():
        assert not set(q['fit_ids'])&set(q['held_ids'])
        assert not {inv[i]['participant'] for i in q['fit_ids']}&{inv[i]['participant'] for i in q['held_ids']}
    OUT.mkdir(exist_ok=False);(OUT/'profiles').mkdir()
    p.save_json(OUT/'protocol.json',dict(preregistration_sha256=p.digest(DOC),source_hashes_verified=hashes,
        nominal_gyro_dps_per_count=.070,nominal_radius_m=.30,relative_near=RELATIVE_NEAR,
        inputs='Full native sensor arrays; fold-only axis/sign/bias, never learned midpoint scales',
        source_method='literal Eq1-3 domain only; not faithful WhAG/trajectory reproduction',fitting=False,
        validation_accessed=False,test_accessed=False,promotion=False))
    rows=[];maximum=0.
    for n,(ident,(fold,q)) in enumerate(sorted(by_id.items()),1):
        r=inv[ident];assert r['partition']=='train'
        cal=q['calibration'][r['setup']]
        with np.load(SENSOR/'sensors'/(ident+'.npz')) as z:t,raw,valid=z['t'],z['raw'],z['imu_valid']
        wheels=[]
        for side,term in enumerate(cal['terms'][:2]):
            column=term['column'];assert column//6==side and column%6 in (3,4,5)
            bias=cal['gyro_bias_counts'][side][column%6-3]
            wheels.append((raw[:,column]-bias)*np.sign(term['scale'])*.070*np.pi/180*.30)
        left,right=wheels
        dr=np.r_[np.nan,np.diff(right)];dl=np.r_[np.nan,np.diff(left)]
        eligible=valid&np.r_[False,valid[:-1]]&np.isfinite(left)&np.isfinite(right)
        dr[~eligible]=np.nan;dl[~eligible]=np.nan
        result=literal_weights(right,left,dr,dl)
        safe=eligible&result['safe']
        with np.errstate(divide='ignore',invalid='ignore'):
            reduced=right*dl/(right*dl+left*dr)
        error=np.abs(reduced[safe]-result['weight'][safe])/np.maximum(1.,np.abs(result['weight'][safe]))
        if len(error):maximum=max(maximum,float(error.max()));assert np.all(error<1e-6)
        row=dict(id=ident,fold=fold,participant=r['participant'],maneuver=r['condition'],native_frames=len(t),eligible_frames=int(eligible.sum()),
            opposite_wheel_frames=int((eligible&(left*right<0)).sum()),opposite_derivative_frames=int((eligible&(dl*dr<0)).sum()),
            **{key+'_frames':int((eligible&value).sum()) for key,value in result.items() if key!='weight'},
            literal_algebra_max_relative_difference=float(error.max()) if len(error) else None)
        np.savez_compressed(OUT/'profiles'/(ident+'.npz'),t=t,left=left,right=right,dl=dl,dr=dr,eligible=eligible,**result)
        rows.append(row)
        if n%25==0:
            p.save_json(OUT/'progress.json',dict(completed=n,last_id=ident,source_sha256=p.digest(__file__)))
            print('v98',n,flush=True)
    assert sum(r['participant']=='No.20' for r in rows)==15
    p.write_csv(OUT/'trials.csv',rows)
    totals={key:sum(r[key] for r in rows) for key in rows[0] if key.endswith('_frames')}
    p.save_json(OUT/'run.json',dict(recordings=207,no20_records=15,totals=totals,max_literal_algebra_relative_difference=maximum,
        scope='Conditional nominal sensor proxies, not physical wheel measurements or accuracy metrics',promotion=False,validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
