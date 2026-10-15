"""Fit clock channels exclusively on fresh magnitude-seed TRAIN fold labels."""
import json
import numpy as np
import pipeline as p
from seedless_clock_v83 import OUT as SEEDS
from native_projection_v80 import OUT as SENSOR
from participant_folds_experiment_v24 import FOLDS
from observed_sync_experiment import synchronize_observed
from audit_fold_routes_v59 import verified_json

OUT=p.ROOT/'outputs_fold_seedless_clock_v84'


def main():
    OUT.mkdir(exist_ok=False)
    protocol=verified_json(SEEDS,'protocol.json');seeds=verified_json(SEEDS,'seeds.json');cfg=protocol['settings']
    inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    manifests={s:json.loads((s/'artifact_manifest.json').read_text())['sha256'] for s in (SEEDS,SENSOR)}
    data={};fulls={};refs={}
    for r in seeds:
        ident=r['id'];assert inv[ident]['partition']=='train'
        for folder,sub,target,keys in [(SENSOR,'sensors',fulls,('t','raw','imu_valid')),(SEEDS,'references',refs,None)]:
            path=folder/sub/(ident+'.npz');assert p.digest(path)==manifests[folder][str(path.relative_to(folder))]
            with np.load(path) as z:target[ident]={k:z[k] for k in (keys or z.files)}
        refs[ident]['hz']=float(refs[ident]['hz'])
        if r['accepted']:
            path=SEEDS/'labels'/(ident+'.npz');assert p.digest(path)==manifests[SEEDS][str(path.relative_to(SEEDS))]
            with np.load(path) as z:data[ident]={k:z[k] for k in z.files}
    p.save_json(OUT/'protocol.json',dict(hypothesis='Training-only seed fits produce supported held clocks without inherited clock calibration',
        configurations=['one fresh seed-only physical calibration per fold; unchanged signed search gates'],
        no_inherited_fallback=True,no_ATE_selection=True,frozen_207=True,validation_accessed=False,test_accessed=False,
        limitation='No alias arbitration override; reference geometry/QC and prior dataset acceptance remain inherited',
        gate=protocol['next_gate']))
    rows=[];models={}
    for fold,held_people in enumerate(FOLDS):
        held=[r['id'] for r in seeds if r['participant'] in held_people]
        fitting=[r['id'] for r in seeds if r['participant'] not in held_people and r['accepted']]
        assert not ({inv[i]['participant'] for i in fitting}&held_people)
        cal=p.calibrate([(inv[i],data[i],{}) for i in fitting],cfg)
        assert all(set(c['training_trials'])<=set(fitting) for c in cal.values())
        settings=dict(cfg,sync_terms={s:c['terms'] for s,c in cal.items()})
        models[str(fold)]=dict(fit_ids=fitting,held_ids=held,calibration=cal,seed_provenance='v83 fresh uncalibrated magnitudes; no saved labels or clocks',held_fit_overlap=0)
        for ident in held:
            r=inv[ident];full=fulls[ident];row=dict(id=ident,participant=r['participant'],condition=r['condition'],fold=fold)
            try:
                result=synchronize_observed(full['t'],full['raw'],full['imu_valid'],refs[ident],settings,r['setup'])
                row.update(accepted=True,**result)
            except p.TrialRejected as exc:row.update(accepted=False,reason=str(exc),diagnostics=exc.diagnostics)
            rows.append(row)
        p.save_json(OUT/'models.json',models);p.save_json(OUT/'checkpoint.json',rows)
        print('v84 completed fold',fold,'accepted',sum(r['accepted'] for r in rows),'/',len(rows),flush=True)
    assert len(rows)==207 and len({r['id'] for r in rows})==207
    p.save_json(OUT/'clocks.json',rows);p.write_csv(OUT/'trials.csv',[{k:v for k,v in r.items() if k not in ('diagnostics','search_diagnostics')} for r in rows])
    accepted=sum(r['accepted'] for r in rows)
    p.save_json(OUT/'run.json',dict(trials=207,accepted=accepted,rejected=207-accepted,held_fit_overlap=0,
        clock_seed_fit_nested=True,full_pipeline_nested=False,promotion=False,
        decision='clock coverage passes; frozen support and distributed alias review required' if accepted==207 else 'fail closed: missing held clocks; no reduced-support estimator refit',
        trajectory_metrics='unavailable: no trajectory predictions',validation_accessed=False,test_accessed=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
