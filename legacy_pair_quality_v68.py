"""Existing-data pairing and observed-marker support; never modifies training."""
import json
import numpy as np
import yaml
import pipeline as p

OUT = p.ROOT/'outputs_legacy_pair_quality_v68'


def quality(path):
    c=p.ezc3d.c3d(str(path)); point=c['parameters']['POINT']; labels=[s.strip() for s in point['LABELS']['value']]
    ids=[labels.index(s) for s in ('L_WC','R_WC') if s in labels]
    if len(ids)!=2: return dict(marker_pair_present=False,labels=labels)
    unit=point['UNITS']['value'][0].strip().lower()
    if unit not in ('mm','cm','m'): raise ValueError(unit)
    xyz=c['data']['points'][:3,ids,:].transpose(2,1,0)*dict(mm=.001,cm=.01,m=1.)[unit]
    residual=c['data']['meta_points']['residuals'][0,ids,:].T
    finite=np.isfinite(xyz).all(axis=(1,2)); strict=finite & (residual>0).all(axis=1)
    masks=c['data']['meta_points'].get('camera_masks')
    populated=False
    if masks is not None:
        support=np.asarray(masks)[:,ids,:].any(axis=0).T; populated=bool(support.any())
        if populated: strict &= support.all(axis=1)
    separation=np.linalg.norm(xyz[:,0]-xyz[:,1],axis=1)
    supported=separation[strict]
    return dict(marker_pair_present=True,labels=labels,frames=len(xyz),observed_frames=int(strict.sum()),
        observed_fraction=float(strict.mean()),zero_residual_pair_frames=int(((residual==0).all(axis=1)).sum()),
        camera_masks_populated=populated,hz=float(c['header']['points']['frame_rate']),
        observed_separation_median_m=float(np.median(supported)) if len(supported) else None,
        longest_observed_run_s=max((b-a for a,b in p.runs(strict)),default=0)/float(c['header']['points']['frame_rate']))


def main():
    OUT.mkdir(exist_ok=False)
    root=p.ROOT/'outdatedwithonly_2imu'; old=json.loads((p.ROOT/'outputs_two_imu_inventory_v65/inventory.json').read_text())
    for name,digest in old['file_hashes'].items(): assert p.digest(root/name)==digest, 'Legacy input changed'
    rows=[]
    for session in sorted(root.iterdir()):
        if not session.is_dir(): continue
        config=yaml.safe_load((session/'pairing.yaml').read_text())
        for pair in config['pairs']:
            imu=session/'imu'/pair['imu_dir']; name=pair.get('c3d',pair.get('c3d_archive',''))
            c3d=session/'c3d'/name
            # Pair paths are a declaration; unavailable archive paths remain missing.
            assert imu.resolve().is_relative_to(root.resolve()) and c3d.resolve().is_relative_to(root.resolve())
            row=dict(session=session.name,trial_id=pair['trial_id'],imu_directory=str(imu.relative_to(root)),
                c3d_declared=str(c3d.relative_to(root)),c3d_exists=c3d.is_file(),strict_training_eligible=False)
            for side in ('left','right'):
                path=imu/(side+'_raw.csv'); row[side+'_exists']=path.is_file()
                if path.is_file():
                    t=np.loadtxt(path,delimiter=',',skiprows=1,usecols=0)
                    dt=np.diff(t); positive=dt[dt>0]
                    row.update({side+'_samples':len(t),side+'_nonpositive_time_steps':int((dt<=0).sum()),
                        side+'_median_hz':float(1e6/np.median(positive)) if len(positive) else None,
                        side+'_duration_s':float((t[-1]-t[0])/1e6),side+'_max_step_ms':float(dt.max()/1000)})
            if c3d.is_file(): row.update(quality(c3d))
            rows.append(row)
    assert len(rows)==len(old['acquisitions']), 'Declared pair/metadata count differs'
    assert all(0 <= r.get('observed_fraction',0) <= 1 for r in rows)
    p.write_csv(OUT/'pairs.csv',rows)
    july=[r for r in rows if r['session']=='2026-07-31']
    supported=[r for r in july if r.get('observed_frames',0)>0 and r['left_exists'] and r['right_exists']]
    summary=dict(declared_pairs=len(rows),july_declared_pairs=len(july),july_available_c3d=sum(r['c3d_exists'] for r in july),
        july_two_imu_pairs_with_observed_markers=len(supported),july_observed_frames=sum(r['observed_frames'] for r in supported),
        strict_training_eligible=0,reason='Participant overlap, physical marker semantics, conversion and clock compatibility unresolved',
        training_modified=False,test_accessed=False,validation_accessed=False)
    p.save_json(OUT/'run.json',summary)
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print(json.dumps(summary,indent=2))


if __name__=='__main__': main()
