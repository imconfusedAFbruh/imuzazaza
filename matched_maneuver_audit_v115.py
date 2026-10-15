"""Retrospective arithmetic on sealed exposed aggregate scores; no model fitting."""
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs_matched_maneuver_audit_v115'
SOURCE = ROOT / 'outputs_historical_metrics_v77'
PREFIX = 'outputs_clock_arbitrated_v42/'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def balanced(rows):
    people = sorted({r['participant_id'] for r in rows})
    return math.fsum(math.fsum(r['score'] for r in rows if r['participant_id'] == p)
                     / sum(r['participant_id'] == p for r in rows) for p in people) / len(people)


def winners(rows):
    result = {}
    for maneuver in sorted({r['maneuver'] for r in rows}):
        models = sorted({r['model'] for r in rows if r['maneuver'] == maneuver})
        result[maneuver] = min(models, key=lambda model: balanced(
            [r for r in rows if r['maneuver'] == maneuver and r['model'] == model]))
    return result


def main():
    fixture = [dict(participant_id=p, maneuver=q, model=m, score=x)
               for p in ('p1', 'p2') for q in ('a', 'b')
               for m, x in (('m1', 1 if q == 'a' else 3), ('m2', 2 if q == 'a' else 1))]
    chosen = winners(fixture)
    assert chosen == {'a': 'm1', 'b': 'm2'}
    assert balanced([r for r in fixture if r['model'] == chosen[r['maneuver']]]) == 1
    assert balanced([dict(participant_id='p1', score=0), dict(participant_id='p1', score=0),
                     dict(participant_id='p2', score=6)]) == 3
    manifest = json.loads((SOURCE / 'artifact_manifest.json').read_text())['sha256']
    inputs = {}
    for name in ('trial_metrics.csv', 'maneuver_summary.csv', 'summary.csv'):
        assert digest(SOURCE / name) == manifest[name], name
        inputs[str((SOURCE / name).relative_to(ROOT))] = manifest[name]
    source = ROOT / 'outputs_clock_arbitrated_v42'
    parent = json.loads((source / 'artifact_manifest.json').read_text())['sha256']
    for name in ('protocol.json', 'report.md'):
        assert digest(source / name) == parent[name], name
        inputs[str((source / name).relative_to(ROOT))] = parent[name]
    with (SOURCE / 'trial_metrics.csv').open(newline='') as f:
        rows = [dict(r, score=float(r['ATE_RMSE_mm'])) for r in csv.DictReader(f)
                if r['model'].startswith(PREFIX)]
    models = sorted({r['model'] for r in rows})
    assert len(models) == 6 and len(rows) == 426
    reference = {r['recording_id']: r for r in rows if r['model'] == models[0]}
    assert len(reference) == 71
    for model in models:
        group = [r for r in rows if r['model'] == model]
        assert len(group) == 71 and {r['recording_id'] for r in group} == set(reference)
        for r in group:
            assert math.isfinite(r['score']) and r['score'] >= 0
            a = reference[r['recording_id']]
            assert all(r[k] == a[k] for k in ('participant_id', 'maneuver', 'Valid_Frame_Count'))
    with (SOURCE / 'maneuver_summary.csv').open(newline='') as f:
        published = {(r['model'], r['maneuver']): r for r in csv.DictReader(f)}
    with (SOURCE / 'summary.csv').open(newline='') as f:
        summaries = {r['model']: r for r in csv.DictReader(f)}
    table = []
    for maneuver in sorted({r['maneuver'] for r in rows}):
        for model in models:
            group = [r for r in rows if r['model'] == model and r['maneuver'] == maneuver]
            score = balanced(group)
            assert abs(score - float(published[model, maneuver]['ATE_RMSE_mm'])) < 1e-9
            table.append(dict(maneuver=maneuver, model=model, ATE_RMSE_mm=score,
                              trials=len(group), people=len({r['participant_id'] for r in group})))
    chosen = winners(rows)
    switched = [r for r in rows if r['model'] == chosen[r['maneuver']]]
    assert len(switched) == 71 and {r['recording_id'] for r in switched} == set(reference)
    scores = {m: balanced([r for r in rows if r['model'] == m]) for m in models}
    assert all(abs(scores[m] - float(summaries[m]['ATE_RMSE_mm'])) < 1e-9 for m in models)
    result = dict(experiment='v115', scope='retrospective same-support six-candidate outcome oracle',
                  fixed_scores_mm=scores, chosen_by_maneuver=chosen,
                  switching_score_mm=balanced(switched), recording_count=71, people=4,
                  raw_or_prediction_reads=0, test_accessed=False, promotion=False,
                  input_hashes=inputs, protocol_sha256=digest(ROOT / 'research_docs/matched_maneuver_audit_v115.md'))
    OUT.mkdir(exist_ok=False)
    for name, data in [('maneuvers.csv', table), ('switched_trials.csv', switched)]:
        with (OUT / name).open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(data[0]))
            writer.writeheader()
            writer.writerows(data)
    (OUT / 'run.json').write_text(json.dumps(result, indent=2))
    (OUT / 'artifact_manifest.json').write_text(json.dumps(dict(
        sha256={p.name: digest(p) for p in OUT.iterdir() if p.is_file()},
        source_sha256=digest(Path(__file__))), indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
