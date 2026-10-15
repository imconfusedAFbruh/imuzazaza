"""Descriptive paired TRAIN stability; consumes sealed participant tables only."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT/'outputs_reservoir_path_v121'
OUT = ROOT/'outputs_reservoir_stability_v122'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(benefit):
    benefit = np.asarray(benefit, dtype=float)
    n = len(benefit)
    omitted = (benefit.sum()-benefit)/(n-1)
    draws = np.random.default_rng(122).integers(n, size=(4096, n))
    interval = np.quantile(benefit[draws].mean(axis=1), [.025, .975])
    means = (np.asarray(list(itertools.product((-1, 1), repeat=n)))@benefit)/n
    return dict(mean_benefit_mm=float(benefit.mean()),
                leave_one_person_out_benefits_mm=omitted.tolist(),
                bootstrap_percentile95_mm=interval.tolist(),
                two_sided_sign_flip_fraction=float(np.mean(np.abs(means)>=abs(benefit.mean())-1e-12)),
                sign_flips=len(means))


def self_check():
    same = summarize([2., 2., 2.])
    assert same['mean_benefit_mm'] == 2
    assert same['leave_one_person_out_benefits_mm'] == [2., 2., 2.]
    assert same['bootstrap_percentile95_mm'] == [2., 2.]
    assert same['two_sided_sign_flip_fraction'] == .25
    assert summarize([0., 0.])['two_sided_sign_flip_fraction'] == 1
    a = summarize([1., -2., 3.])
    b = summarize([-1., 2., -3.])
    assert a['two_sided_sign_flip_fraction'] == b['two_sided_sign_flip_fraction']


def main():
    self_check()
    if (ROOT/'research_state/STOP').exists():
        raise RuntimeError('STOP')
    manifest = json.loads((SOURCE/'artifact_manifest.json').read_text())['sha256']
    inputs = {}
    for name in ('lambda_0_participants.csv', 'lambda_10_participants.csv', 'run.json'):
        path = SOURCE/name
        assert digest(path) == manifest[name]
        inputs[str(path.relative_to(ROOT))] = digest(path)
    tables = []
    for penalty in (0, 10):
        with (SOURCE/f'lambda_{penalty}_participants.csv').open(newline='') as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 12
        tables.append({r['participant']: r for r in rows})
    assert tables[0].keys() == tables[1].keys()
    people = sorted(tables[0])
    assert sum(int(tables[0][person]['trials']) for person in people) == 207
    assert int(tables[0]['No.20']['trials']) == 15
    for person in people:
        assert tables[0][person]['trials'] == tables[1][person]['trials']
    values = np.array([[float(t[person]['mean_trial_position_rmse_m'])*1000
                        for person in people] for t in tables])
    run = json.loads((SOURCE/'run.json').read_text())
    assert run['selected']['penalty'] == 10 and run['selected']['eligible']
    assert abs(values[1].mean()-1000*run['selected']['equal_participant_mean_position_rmse_m']) < 1e-10
    benefit = values[0]-values[1]
    result = summarize(benefit)
    result.update(participants=people, recordings=207,
                  participant_benefits_mm=dict(zip(people, benefit.tolist())),
                  participants_improved=int((benefit>0).sum()),
                  conditional_post_selection_train_only=True,
                  validation_accessed=False, test_accessed=False)
    inputs['reservoir_stability_v122.py'] = digest(Path(__file__))
    inputs['research_docs/reservoir_stability_v122.md'] = digest(ROOT/'research_docs/reservoir_stability_v122.md')
    OUT.mkdir(exist_ok=False)
    (OUT/'run.json').write_text(json.dumps(dict(result=result, inputs=inputs), indent=2))
    (OUT/'artifact_manifest.json').write_text(json.dumps({'sha256': {'run.json': digest(OUT/'run.json')}}, indent=2))
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
