"""Figure 13 - experiment pipeline diagram (six verification steps).  Output: Figure13.png/.pdf at 600 dpi."""
import os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
W, H = 6.6, 9.2
fig = plt.figure(figsize=(W, H), dpi=600); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
ax.text(W/2, H-0.3, 'Experiment Pipeline \u2014 Six Verification Steps', ha='center', va='center', fontsize=13, fontweight='bold', color='#1f3a5f')
ax.text(W/2, H-0.54, 'Synthetic dataset, ordering benchmark, ClassBench-ng, and compiled kernel', ha='center', va='center', fontsize=8.5, color='#444')
boxes = [('Generate', '10,000 LRF policies \u00b7 Small / Medium / Large \u00b7 seed 2025', '#dbe9f6', '#2c6fad'),
         ('Convert', 'LRF \u2192 TRF \u00b7 Algorithm 1 \u00b7 Ordering 4 (default)', '#e8dff5', '#6a4c9c'),
         ('Verify Step 1 \u2014 Semantic Fidelity', '10,000 policies \u00b7 73.12 M evaluations \u00b7 0 discrepancies', '#fbe0e0', '#b03a2e'),
         ('Verify Step 2 \u2014 Anomaly Detection', '7,000 trials \u00b7 14 configurations \u00b7 Z3 oracle on 10% sample', '#fdebd0', '#b9770e'),
         ('Verify Step 3 \u2014 Scalability & Depth', 'n = 5 \u2192 400 \u00b7 depth d = 4 \u00b7 two platforms', '#dff2e4', '#1e8449'),
         ('Verify Step 4 \u2014 Ordering Comparison', '12 orderings \u00b7 10 independently generated policies per size \u00b7 n \u2208 {50, 100, 200, 400}', '#d6eaf8', '#1f618d'),
         ('Verify Step 5 \u2014 ClassBench-ng', '8 rulesets \u00b7 32 cases \u00b7 vs FDD-style fixed-order ablation / HiCuts', '#e8dff5', '#7d3c98'),
         ('Verify Step 6 \u2014 Cython Kernel', '5 trials \u00b7 compiled native C \u00b7 same algorithm, different runtime', '#fadbd8', '#922b21')]
y = H-0.9; bh = 0.54; gap = 0.17; x0, bw = 0.5, W-1.0
for i, (t, s, fc, ec) in enumerate(boxes):
    ax.add_patch(FancyBboxPatch((x0, y-bh), bw, bh, boxstyle='round,pad=0.02,rounding_size=0.08', fc=fc, ec=ec, lw=1.6))
    ax.text(W/2, y-bh*0.36, t, ha='center', va='center', fontsize=9.5, fontweight='bold', color=ec)
    ax.text(W/2, y-bh*0.73, s, ha='center', va='center', fontsize=7.3, color='#333')
    if i < len(boxes)-1: ax.annotate('', xy=(W/2, y-bh-gap+0.02), xytext=(W/2, y-bh-0.02), arrowprops=dict(arrowstyle='-|>', color='#333', lw=1.2))
    y -= bh+gap
rh = y-0.25
ax.add_patch(FancyBboxPatch((x0, 0.2), bw, rh, boxstyle='round,pad=0.02,rounding_size=0.08', fc='#f4f6f7', ec='#5d6d7e', lw=1.6))
ax.text(W/2, 0.2+rh-0.2, 'Verified Results', ha='center', va='center', fontsize=10.5, fontweight='bold', color='#1f3a5f')
items = [('Fidelity = 100%', '73,120,887 evaluations, FN = 0  (95% UCI \u2264 4.10\u00d710\u207b\u2078)'),
         ('Recall = Precision = 100%', '20,868 TP, 0 FP, 0 FN (pairwise anomalies, Definition 5)'),
         ('d = 4 constant', 'all n = 5\u2192400 and all 32 ClassBench-ng cases (by construction; no early collapse)'),
         ('Cython 40\u00d7\u201341\u00d7 speedup', '97\u2013177 ns/packet  (39\u00d7 at n = 25); runtime, not algorithmic, comparison'),
         ('Theorems 1\u20133, Propositions 1\u20134', 'consistent with every measurement (proofs are deductive; experiments are checks)')]
yy = 0.2+rh-0.45
for h, s in items:
    ax.text(x0+0.25, yy, '\u2713 '+h, ha='left', va='center', fontsize=8.2, fontweight='bold', color='#1e8449')
    ax.text(x0+0.42, yy-0.14, s, ha='left', va='center', fontsize=6.9, color='#333'); yy -= 0.3
fig.savefig(os.path.join(OUT, 'Figure13.png'), dpi=600); fig.savefig(os.path.join(OUT, 'Figure13.pdf'))
print('Figure13 written')
