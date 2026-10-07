"""Summarize sealed v9 development experiments without opening recordings."""
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from pipeline import ROOT, digest, save_json


def compare_tables(tables, out):
    """Tables are explicitly supplied; unequal cohorts are rejected."""
    records = {}
    for name, path in tables.items():
        with path.open(newline='', encoding='utf-8') as stream:
            rows = list(csv.DictReader(stream))
        records[name] = {r['id']: r for r in rows}
        if len(records[name]) != len(rows):
            raise ValueError('Duplicate trial identifiers')
    control = records['Current ridge']
    for name, rows in records.items():
        if set(rows) != set(control):
            raise ValueError(f'{name}: different recording cohort; report separately')
        for trial, row in rows.items():
            if row['participant'] != control[trial]['participant'] or row['condition'] != control[trial]['condition']:
                raise ValueError('Changed participant or maneuver assignment')
            if 'scored_frames' in row and row['scored_frames'] != control[trial]['scored_frames']:
                raise ValueError('Different scored frame counts')
    people = sorted({r['participant'] for r in control.values()})
    conditions = sorted({r['condition'] for r in control.values()})
    summary = {}
    for name, rows in records.items():
        person = {p: float(np.mean([float(r['position_rmse_m']) for r in rows.values() if r['participant'] == p])) for p in people}
        maneuver = {c: float(np.mean([np.mean([float(r['position_rmse_m']) for r in rows.values() if r['condition'] == c and r['participant'] == p])
                            for p in people if any(r['condition'] == c and r['participant'] == p for r in rows.values())])) for c in conditions}
        summary[name] = dict(overall_m=float(np.mean(list(person.values()))), participants=person, conditions=maneuver)
    out.mkdir(exist_ok=False)
    fig, axes = plt.subplots(1, 2, figsize=(13, 4), layout='constrained')
    names = list(summary)
    width = .8 / len(names)
    for index, name in enumerate(names):
        for ax, keys, field in ((axes[0], people, 'participants'), (axes[1], conditions, 'conditions')):
            ax.bar(np.arange(len(keys)) + index * width, [1000*summary[name][field][k] for k in keys], width=width, label=name)
            ax.set_xticks(np.arange(len(keys)) + (len(names)-1)*width/2, keys)
            ax.set_ylabel('Mean trajectory RMSE (mm)'); ax.grid(axis='y', alpha=.2)
    axes[0].set_title('By participant'); axes[1].set_title('By maneuver')
    axes[0].legend(fontsize=8)
    fig.suptitle(f'Exploratory validation · {len(control)} recordings · identical observation support')
    fig.savefig(out/'comparison.png', dpi=180); fig.savefig(out/'comparison.svg'); plt.close(fig)
    save_json(out/'comparison.json', dict(results=summary, trials=len(control), test_evaluated=False,
        source_sha256=digest(Path(__file__)), tables={name:dict(path=str(path.relative_to(ROOT)), sha256=digest(path)) for name,path in tables.items()},
        limitations='Count/ID checks supplement runner provenance; exact mask equality is established by shared sealed v7 caches, not inferred from frame counts.'))
    return summary


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', action='append', default=[], help='Display name=relative trial CSV path')
    parser.add_argument('--out', default='outputs_build_comparison_v9')
    args=parser.parse_args()
    tables={'Current ridge': ROOT/'outputs_observed_ridge_v8/selected_trials.csv'}
    for value in args.candidate:
        name,path=value.split('=',1); tables[name]=ROOT/path
    print(json.dumps(compare_tables(tables, ROOT/args.out), indent=2))
