"""TRAIN PS boundary sensitivity, fixed existing offsets, no clock optimization."""
import csv,json
from pathlib import Path
import numpy as np
import pipeline as p
from observed_reference_experiment import observed_markers

OUT=p.ROOT/'outputs_no8_boundary_v46'
def main():
    if OUT.exists():raise RuntimeError('Preserve output')
    OUT.mkdir();cfg=json.loads((p.ROOT/'outputs_observed_reference_v7/run.json').read_text())['settings'];inv={r['id']:r for r in json.loads((p.ROOT/'outputs_amended_v2/inventory.json').read_text())}
    changes={r['id']:r for r in csv.DictReader((p.ROOT/'outputs_clock_arbitrated_v42/clock_changes.csv').open())};records=[];reader=p.read_markers
    try:
        p.read_markers=observed_markers
        for k in (1,2,3):
            id=f'2026-09-24__PS__PS_Trial{k}_No.8';row=inv[id];assert row['partition']=='train';delta=float(changes[id]['offset_delta_s'])
            with np.load(p.ROOT/'outputs_clock_arbitrated_folds_v43/common_trajectories'/(id+'.npz')) as z:a={key:z[key] for key in z.files}
            with np.load(p.ROOT/'outputs_clock_damped_v40/fold_motion'/(id+'.npz')) as z:frozen=z['frozen_new_clock_motion']
            old=a['old_clock_blend_motion'];g=p.reference(p.ROOT/row['c3d'],cfg,row['setup']);first=np.flatnonzero(g['derivative_valid'])[0]
            actual=float(np.trapezoid(frozen[:,0]-old[:,0],a['time_s']))
            formula=delta*(old[-1,0]-old[0,0])
            records.append(dict(id=id,delta_s=delta,common_initial_c3d_s=float(a['native_c3d_time_s'][0]),old_initial_forward_m_s=float(old[0,0]),old_final_forward_m_s=float(old[-1,0]),first_order_boundary_delta_mm=float(formula*1000),actual_forward_integral_delta_mm=actual*1000,remainder_mm=float((actual-formula)*1000),reference_first_observed_s=float(g['t'][np.flatnonzero(g['valid'])[0]]),reference_first_derivative_s=float(g['t'][first]),reference_first_derivative_speed_m_s=float(g['speed'][first])))
    finally:p.read_markers=reader
    p.write_csv(OUT/'boundary.csv',records);p.save_json(OUT/'run.json',dict(records=records,validation_accessed=False,test_accessed=False,no_clock_search=True,no_trajectory_alignment=True,source_sha256=p.digest(Path(__file__))))
    (OUT/'report.md').write_text('''# No.8 PS clock-boundary sensitivity v46

Fixed existing old/new offsets and same-fitting-ID old fold predictors. TRAIN only. No new lag optimization, no position-selected clock, no initial-pose modification or optical resets.

For a shifted velocity v(t+delta), integral difference over a fixed interval is approximately delta*[v(end)-v(start)]. Native observed C3D begins after motion has already reached about 2m/s. Ending velocity is approximately zero. A negative clock change therefore adds substantial integrated longitudinal travel from the beginning of the observed interval. This sensitivity is expected even when the clock repair improves independent yaw correlation.

PS2: delta=-55.5ms, initial/final old forward speed=2.097919/.022733m/s. First-order boundary contribution +115.173mm; actual frozen-new-clock minus old integral +125.763mm (remainder10.590mm).

PS3: delta=-41ms, initial/final=2.094083/.018520m/s. First-order +85.098mm; actual+82.638mm (remainder-2.460mm).

PS2 first optical observed/derivative times2.23/2.38s; first derivative speed2.048892m/s. PS3 times3.00/3.15s and2.022821m/s. No optical launch transition is available in these observed supports, so first-motion event matching cannot verify a shared acquisition start. This is not a reason to zero or snap position.

Inference: earlier clocking can have fortuitously canceled travel-model error at a crop that begins in motion. Synchronization improvements do not guarantee lower endpoint or synchronized position error under inherited calibration/model. Waveform effective lag can also include body/wheel braking response. New clock is supported by signed yaw and slightly improved signed-speed correlation; reverting from position loss would be invalid. Actual clock truth remains unverified without shared hardware timing.

The formula is first-order, not an exact causal decomposition: changes in timestamp-conditioned features and predictor preparation can contribute to the remainder. No trajectory cross-correlation is used to choose a clock because monotonically accumulating positions obscure time identifiability and would optimize the evaluated outcome.
''',encoding='utf-8')
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={str(f.relative_to(OUT)):p.digest(f) for f in OUT.rglob('*') if f.is_file()}));print(json.dumps(records,indent=2))
if __name__=='__main__':main()
