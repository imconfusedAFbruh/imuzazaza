"""Rescore sealed historical predictions, no training or candidate selection."""
import csv
import json
import numpy as np
import pipeline as p
from audit_fold_routes_v59 import verified_json

OUT=p.ROOT/'outputs_headline_reproduction_v69'


def main():
    OUT.mkdir(exist_ok=False)
    source=p.ROOT/'outputs_clock_arbitrated_v42'
    run=verified_json(source,'run.json'); manifest=json.loads((source/'artifact_manifest.json').read_text())['sha256']
    expected=list(csv.DictReader((source/'common_native_trials.csv').open()))
    settings=json.loads((p.ROOT/'outputs_observed_reference_v7/run.json').read_text())['settings']
    rows=[]; maximum=0.; support_difference=0
    for ident in sorted({r['id'] for r in expected}):
        path=source/'common_trajectories'/(ident+'.npz')
        assert p.digest(path)==manifest[str(path.relative_to(source))]
        with np.load(path) as z:
            d=dict(gt_xy=z['reference_xy_m'],gt_heading=z['reference_heading_rad'],gt_valid=z['reference_valid'])
            for old in [r for r in expected if r['id']==ident]:
                method=old['method']; metric=p.metrics(d,z[method+'_xy_m'],z[method+'_heading_rad'],settings)
                for key in ('position_rmse_m','heading_rmse_deg'):
                    maximum=max(maximum,abs(metric[key]-float(old[key])))
                support_difference+=abs(metric['scored_frames']-int(old['scored_frames']))
                rows.append(dict(id=ident,participant=old['participant'],condition=old['condition'],method=method,**metric))
    assert len(rows)==426 and maximum<1e-10 and support_difference==0
    summaries={}
    for method in sorted({r['method'] for r in rows}):
        summaries[method]=p.summarize([r for r in rows if r['method']==method])[0]
        assert abs(summaries[method]['equal_participant_mean_position_rmse_m']-run['summary']['common_native'][method]['equal_participant_mean_position_rmse_m'])<1e-10
    retained=verified_json(p.ROOT/'outputs_dynamic_loader_v36','run.json')
    p.write_csv(OUT/'trials.csv',rows)
    p.save_json(OUT/'run.json',dict(common_native=summaries,maximum_trial_metric_difference=maximum,scored_frame_difference=support_difference,
        retained_existing_loader_reproduction=retained['summary'],retained_loader_maximum_xy_difference_m=retained['maximum_xy_difference_m'],
        scope='Historical already-exposed validation predictions; artifact/metric audit only, not a new blind estimate or current full model refit',
        training=False,selection=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print(json.dumps(dict(maximum_metric_difference=maximum,scored_frame_difference=support_difference,
        old_clock_blend_mm=1000*summaries['old_clock_blend']['equal_participant_mean_position_rmse_m'],
        new_clock_refit_blend_mm=1000*summaries['new_clock_refit_blend']['equal_participant_mean_position_rmse_m']),indent=2))


if __name__=='__main__': main()
