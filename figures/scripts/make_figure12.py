"""Figure 12 - conversion time vs policy size. Data: ../../scalability_v12_results.json.  Output: Figure12.png/.pdf at 600 dpi."""
import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ROOT = os.path.abspath(os.path.join(OUT, '..'))
import json, matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

r = json.load(open(os.path.join(ROOT, 'scalability_v12_results.json')))['results']
ns = [d['n'] for d in r]; conv = [d['conv_mean_ms'] for d in r]

NAVY = '#1F3A5F'
cols = {'small': '#4A7FA5', 'medium': '#7B4FA0', 'large': '#2E8B6E'}
bands = {'small': ('#E8F0F8', '#4A7FA5'), 'medium': ('#F1E9F5', '#7B4FA0'), 'large': ('#E6F3EE', '#2E8B6E')}

fig, ax = plt.subplots(figsize=(3.347, 2.453))   # 2008 x 1472 px at 600 dpi
plt.subplots_adjust(left=0.135, right=0.98, top=0.86, bottom=0.17)
x = np.arange(len(ns))
ax.set_yscale('log')
# bands in index space (boundaries halfway between categories)
ax.axvspan(-0.5, 2.5, color=bands['small'][0], zorder=0)
ax.axvspan(2.5, 4.5, color=bands['medium'][0], zorder=0)
ax.axvspan(4.5, 6.5, color=bands['large'][0], zorder=0)
ax.plot(x, conv, color='#8C8C8C', lw=1.4, zorder=2)
for xi, yi, d in zip(x, conv, r):
    ax.plot(xi, yi, 'o', ms=6.5, color=cols[d['size_category']], zorder=3)
ax.set_xlim(-0.5, 6.5); ax.set_ylim(5, 5000)
ax.set_xticks(x); ax.set_xticklabels([str(n) for n in ns], fontsize=6)
ax.tick_params(axis='y', labelsize=6)
ax.set_xlabel('policy size n (rules)', fontsize=6.5)
ax.set_ylabel('conversion time (ms, log scale)', fontsize=6.5)
ax.grid(True, which='both', ls=':', color='#C9D3DD', lw=0.5, zorder=1)
ax.set_axisbelow(True)
for s in ax.spines.values(): s.set_linewidth(0.6)
# region labels placed in the empty corner of each band
ax.text(1.0, 1500, 'Small\n(1–25)', ha='center', va='center', fontsize=5.6, fontweight='bold', color=bands['small'][1])
ax.text(3.5, 20, 'Medium\n(26–100)', ha='center', va='center', fontsize=5.6, fontweight='bold', color=bands['medium'][1])
ax.text(5.5, 20, 'Large\n(101–400)', ha='center', va='center', fontsize=5.6, fontweight='bold', color=bands['large'][1])
ax.set_title('LRF→TRF conversion time vs policy size\nScalability benchmark (Ordering 4)', fontsize=7.2, fontweight='bold', color=NAVY)
fig.savefig(os.path.join(OUT, 'Figure12.png'), dpi=600)
fig.savefig(os.path.join(OUT, 'Figure12.pdf'))
