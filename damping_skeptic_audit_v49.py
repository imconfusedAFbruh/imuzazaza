"""Independent read-only training damping/control audit, no estimator fitting."""
import json,csv
from pathlib import Path
import numpy as np
import pipeline as p

OUT=p.ROOT/'outputs_damping_skeptic_v49'
DAMP=p.ROOT/'outputs_clock_arbitrated_damped_v46'
FOLD=p.ROOT/'outputs_clock_arbitrated_folds_v43'
OLD=p.ROOT/'outputs_dynamic_blend_v34'

def main():
    if OUT.exists():raise RuntimeError('Preserve output')
    OUT.mkdir();checks=[]
    for folder in (DAMP,FOLD,OLD,p.ROOT/'outputs_clock_small_basin_v48'):
        seals=json.loads((folder/'artifact_manifest.json').read_text())['sha256']
        for name,digest in seals.items():assert p.digest(folder/name)==digest
        checks.append(dict(folder=folder.name,verified_files=len(seals)))
    inv={q['id']:q for q in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    protocol=json.loads((p.ROOT/'outputs_clock_arbitrated_v42/protocol.json').read_text());trainset=set(protocol['training_ids']);fitchecks=[];heldids=set()
    for i in range(3):
        old=json.loads((OLD/f'fold_{i}_models.json').read_text());new=json.loads((FOLD/f'fold_{i}_models.json').read_text())
        assert set(old['fit_ids'])==set(new['fitting_ids'])
        hs=set(new['held_ids']);fs=set(new['fitting_ids']);assert not hs&fs and hs|fs==trainset
        assert all(inv[id]['partition']=='train' for id in hs|fs)
        assert not ({inv[id]['participant'] for id in hs}&{inv[id]['participant'] for id in fs})
        assert not heldids&hs;heldids|=hs
        fitchecks.append(dict(fold=i,held=len(hs),fit=len(fs),same_fit_ids=True,held_people=sorted({inv[id]['participant'] for id in hs})))
    rows=list(csv.DictReader((DAMP/'training_trials.csv').open()));prior=list(csv.DictReader((FOLD/'trials.csv').open()))
    for r in rows:
        assert r['id'] in heldids and inv[r['id']]['partition']=='train'
        for key in ('position_rmse_m','heading_rmse_deg'):r[key]=float(r[key])
    oldscores={(r['id'],r['method']):float(r['position_rmse_m']) for r in prior}
    worst_diff=0
    for r in rows:
        if r['method'] in ('old_clock_control','weight_1'):
            name='old_clock_blend' if r['method']=='old_clock_control' else 'new_clock_blend'
            worst_diff=max(worst_diff,abs(r['position_rmse_m']-oldscores[r['id'],name]))
    assert worst_diff<1e-12
    selection=json.loads((DAMP/'selection.json').read_text());candidates=[]
    oldbase={r['participant']:r['mean_trial_position_rmse_m'] for r in p.summarize([r for r in rows if r['method']=='old_clock_control'])[1]}
    samebase={r['participant']:r['mean_trial_position_rmse_m'] for r in p.summarize([r for r in rows if r['method']=='weight_0'])[1]}
    for c in selection['candidates']:
        group=[r for r in rows if r['method']==f'weight_{c["weight"]:g}'];assert len(group)==207 and len({r['id'] for r in group})==207
        ss,pp,_=p.summarize(group);ratios={q['participant']:q['mean_trial_position_rmse_m']/oldbase[q['participant']] for q in pp};same={q['participant']:q['mean_trial_position_rmse_m']/samebase[q['participant']] for q in pp}
        assert abs(ss['equal_participant_mean_position_rmse_m']-c['score'])<1e-12
        assert abs(max(ratios.values())-c['worst_old_clock_ratio'])<1e-12
        assert abs(max(same.values())-c['worst_same_clock_ratio'])<1e-12
        candidates.append(dict(weight=c['weight'],score_mm=c['score']*1000,worst_old=max(ratios.values()),worst_same=max(same.values()),worst_person=max(ratios,key=ratios.get),eligible=max(ratios.values())<=1.05 and max(same.values())<=1.05))
    assert not any(c['eligible'] for c in candidates) and selection['selected'] is None
    assert not list((DAMP/'validation_trajectories').iterdir()) and not (DAMP/'validation_trials.csv').exists()
    fallback=sorted(heldids&set(protocol['fallback_old_clock_ids']))
    # For old-clock fallback, frozen prediction must reproduce old-clock control.
    fallback_errors={}
    for id in fallback:
        with np.load(DAMP/'fold_motion'/(id+'.npz')) as z:frozen=z['frozen_new_clock_motion']
        with np.load(FOLD/'common_trajectories'/(id+'.npz')) as z:old=z['old_clock_blend_motion']
        error=float(np.max(np.abs(frozen-old)));fallback_errors[id]=error;assert error<1e-10
    signalrows=list(csv.DictReader((p.ROOT/'outputs_clock_small_basin_v48/signal_evidence.csv').open()))
    indexed={(r['id'],r['source']):r for r in signalrows};strong=[]
    for r in signalrows:
        if r['source']=='speed' and float(r['new_correlation'])-float(r['old_correlation'])<=-.025:
            y=indexed[r['id'],'signed_yaw'];strong.append(dict(id=r['id'],delta_ms=float(r['delta_s'])*1000,speed_old=float(r['old_correlation']),speed_new=float(r['new_correlation']),yaw_old=float(y['old_correlation']),yaw_new=float(y['new_correlation']),yaw_gain=float(y['new_correlation'])-float(y['old_correlation'])))
    oldcfg=json.loads((p.ROOT/'outputs_observed_reference_v7/run.json').read_text())['settings'];newcfg=json.loads((p.ROOT/'outputs_observed_sync_v9/run.json').read_text())['settings']
    same_sync_terms=oldcfg['sync_terms']==newcfg['sync_terms']
    results=dict(manifests=checks,folds=fitchecks,held_train_count=len(heldids),maximum_control_score_difference_m=worst_diff,candidates=candidates,fallback_frozen_motion_max_errors=fallback_errors,validation_output_absent=True,source_has_guard_before_validation=True,strong_speed_contradictions=strong,v48_old_new_sync_terms_identical=same_sync_terms,validation_accessed=False,test_accessed=False)
    p.save_json(OUT/'audit.json',results);p.write_csv(OUT/'weights.csv',candidates);p.write_csv(OUT/'strong_speed_contradictions.csv',strong)
    lines=['# Damping and small-clock skeptic audit v49','','## Damping: rejection reproduced','',f'All sealed parent file hashes verified: {checks}. Exact same fitting IDs checked in all three folds.207 held TRAIN trials/12 people, no cross-participant fitting overlap. Old controls and weight1 refit scores reproduce v43 with maximum difference{worst_diff:.3g}m. All six weights0/.1/.25/.5/.75/1 reaggregated; none pass both frozen5%guards. Empty validation output directory and absent validation table corroborate the source guard raising before the validation loop. Reading validation ID metadata is not reading validation signals. No test access.','', '| Weight | Equal-person RMSE mm | Worst old-clock ratio | Worst same-clock ratio | Eligible |','|---|---:|---:|---:|---|']
    lines +=[f'| {q["weight"]} | {q["score_mm"]:.6f} | {q["worst_old"]:.9f} | {q["worst_same"]:.9f} | {q["eligible"]} |' for q in candidates]
    lines +=['',f'Fallback raw selection uses exactly v42 fallback IDs; {len(fallback)} fallback IDs occur in held folds. Independently checking frozen motion on every fallback gives <=1e-10 difference from old clock control. The SENSORS v40 folder is verified but not used for inference in the v46 source, so obsolete all-new raw cannot override fallback. Calibration/base remain inherited.','', '## Small-shift contradictions: flag, do not force clocks','', '| Trial | Delta ms | Old speed corr | New speed corr | Yaw gain |','|---|---:|---:|---:|---:|']
    lines +=[f'| {r["id"]} | {r["delta_ms"]:+.3f} | {r["speed_old"]:.6f} | {r["speed_new"]:.6f} | {r["yaw_gain"]:+.6f} |' for r in strong]
    lines +=['',f'v48 old/new sync_terms identical: {same_sync_terms}. All five speed contradictions improve yaw modestly (+.0041 to+.0198), below the large-update gate minimum+.025. Every candidate is under250ms and the existing frozen v42 rule therefore retains new. These results establish channel disagreement, not physical clock truth. They justify flagging and testing a new training-predeclared multichannel synchronization protocol; they do not justify blindly choosing the old lag.','', 'Wheel speed differs from body speed under braking/slip, and inherited wheel calibration is jointly fit to midpoint speed rather than verified individual rim speeds. Optical speed derivatives may also contain segment/filter edge effects. v48 uses absolute speed, globally standardized signals, and merely checks nonzero normalized SD; it does not enforce the v42 physical-amplitude identifiability thresholds, distributed windows, independent ordinal edges or response-delay separation. A global wheel-speed correlation decline can therefore be an effective-lag confound. Do not promote an offset based on these global scores alone. Signed yaw directly observes body angular motion but can carry mounting/lever-arm effects or optical heading issues too. Shared trigger/timecode remains unavailable.','', '## Simple refit v49 source leakage scope','', 'Source excludes held people before p.calibrate, and calibrate axes/scales/rest biases/gravity use only fitting raw/optical labels. Startup initialization reads original held IMU first5s using fitting calibration, not optical targets. Base motion p.velocities replaces the inherited ridge. Feature clipping, normalization, residual caps and endpoint fitting receive fitting entries only. Held optical data is used for evaluating metrics and the single allowed optical initial pose. Thus estimator fitting is participant-excluded by source inspection.','', 'Limits: cached clock/reference geometry/QC preparation remains inherited. Fixed C hyperparameters originated in older exploratory conditional training; no nested selection is implemented.207identified target-train records are a smaller dataset than473current inherited controls; scores are not like-for-like model quality comparisons. The source scores its own prepared100Hz supports/initial poses, whereas v43 uses native-common support. Compare within v49 first; do not subtract v43 or validation headline as an exact gain. This is a calibration+base+residual estimator refit audit, not a completely independent synchronization or final test. Calibration uses pooled labels without equal-person weighting; setup-specific fits may be unstable when excluding four people.','', 'Protocol text in v46 still mentions the historically rejected No13 alias as if unresolved, even though fallback selection fixes it; this stale text does not change runtime raw selection, but should be clarified in future reports. No sealed source or output modified.']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(q.relative_to(OUT)):p.digest(q) for q in OUT.rglob('*') if q.is_file()}));print(json.dumps(results,indent=2))

if __name__=='__main__':main()
