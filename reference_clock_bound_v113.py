"""Logical fixed-reference gate bound from sealed metadata, no signal reads."""
import json
import pipeline as p
from basin_completeness_v91 import verify

OUT=p.ROOT/'outputs_reference_clock_bound_v113'


def possible(channels,minimum):
    return any(q['motion_eligible'] and q['reference_peaks']>=minimum for q in channels)


def main():
    assert not possible([dict(motion_eligible=True,reference_peaks=1),dict(motion_eligible=False,reference_peaks=10)],2)
    assert possible([dict(motion_eligible=True,reference_peaks=2)],2)
    parents=[p.ROOT/'outputs_distributed_clock_candidates_v86',p.ROOT/'outputs_fold_seedless_clock_v84']
    hashes=sum(verify(q) for q in parents)
    clocks=json.loads((parents[1]/'clocks.json').read_text());assert len(clocks)==len({r['id'] for r in clocks})==207
    bad={r['id'] for r in clocks if not r['accepted']};assert len(bad)==8
    minimum=json.loads((parents[0]/'protocol.json').read_text())['settings']['min_peak_matches']
    channels=json.loads((parents[0]/'candidates.json').read_text());rows=[]
    for ident in sorted(bad):
        group=[q for q in channels if q['id']==ident]
        assert len(group)==2 and {q['channel'] for q in group}=={'speed','signed_yaw'}
        rows.append(dict(id=ident,imu_only_possible=possible(group,minimum),channels=[{k:q[k] for k in ('channel','motion_eligible','reference_peaks')} for q in group]))
    OUT.mkdir(exist_ok=False);p.save_json(OUT/'cases.json',rows)
    blocked=sum(not q['imu_only_possible'] for q in rows)
    p.save_json(OUT/'run.json',dict(experiment='v113',baseline_trials=207,baseline_accepted=199,
        reference_bound_blockers=blocked,permissive_acceptance_upper_bound=207-blocked,
        min_peak_matches=minimum,parent_hashes_verified=hashes,
        parent_manifests={q.name:p.digest(q/'artifact_manifest.json') for q in parents},
        protocol_sha256=p.digest(p.ROOT/'research_docs/reference_clock_bound_v113.md'),
        scope='fixed reference features/motion/peaks only; not physical timing unobservability',
        recording_reads=0,signal_reads=0,predictions=0,promotion=False))
    p.save_json(OUT/'artifact_manifest.json',dict(sha256={f.name:p.digest(f) for f in OUT.iterdir() if f.is_file()},source_sha256=p.digest(__file__)))
    print((OUT/'run.json').read_text(),flush=True)


if __name__=='__main__':main()
