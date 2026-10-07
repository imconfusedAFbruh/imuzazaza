"""Source-backed diagnostic figure for v33 confidence ablation."""
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pipeline import ROOT, digest, save_json

p = ROOT/'outputs_weak_labels_v33'
run = json.loads((p/'run.json').read_text())
selection = json.loads((p/'selection.json').read_text())
weights = [q['confidence'] for q in selection['candidates']]
train = [q['score']*1000 for q in selection['candidates']]
validation = [run['summary'][q['name']]['equal_participant_mean_position_rmse_m']*1000 for q in selection['candidates']]
old = pd.read_csv(p/'confidence_0p0_trials.csv')
new = pd.read_csv(p/'confidence_0p5_trials.csv')
comparison = old.merge(new, on='id', suffixes=('_original', '_selected'))
comparison['delta_position_rmse_mm'] = (comparison['position_rmse_m_selected']-comparison['position_rmse_m_original'])*1000
comparison.to_csv(p/'paired_selected_vs_original.csv', index=False)
base = pd.read_csv(p/'confidence_0p0_maneuvers.csv').set_index('condition')
selected = pd.read_csv(p/'confidence_0p5_maneuvers.csv').set_index('condition')
delta = (selected['equal_participant_mean_position_rmse_m']-base['equal_participant_mean_position_rmse_m'])*1000
fig, axes = plt.subplots(1, 3, figsize=(15.8, 4.7))
fig.suptitle('Stored processed endpoint confidence: training gain, no useful validation gain', fontsize=15)
for ax, values, title in [(axes[0], train, 'Conditional training participant fold'), (axes[1], validation, 'Unchanged observed validation frames')]:
    ax.plot(weights, values, 'o-', color='#225ea8', linewidth=2)
    ax.axhline(values[0], color='#777777', linestyle='--', linewidth=1)
    for w, value in zip(weights, values):
        ax.annotate(f'{value:.3f}', (w, value), xytext=(0, 8), textcoords='offset points', ha='center', fontsize=9)
    ax.scatter([.5], [values[-1]], color='#d95f0e', zorder=4, s=70, label='Training-selected confidence 0.5')
    ax.set_title(title, fontsize=11)
    ax.set_xlabel('Confidence per processed endpoint')
    ax.set_ylabel('Equal-participant mean trajectory RMSE (mm)')
    ax.grid(alpha=.2)
    ax.margins(y=.25)
axes[0].legend(fontsize=8, loc='upper right')
axes[2].bar(delta.index, delta.values, color=['#d95f0e' if v > 0 else '#225ea8' for v in delta.values])
axes[2].axhline(0, color='#777777', linewidth=1)
axes[2].set_title('Selected model minus original, by maneuver', fontsize=11)
axes[2].set_ylabel('Change in RMSE (mm); lower is better')
axes[2].grid(axis='y', alpha=.2)
fig.text(.5, .012, 'All 473 training recordings. 71 validation recordings / 4 participants. Test untouched. Original base and calibration fixed.', ha='center', fontsize=9)
fig.tight_layout(rect=(0, .05, 1, .92))
(p/'figures').mkdir(exist_ok=True)
fig.savefig(p/'figures/confidence_ablation.png', dpi=150)
plt.close(fig)
save_json(p/'artifact_manifest.json', dict(sha256={str(q.relative_to(p)): digest(q) for q in p.rglob('*') if q.is_file() and q.name!='artifact_manifest.json'}))
print(p/'figures/confidence_ablation.png')
