"""Figures 6 and 8 - conversion-time breakdown (shares) and formal correctness chain.  Output: Figure06/08.png/.pdf at 600 dpi."""
import os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
# ---- Figure 8
W, H = 6.7, 9.0
fig = plt.figure(figsize=(W, H), dpi=600); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
ax.text(W/2, H-0.32, 'End-to-End Formal Correctness Chain', ha='center', fontsize=13.5, fontweight='bold', color='#1f3a5f')
def box(x, y, w, h, fc, ec, title, sub, fs=10):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.02,rounding_size=0.08', fc=fc, ec=ec, lw=1.6))
    ax.text(x+w/2, y+h*0.62, title, ha='center', va='center', fontsize=fs, fontweight='bold', color=ec); ax.text(x+w/2, y+h*0.27, sub, ha='center', va='center', fontsize=8, color='#333')
def tag(x, y, text, w, h):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.02,rounding_size=0.04', fc='white', ec='#2c4a6b', lw=1.0, ls='--'))
    ax.text(x+w/2, y+h/2, text, ha='center', va='center', fontsize=7.6, color='#2c4a6b')
bx, bw, bh = 0.45, 3.2, 0.8; gap = 0.48
ys = [H-0.8-i*(bh+gap) for i in range(6)]
box(bx, ys[0]-bh, bw, bh, '#fbe0e0', '#b03a2e', 'P  (LRF)', 'with anomalies')
box(bx, ys[1]-bh, bw, bh, '#fbe0e0', '#b03a2e', 'Deterministic Triad', 'Stage 2 \u00b7 O(n\u00b2) \u00b7 pairwise (Definition 5)')
box(bx, ys[2]-bh, bw, bh, '#fdebd0', '#b9770e', 'P\u2032  (pairwise conflict-free)', 'no Shadow / Redundant pair')
box(bx, ys[3]-bh, bw, bh, '#dbe9f6', '#2c6fad', '4D Decomp. + Proj. Normalization', 'Stages 4\u20135 \u00b7 Algorithm 1 \u00b7 cell set C\u2032', fs=9.5)
box(bx, ys[4]-bh, bw, bh, '#dff2e4', '#1e8449', 'TRF  T = BuildTRF(C\u2032, A*)', 'd = 4 \u00b7 sibling edges disjoint')
box(bx, ys[5]-bh, bw, bh, '#eeeeee', '#666666', 'ALLOW / DENY', '= \u03c6_LRF(P, \u03c8)')
for i in range(5): ax.annotate('', xy=(bx+bw/2, ys[i+1]), xytext=(bx+bw/2, ys[i]-bh), arrowprops=dict(arrowstyle='-|>', color='#333', lw=1.3))
tx = 4.0; tw = 2.3
tag(tx, ys[1]-bh+0.12, 'Proposition 2 (Completeness)\nLemma 4 (C1\u2013C4 \u21d4 containment)', tw, 0.56)
tag(tx, ys[2]-bh+0.19, 'Proposition 1 (Removal preserves \u03c6_LRF)', tw, 0.42)
tag(tx, ys[3]-bh-0.02, 'Lemma 1 (cells disjoint) \u00b7 Lemma 1.A\nLemma 1.B (axis alignment)\nLemma 2 (cover \u03a9) \u00b7 Lemma 3 (first match)', tw, 0.84)
tag(tx, ys[4]-bh+0.02, 'Corollary 1.B (sibling disjointness)\nTheorem 1 (\u03c6_TRF = \u03c6_LRF(P\u2032))\nTheorem 2 (leaves disjoint)', tw, 0.76)
tag(tx, ys[5]-bh+0.12, 'Corollary 1 (end-to-end)\nTheorem 3 (same for all a \u2208 A)', tw, 0.56)
ax.plot([0.45, W-0.45], [0.78, 0.78], color='#999', lw=0.8)
ax.text(W/2, 0.55, 'Corollary 1:  \u03c6_LRF(P, \u03c8) = \u03c6_LRF(P\u2032, \u03c8) = \u03c6_TRF(T, \u03c8)   for all \u03c8 \u2208 \u03a9 and every admissible ordering', ha='center', fontsize=8.4, fontweight='bold', color='#1f3a5f')
ax.text(W/2, 0.28, 'Consistency check: 73,120,887 evaluations \u00b7 0 discrepancies \u00b7 95% upper bound on FN rate 4.10\u00d710\u207b\u2078 (Section 6.2)', ha='center', fontsize=7.4, color='#555')
fig.savefig(os.path.join(OUT, 'Figure08.png'), dpi=600); fig.savefig(os.path.join(OUT, 'Figure08.pdf')); plt.close(fig)
# ---- Figure 6 (shares from the author's profiling run; absolute times are in Figure 12 / Table 6)
W, H = 6.7, 5.4
fig = plt.figure(figsize=(W, H), dpi=600)
fig.text(0.5, 0.95, 'Conversion Time Breakdown by Pipeline Stage', ha='center', fontsize=12.5, fontweight='bold', color='#1f3a5f')
fig.text(0.5, 0.905, 'profiled run, n = 400 rules, Ordering 4 \u2014 shares of wall-clock conversion time', ha='center', fontsize=8, color='#555')
ax = fig.add_axes([0.02, 0.22, 0.46, 0.62]); ax.set_aspect('equal')
shares = [55, 25, 15, 5]; cols = ['#e06666', '#5b8fd6', '#63b37c', '#f0a24b']
ax.pie(shares, colors=cols, startangle=90, counterclock=False, wedgeprops=dict(width=0.42, edgecolor='white', lw=2))
ax.text(0, 0, 'share of\nconversion\ntime', ha='center', va='center', fontsize=9.5, fontweight='bold', color='#1f3a5f')
labels = [('55%', 'Projection Normalization', 'Stage 5 \u00b7 O(N\u00b2)'), ('25%', 'Sweep-line cell construction', 'Stage 4, Phase 2 \u00b7 O(N\u00b7n)'), ('15%', 'Anomaly detection (Triad)', 'Stage 2 \u00b7 O(n\u00b2)'), ('5%', 'Expansion, action assignment, merge', 'Stage 4, Phases 1, 3, 4')]
ly = 0.78
for c, (p, l, s) in zip(cols, labels):
    fig.patches.append(plt.Rectangle((0.52, ly-0.015), 0.022, 0.032, transform=fig.transFigure, color=c))
    fig.text(0.555, ly+0.004, f'{p}  {l}', fontsize=7.8, va='center', fontweight='bold', color='#222'); fig.text(0.555, ly-0.03, s, fontsize=7, va='center', color='#555'); ly -= 0.1
fig.text(0.52, 0.34, 'N = cells before normalization; N = O(n\u00b3) per atomic\nprotocol in the worst case (Section 4.4). Projection\nNormalization dominates at large n because of its O(N\u00b2)\ncost; conversion is a one-time offline cost. Absolute\ntimes for the released runs: Figure 12 and Table 6.', fontsize=7.2, va='top', color='#333', linespacing=1.45)
fig.savefig(os.path.join(OUT, 'Figure06.png'), dpi=600); fig.savefig(os.path.join(OUT, 'Figure06.pdf'))
print('Figure06 and Figure08 written')
