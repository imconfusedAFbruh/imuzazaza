"""Training-only endpoint support audit for the declared long-horizon windows."""
import json
import numpy as np
from pipeline import ROOT,digest,save_json
from planar_experiment import lateral_labels
from observed_training_experiment import observed_rows
from long_horizon_experiment import INNER,HORIZONS,N


def main():
    source=ROOT/'outputs_observed_reference_v7';out=ROOT/'outputs_long_horizon_support_v9_active'
    out.mkdir(exist_ok=False)
    cfg=json.loads((source/'run.json').read_text())['settings']
    manifest=json.loads((source/'artifact_manifest.json').read_text())
    counts={split:{str(h/100):dict(endpoint_pairs=0,pairs_crossing_optical_gaps=0) for h in HORIZONS} for split in ('inner_fit','all_training')}
    windows=dict(inner_fit=0,all_training=0)
    empty_windows=dict(inner_fit=0,all_training=0);condition_windows={}
    for row,d,_ in observed_rows(source,cfg,'train',manifest):
        _,valid=lateral_labels(d)
        valid&=np.isfinite(d['gt_v'])&np.isfinite(d['gt_yaw'])
        for start in range(0,len(d['t']),1024):
            if not d['imu_valid'][start:start+N].all() or not valid[start:start+N].any() or not d['gt_valid'][start]:continue
            if not d['imu_valid'][max(0,start-128):min(len(d['t']),start+1408)].all():continue
            if not any(start+h<len(d['t']) and d['gt_valid'][start+h] for h in HORIZONS):continue
            splits=['all_training']+(['inner_fit'] if row['participant'] not in INNER else [])
            for split in splits:
                windows[split]+=1
                empty_windows[split]+=sum(start+k>=len(d['t']) for k in range(0,N,256))
                if split=='all_training':condition_windows[row['condition']]=condition_windows.get(row['condition'],0)+1
                for h in HORIZONS:
                    if start+h>=len(d['t']) or not d['gt_valid'][start+h]:continue
                    item=counts[split][str(h/100)];item['endpoint_pairs']+=1
                    item['pairs_crossing_optical_gaps']+=int(not d['gt_valid'][start:start+h+1].all())
    for split in counts:
        for item in counts[split].values():item['fraction_crossing_optical_gaps']=item['pairs_crossing_optical_gaps']/max(item['endpoint_pairs'],1)
    save_json(out/'support.json',dict(eligible_windows=windows,excluded_empty_context_windows=empty_windows,all_training_condition_windows=condition_windows,horizons=counts,test_evaluated=False,source_sha256=digest(__file__),
      source_manifest_sha256=digest(source/'artifact_manifest.json'),
      semantics='Matches declared1025samplelongsegments,stride1024; endpointandIMUsupport only, rates finite on anypart; no intermediate optical poses in endpoint objective.'))
    print(json.dumps(dict(windows=windows,excluded_empty_context_windows=empty_windows,all_training_condition_windows=condition_windows,counts=counts),indent=2))


if __name__=='__main__':main()
