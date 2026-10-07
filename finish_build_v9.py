"""Assemble the completed build from sealed experiment outputs."""
import json
from pathlib import Path

from pipeline import ROOT, digest, save_json
from build_comparison_v9 import compare_tables


def main():
    folders=['outputs_long_horizon_v9','outputs_physics_state_v9','outputs_observed_sync_v9']
    for name in folders:
        folder=ROOT/name
        for file,sha in json.loads((folder/'artifact_manifest.json').read_text())['sha256'].items():
            if digest(folder/file)!=sha:raise RuntimeError('Changed experiment artifact: '+name+'/'+file)
    neural=json.loads((ROOT/'outputs_long_horizon_v9/selection.json').read_text())
    out=ROOT/'outputs_build_v9'
    chosen=neural['selected']
    tables={'Current ridge':ROOT/'outputs_observed_ridge_v8/selected_trials.csv',
        'Short-loss ensemble':ROOT/'outputs_long_horizon_v9/short_ensemble_trials.csv',
        'Endpoint-loss ensemble':ROOT/'outputs_long_horizon_v9/endpoint_ensemble_trials.csv',
        'Inner-selected neural model':ROOT/f'outputs_long_horizon_v9/{chosen}_trials.csv',
        'Empirical bias state':ROOT/'outputs_physics_state_v9/selected_trials.csv'}
    summary=compare_tables(tables,out)
    current=summary['Current ridge']
    rows=['# V9 build results','',
        'Three development experiments completed. Existing ridge artifacts and historical test results are preserved. No test acquisitions were opened. The main table uses identical v7 observed frames on 71 validation recordings/four participants. These repeatedly inspected participants provide exploratory development evidence.','',
        '| Candidate | Overall RMSE (mm) | SL RMSE (mm) |', '|---|---:|---:|']
    for name,value in summary.items():rows.append(f"| {name} | {value['overall_m']*1000:.3f} | {value['conditions']['SL']*1000:.3f} |")
    rows.extend(['','## Three-seed comparison','',
        '| Loss | Median RMSE (mm) | Minimum–maximum (mm) |','|---|---:|---:|'])
    for method,spread in neural['spread'].items():
        rows.append(f"| {method} | {spread['median_rmse_m']*1000:.3f} | {spread['minimum_rmse_m']*1000:.3f}–{spread['maximum_rmse_m']*1000:.3f} |")
    rows.extend(['',f"The neural method/seed **{chosen}** was selected on a training participant fold before final validation. New normalization, clipping and neural weights exclude that fold during selection. The inherited TCN and calibration previously saw those participants; this is conditional model selection, not a fully independent whole-pipeline fold. All three seeds and both predeclared motion ensembles are reported. The matched short-loss comparator uses the same segments/model/context; it is not a reproduction of the older ridge training procedure.",
        '', 'The endpoint objective uses observed start/end SE(2) poses at 1/3/5/10 seconds and uninterrupted IMU input. It does not fill intermediate optical gaps. Original 512-frame contexts and 1.28 seconds of future IMU are retained, with differentiable stitched central outputs. Short recordings use only supported horizons. The unfinished long-only attempt was preserved and corrected before final validation.',
        '', '## Observed-only synchronization','',
        'This separate comparison uses native optical timestamps and a shared initial pose: 116.823 → 116.508 mm. The 0.316 mm aggregate change accompanies a No.14 regression from 106.637 to 113.333 mm. Accepted training coverage changes from 473 to 465; all 71 validation recordings remain. It does not justify a claimed substantial accuracy gain or automatic promotion. Do not directly compare its native score to the main table’s resampled score.',
        '', '## Physics state comparator','',
        'The bounded empirical yaw-bias/wheel fusion comparator scores 230.680 mm versus 222.128 mm for its static empirical control. It improved its training holdout but worsened validation. Unknown integer encoding and mounting rotations prevent calling it a calibrated full attitude INS. It assumes zero lateral motion; it does not constrain the ridge model’s lateral channel. This negative result does not justify fusion.',
        '', '## Deployment decision',''])
    endpoint=summary['Endpoint-loss ensemble']
    improves_both=endpoint['overall_m']<current['overall_m'] and endpoint['conditions']['SL']<current['conditions']['SL']
    consistent=all(endpoint['participants'][person]<=value for person,value in current['participants'].items())
    decision='retain_existing_ridge'
    if improves_both and consistent:
        rows.append('The endpoint ensemble improves overall, SL and all four participant averages. It is a candidate for a frozen follow-up evaluation; all seeds and the existing control remain available. This exploratory result alone does not establish confirmatory paper accuracy.')
        decision='endpoint_ensemble_candidate_for_followup'
    else:
        rows.append('Retain the existing 116.898 mm ridge model. The new experiments do not establish a consistent gain across overall error, SL and all participants. Preserve the new candidates as measured comparisons rather than replacing the current model with a validation-selected best seed.')
    rows.extend(['', 'Global 1–10 mm accuracy and the below-100 mm overall/SL milestone remain unproven. A genuinely untouched cohort under a frozen observed-reference protocol is needed for a confirmatory paper estimate.',
        '', 'Reports: `outputs_long_horizon_v9/report.md`, `outputs_observed_sync_v9/report.md`, `outputs_physics_state_v9/report.md`. Paired SL trajectories and drift/turn/straight diagnostics are in `outputs_build_trajectories_v9/`.'])
    (out/'report.md').write_text('\n'.join(rows)+'\n',encoding='utf-8')
    save_json(out/'decision.json',dict(decision=decision,neural_preselected=chosen,summary=summary,seeds=neural['spread'],test_evaluated=False,
        provenance={name+'/artifact_manifest.json':digest(ROOT/name/'artifact_manifest.json') for name in folders},
        executed_source_sha256=digest(Path(__file__))))
    save_json(out/'artifact_manifest.json',dict(sha256={str(p.relative_to(out)):digest(p) for p in out.rglob('*') if p.is_file()}))
    print(json.dumps(dict(decision=decision,summary=summary,seeds=neural['spread']),indent=2))


if __name__=='__main__':main()
