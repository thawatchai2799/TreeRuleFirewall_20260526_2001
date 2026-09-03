"""Figures 14 and 15 - ClassBench-ng comparison (latency/speedup) and depth heat maps.
Data: ../../classbench_results.json.  Output: Figure14/15.png and .pdf at 600 dpi."""
import json, os, statistics
import numpy as np
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.abspath(os.path.join(HERE, '..', '..')); OUT = os.path.join(HERE, '..')
d = json.load(open(os.path.join(ROOT, 'classbench_results.json')))['by_ruleset']
rs = ['acl1_1k', 'acl2_1k', 'acl3_1k', 'fw1_1k', 'fw2_1k', 'fw3_1k', 'ipc1_1k', 'ipc2_1k']; names = [r.replace('_1k', '') for r in rs]; sizes = [50, 100, 200, 400]
mean = lambda m: [statistics.mean(d[r]['by_size'][str(s)][m] for r in rs) for s in sizes]

# ---- Figure 14
fig, (a, b) = plt.subplots(2, 1, figsize=(6.7, 8.9), dpi=600)
a.axvspan(25, 150, color='#ead9f0', alpha=0.5); a.axvspan(150, 450, color='#d9efe5', alpha=0.5)
a.plot(sizes, mean('trf_match_us'), '-o', color='#2c4a6b', lw=2.4, ms=8, label='TRF (proposed; d = 4 in all cases)')
a.plot(sizes, mean('lrf_match_us'), '-s', color='#c0392b', lw=2.4, ms=8, label='LRF (linear scan baseline)')
a.plot(sizes, mean('fdd_match_us'), '-D', color='#5cb85c', lw=2.4, ms=8, label='FDD-style fixed-order ablation (Ordering 1)')
a.plot(sizes, mean('hicuts_match_us'), '-^', color='#e67e22', lw=2.4, ms=8, label='HiCuts [16]')
a.set_xscale('log'); a.set_xticks(sizes); a.set_xticklabels(sizes); a.set_xlim(40, 470)
a.text(60, 0.6, 'Medium', color='#7b4f9d', fontweight='bold'); a.text(260, 0.6, 'Large', color='#2e8b6e', fontweight='bold')
a.set_xlabel('sampled rules per ruleset', fontsize=11); a.set_ylabel('mean match latency (\u03bcs)', fontsize=11); a.set_ylim(0, 22)
a.set_title('(a)  Match latency \u2014 mean of 8 ClassBench-ng rulesets (Python)', fontsize=10.5, fontweight='bold', color='#1f3a5f'); a.legend(fontsize=8.5, loc='upper left'); a.grid(axis='y', ls=':', alpha=0.4)
sp = [d[r]['by_size']['400']['trf_speedup'] for r in rs]; cols = ['#2c4a6b' if v >= 1 else '#c0392b' for v in sp]
b.barh(names[::-1], sp[::-1], color=cols[::-1]); b.axvline(1, ls='--', color='k')
for i, v in enumerate(sp[::-1]): b.text(v + 0.05, i, f'{v:.2f}\u00d7', va='center', fontsize=9)
b.set_xlim(0, 4.9); b.set_xlabel('TRF/LRF speedup (\u00d7) at n=400 (Large)\n(>1 = TRF faster)', fontsize=10)
b.set_title('(b)  Per-ruleset speedup at n=400', fontsize=11, fontweight='bold', color='#1f3a5f')
for ax in (a, b):
    for s in ('top', 'right'): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(OUT, 'Figure14.png'), dpi=600); fig.savefig(os.path.join(OUT, 'Figure14.pdf')); plt.close(fig)

# ---- Figure 15
trf = np.array([[d[r]['by_size'][str(s)]['trf_depth'] for s in sizes] for r in rs]); hic = np.array([[d[r]['by_size'][str(s)]['hicuts_depth'] for s in sizes] for r in rs])
fig, (a, b) = plt.subplots(2, 1, figsize=(6.7, 9.9), dpi=600)
fig.suptitle('TRF vs HiCuts depth \u2014 8 rulesets \u00d7 4 sizes = 32 cases', fontsize=12, fontweight='bold', color='#1f3a5f')
for ax_, M, cm, vmax, title in [(a, trf, 'Blues', 7, '(a)  TRF depth \u2014 d = 4 in all 32 cases (FDD-style ablation identical)'), (b, hic, 'YlOrRd', 12, '(b)  HiCuts depth \u2014 variable (1\u201312); dark = deep worst-case path')]:
    im = ax_.imshow(M, cmap=cm, vmin=0, vmax=vmax, aspect='auto'); ax_.set_xticks(range(4)); ax_.set_xticklabels([f'n={s}' for s in sizes]); ax_.set_yticks(range(8)); ax_.set_yticklabels(names)
    for i in range(8):
        for j in range(4): ax_.text(j, i, str(M[i, j]), ha='center', va='center', fontsize=11, fontweight='bold', color='white' if M[i, j] > vmax * 0.55 else '#222')
    ax_.set_title(title, fontsize=10.5, fontweight='bold', color='#1f3a5f'); cb = fig.colorbar(im, ax=ax_, fraction=0.04, pad=0.02); cb.set_label('depth d')
fig.tight_layout(rect=[0, 0, 1, 0.97]); fig.savefig(os.path.join(OUT, 'Figure15.png'), dpi=600); fig.savefig(os.path.join(OUT, 'Figure15.pdf'))
print('Figure14 and Figure15 written')
