"""Figure 11 - Python-level match latency and speedup, TRF vs LRF (scalability benchmark).
Data: ../../scalability_v12_results.json.  Output: Figure11.png / Figure11.pdf at 600 dpi."""
import json, os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
OUT = os.path.join(HERE, '..')

d = json.load(open(os.path.join(ROOT, 'scalability_v12_results.json')))['results']
ns = [r['n'] for r in d]; lrf = [r['lrf_mean_us'] for r in d]; trf = [r['trf_mean_us'] for r in d]; sp = [r['speedup'] for r in d]
xs = list(range(len(ns)))
fig, (a, b) = plt.subplots(2, 1, figsize=(6.7, 7.7), dpi=600)
a.axvspan(-0.5, 2.5, color='#dde8f5', alpha=0.6); a.axvspan(2.5, 4.5, color='#ead9f0', alpha=0.6); a.axvspan(4.5, 6.5, color='#d9efe5', alpha=0.6)
a.plot(xs, lrf, '-o', color='#c0392b', lw=2.5, ms=9, label='LRF (linear scan, Python reference)')
a.plot(xs, trf, '-s', color='#2c4a6b', lw=2.5, ms=9, label='TRF (proposed, Python reference)')
a.axvline(4, ls=':', color='#333'); a.text(4.07, 14.5, 'crossover\nn\u2248100', fontsize=10, color='#333')
for x, t, c in [(0.9, 'Small', '#5b7fa6'), (3.5, 'Medium', '#7b4f9d'), (5.5, 'Large', '#2e8b6e')]:
    a.text(x, 0.9, t, fontsize=11, fontweight='bold', color=c, ha='center')
a.set_xticks(xs); a.set_xticklabels(ns); a.set_xlim(-0.5, 6.5); a.set_ylim(0, 21)
a.set_xlabel('policy size n (rules)', fontsize=12); a.set_ylabel('match latency (\u03bcs)', fontsize=12)
a.set_title('(a)  Match latency: TRF vs LRF (both CPython)', fontsize=13, fontweight='bold', color='#1f3a5f')
a.legend(loc='upper left', fontsize=10); a.grid(axis='y', ls=':', alpha=0.4)
cols = ['#8fbde0'] * 3 + ['#b39ddb'] * 2 + ['#66c2a5'] * 2
b.bar(xs, sp, color=cols)
for x, v in zip(xs, sp): b.text(x, v + 0.07, f'{v:.2f}\u00d7', ha='center', fontsize=10)
b.axhline(1, ls='--', color='k')
b.legend(handles=[Patch(color='#8fbde0', label='Small (1\u201325)'), Patch(color='#b39ddb', label='Medium (26\u2013100)'), Patch(color='#66c2a5', label='Large (101\u2013400)')], loc='upper left', fontsize=10)
b.set_xticks(xs); b.set_xticklabels(ns); b.set_ylim(0, 3.9)
b.set_xlabel('policy size n (rules)', fontsize=12); b.set_ylabel('TRF / LRF speedup (\u00d7)', fontsize=12)
b.set_title('(b)  Python-level TRF/LRF speedup (same runtime)', fontsize=13, fontweight='bold', color='#1f3a5f')
b.grid(axis='y', ls=':', alpha=0.4)
for ax in (a, b):
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(OUT, 'Figure11.png'), dpi=600); fig.savefig(os.path.join(OUT, 'Figure11.pdf'))
print('Figure11 written')
