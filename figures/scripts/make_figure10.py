"""Figure 10 - anomaly-detection TP per configuration. Data: ../../anomaly_benchmark_v12_results.json.  Output: Figure10.png/.pdf at 600 dpi."""
import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ROOT = os.path.abspath(os.path.join(OUT, '..'))
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

r = json.load(open(os.path.join(ROOT, 'anomaly_benchmark_v12_results.json')))['configurations']
order = ['Minimal (1S+1R)', 'Normal (2S+2R)', 'Heavy (3S+2R)', 'Only Redundant', 'Only Shadow', 'Single Shadow', 'Single Redundant']
labels = ['Min\n1S+1R', 'Norm\n2S+2R', 'Heavy\n3S+2R', 'Only\nRed', 'Only\nShad', 'Single\nShad', 'Single\nRed']
small = [next(d['TP'] for d in r if d['size_category'] == 'small' and d['config'] == c) for c in order]
medium = [next(d['TP'] for d in r if d['size_category'] == 'medium' and d['config'] == c) for c in order]
assert sum(small) + sum(medium) == 20868

NAVY = '#1F3A5F'
fig, ax = plt.subplots(figsize=(3.347, 2.75))   # 2008 x 1650 px at 600 dpi
plt.subplots_adjust(left=0.15, right=0.975, top=0.84, bottom=0.17)
x = np.arange(7); w = 0.38
ax.bar(x - w/2, small, w, color='#5B9BD5', label='Small (1–25 rules)', zorder=3)
ax.bar(x + w/2, medium, w, color='#9B77C6', label='Medium (26–100 rules)', zorder=3)
ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=5.6)
ax.set_ylim(0, 3000); ax.set_yticks(range(0, 3001, 500)); ax.tick_params(axis='y', labelsize=5.8)
ax.set_ylabel('True Positives (TP)', fontsize=6.5)
ax.grid(axis='y', ls=':', color='#D0D0D0', lw=0.5, zorder=0)
ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
for s in ('left', 'bottom'): ax.spines[s].set_linewidth(0.7)
ax.legend(fontsize=5.6, loc='upper right', frameon=True, edgecolor='#CCCCCC')
ax.set_title('Anomaly detection: TP per configuration\n7000 trials · FP = FN = 0 in every trial', fontsize=7.2, fontweight='bold', color=NAVY)
fig.savefig(os.path.join(OUT, 'Figure10.png'), dpi=600)
fig.savefig(os.path.join(OUT, 'Figure10.pdf'))
