"""Ideal-axis source consistency only; no recording or estimator evaluation."""
import json
import numpy as np
import pipeline as p

OUT=p.ROOT/'outputs_rotation_checks_v111'
SOURCE=p.ROOT/'outputs_rotation_source_v110'
DOC=p.ROOT/'research_docs/rotation_source_v110_v111.md'


def main():
    manifest=json.loads((SOURCE/'manifest.json').read_text())
    for name,sha in manifest.items():assert p.digest(SOURCE/name)==sha
    OUT.mkdir(exist_ok=False);rows=[];g=9.80665;lever=.04
    for phase in np.arange(9)*2*np.pi/9:
        for yaw in (-2.,0.,2.):
            for spin in (-8.,0.,8.):
                ax=g*np.sin(phase);az=g*np.cos(phase)+spin**2*lever
                corrected=az-spin**2*lever
                gx=yaw*np.sin(phase);gz=yaw*np.cos(phase)
                angle=np.arctan2(ax,corrected)
                figure=gx*np.sin(angle)+gz*np.cos(angle)
                assert abs(figure-yaw)<1e-12
                # shortcut: printed ratio is evaluated separately; do not infer unseen author code.
                printed_angle=np.arctan(corrected/ax) if abs(ax)>1e-12 else None
                printed=gx*np.sin(printed_angle)+gz*np.cos(printed_angle) if printed_angle is not None else None
                ax_g=ax/g;az_g=az/g-spin**2*lever/g
                figure_g=gx*ax_g/np.hypot(ax_g,az_g)+gz*az_g/np.hypot(ax_g,az_g)
                assert abs(figure_g-figure)<1e-12
                rows.append(dict(phase_rad=float(phase),yaw_rad_s=yaw,wheel_rad_s=spin,figure_yaw=float(figure),
                    figure_error=float(figure-yaw),printed_ratio_yaw=None if printed is None else float(printed),printed_ratio_error=None if printed is None else float(printed-yaw),
                    unit_path_difference=float(figure_g-figure)))
    camber=[]
    for degrees in (0.,3.2,12.,20.):
        theta=np.deg2rad(degrees);estimate=np.arctan(np.sin(theta))
        ratio=np.cos(theta)/np.cos(estimate)
        assert np.isclose(ratio,np.sqrt(1-np.sin(theta)**4),atol=1e-12)
        camber.append(dict(true_deg=degrees,estimated_deg=float(np.rad2deg(estimate)),
            error_deg=float(np.rad2deg(estimate)-degrees),ideal_transverse_scale_ratio=float(ratio)))
    assert len(rows)==81 and sum(r['printed_ratio_yaw'] is None for r in rows)==9
    json.dumps(rows,allow_nan=False)
    p.write_csv(OUT/'cases.csv',rows);p.write_csv(OUT/'camber.csv',camber)
    p.save_json(OUT/'run.json',dict(experiment='v111',cases=81,
        figure_max_error_rad_s=max(abs(r['figure_error']) for r in rows),
        printed_ratio_undefined=9,printed_ratio_disagreements=sum(r['printed_ratio_error'] is not None and abs(r['printed_ratio_error'])>1e-12 for r in rows),
        unit_path_max_difference=max(abs(r['unit_path_difference']) for r in rows),
        source_hashes_verified=len(manifest),source_manifest_sha256=p.digest(SOURCE/'manifest.json'),
        protocol_sha256=p.digest(DOC),source_sha256=p.digest(__file__),camber=camber,
        faithful_reproduction=False,recording_reads=0,predictions=0,promotion=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={f.name:p.digest(f) for f in OUT.iterdir() if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
