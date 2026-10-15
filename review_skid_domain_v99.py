"""Independent arithmetic/source applicability checks, no new estimator."""
import csv,json
import numpy as np
import pipeline as p
from basin_completeness_v91 import verify
from skid_domain_v98 import OUT as DOMAIN,MODELS,SENSOR,DOC

OUT=p.ROOT/'outputs_skid_domain_review_v99'


def main():
    assert not (p.ROOT/'research_state/STOP').exists()
    hashes=sum(verify(q) for q in (DOMAIN,MODELS,SENSOR,p.ROOT/'outputs_skid_source_v97'))
    rows=list(csv.DictReader((DOMAIN/'trials.csv').open()));maximum=0.;checked=0;aggregate=[]
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    models=json.loads((MODELS/'models.json').read_text())
    for r in rows:
        ident=r['id'];q=models[r['fold']];meta=inv[ident]
        assert ident in q['held_ids'] and ident not in q['fit_ids'] and meta['partition']=='train'
        assert meta['participant']==r['participant'] and meta['condition']==r['maneuver']
        cal=q['calibration'][meta['setup']]
        with np.load(DOMAIN/'profiles'/(ident+'.npz')) as z:d={k:z[k] for k in z.files}
        with np.load(SENSOR/'sensors'/(ident+'.npz')) as z:t,raw,valid=z['t'],z['raw'],z['imu_valid']
        assert np.array_equal(d['t'],t)
        for side,name in ((0,'left'),(1,'right')):
            term=cal['terms'][side];column=term['column'];bias=cal['gyro_bias_counts'][side][column%6-3]
            rim=(raw[:,column]-bias)*(.070*np.pi*.30/180)*(1 if term['scale']>0 else -1)
            assert np.allclose(rim,d[name],rtol=1e-14,atol=1e-14)
        eligible=valid.copy();eligible[0]=False;eligible[1:] &=valid[:-1]
        assert np.array_equal(eligible,d['eligible'])
        left,right=d['left'],d['right'];dl,dr=d['dl'],d['dr']
        for a,delta in ((left,dl),(right,dr)):
            assert np.allclose(delta[1:][eligible[1:]],np.diff(a)[eligible[1:]],rtol=0,atol=0)
            assert np.isnan(delta[~eligible]).all()
        with np.errstate(divide='ignore',invalid='ignore'):
            s=np.divide(right,right+left);a=np.divide(dl,dr+dl)
            numerator=s*a;denominator=numerator+(1-s)*(1-a);w=np.divide(numerator,denominator)
        finite=np.isfinite(w)&np.isfinite(s)&np.isfinite(a)
        assert np.array_equal(finite,d['finite'])
        if finite.any():maximum=max(maximum,float(np.max(abs(w[finite]-d['weight'][finite]))))
        assert np.allclose(w[finite],d['weight'][finite],rtol=1e-12,atol=1e-12)
        assert np.isnan(d['weight'][~finite]).all()
        flags=dict(finite=finite,outside=finite&((w<0)|(w>1)),speed_zero=(right+left)==0,
            acceleration_zero=(dr+dl)==0,third_zero=denominator==0)
        for key,mask in flags.items():assert int((eligible&mask).sum())==int(r[key+'_frames']) and np.array_equal(mask,d[key])
        assert int(eligible.sum())==int(r['eligible_frames'])
        checked+=1
    assert checked==len({r['id'] for r in rows})==207 and sum(r['participant']=='No.20' for r in rows)==15
    totals=json.loads((DOMAIN/'run.json').read_text())['totals']
    for key,value in totals.items():assert value==sum(int(r[key]) for r in rows)
    for group in ('participant','maneuver'):
        for value in sorted({r[group] for r in rows}):
            rr=[r for r in rows if r[group]==value];n=sum(int(r['eligible_frames']) for r in rr)
            aggregate.append(dict(group=group,value=value,trials=len(rr),eligible_frames=n,
                undefined_pct=100*sum(int(r['eligible_frames'])-int(r['finite_frames']) for r in rr)/n,
                nonconvex_pct=100*sum(int(r['outside_frames']) for r in rr)/n))
    OUT.mkdir(exist_ok=False)
    p.write_csv(OUT/'domain_summary.csv',aggregate)
    p.save_json(OUT/'run.json',dict(parent_hashes_verified=hashes,recordings_checked=checked,no20=15,literal_weights_max_difference=maximum,
        native_frames=totals['native_frames'],eligible_frames=totals['eligible_frames'],undefined_frames=totals['eligible_frames']-totals['finite_frames'],
        nonconvex_frames=totals['outside_frames'],physical_WhAG_verified=False,faithful_reproduction=False,new_predictions=False,promotion=False,
        decision='No source-unspecified clipping/rectification/fallback; seek original wheel fusion/sign conventions',validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},
        source_sha256=p.digest(__file__),preregistration_sha256=p.digest(DOC)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
