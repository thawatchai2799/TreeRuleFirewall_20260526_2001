"""Figure 9 - TRF decision-tree anatomy (Ordering 4).  Output: Figure09.png/.pdf at 600 dpi."""
import os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
W, H = 6.9, 6.0; S = 0.4
fig = plt.figure(figsize=(W, H), dpi=600); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
ax.text(0.3, H-0.35, 'TRF Decision Tree Anatomy', fontsize=13.5, fontweight='bold', color='#1f3a5f')
ax.text(0.3, H-0.68, 'Fixed-depth traversal: d = 4 levels (one per attribute); bound d \u2264 7 in the general model', fontsize=8.6, color='#555')
def node(x, y, label, fc, ec, w=0.92, h=0.36, fs=8.3):
    ax.add_patch(FancyBboxPatch((x-w/2, y-h/2), w, h, boxstyle='round,pad=0.02,rounding_size=0.06', fc=fc, ec=ec, lw=1.4))
    ax.text(x, y, label, ha='center', va='center', fontsize=fs, fontweight='bold', color=ec)
def edge(x1, y1, x2, y2, lab=None, dx=0.06):
    ax.plot([x1, x2], [y1-0.18, y2+0.18], color='#777', lw=1.1)
    if lab: ax.text((x1+x2)/2+dx, (y1+y2)/2, lab, fontsize=7, style='italic', color='#666')
L = [H-1.35, H-2.45, H-3.55, H-4.65]
for i, l in enumerate(['L1', 'L2', 'L3', 'L4']): ax.text(0.3, L[i], l, fontsize=10, fontweight='bold', color='#888', va='center')
node(2.5+S, L[0], '[protocol]', '#dbe9f6', '#2c6fad')
for x, lab in [(1.5+S, 'TCP'), (2.5+S, 'UDP'), (3.5+S, 'ICMP')]:
    node(x, L[1], '[dst_ip]', '#dff2e4', '#1e8449'); edge(2.5+S, L[0], x, L[1], lab)
node(1.0+S, L[2], '[dst_port]', '#fdebd0', '#b9770e'); node(2.0+S, L[2], '[dst_port]', '#fdebd0', '#b9770e')
edge(1.5+S, L[1], 1.0+S, L[2], '10.0.x', dx=-0.45); edge(1.5+S, L[1], 2.0+S, L[2], '192.x')
node(0.75+S, L[3], '[src_ip]', '#fbe0e0', '#b03a2e', w=0.78); node(1.55+S, L[3], '[src_ip]', '#fbe0e0', '#b03a2e', w=0.78)
edge(1.0+S, L[2], 0.75+S, L[3]); edge(1.0+S, L[2], 1.55+S, L[3])
node(0.75+S, L[3]-0.7, 'ALLOW', '#1e8449', '#ffffff', w=0.7, h=0.3, fs=8); node(1.55+S, L[3]-0.7, 'DENY', '#c0392b', '#ffffff', w=0.7, h=0.3, fs=8)
for x in (0.75+S, 1.55+S): ax.plot([x, x], [L[3]-0.18, L[3]-0.55], color='#777', lw=1.1)
px, py, pw, ph = 4.55, H-4.95, 2.1, 3.35
ax.add_patch(FancyBboxPatch((px, py), pw, ph, boxstyle='round,pad=0.02,rounding_size=0.08', fc='#f4f6f7', ec='#5d6d7e', lw=1.3))
ax.text(px+pw/2, py+ph-0.28, 'Per-level role (Ordering 4)', ha='center', fontsize=8.8, fontweight='bold', color='#1f3a5f')
rows = [('L1', '#2c6fad', 'Root: split on protocol\n(3 atomic classes)'), ('L2', '#1e8449', 'Disjoint dst_ip ranges\n(Corollary 1.B, Theorem 2)'), ('L3', '#b9770e', 'dst_port refinement in the\nprotocol domain (Def. 1.bis)'), ('L4', '#b03a2e', 'src_ip filter; leaf = action.\nEvery packet: one leaf')]
yy = py+ph-0.75
for l, c, txt in rows:
    ax.text(px+0.14, yy, l, fontsize=8.6, fontweight='bold', color=c, va='top'); ax.text(px+0.5, yy, txt, fontsize=7.0, color='#333', va='top', linespacing=1.35); yy -= 0.72
ax.text(0.3, 0.35, 'Per-packet work is O(d\u00b7c): d = 4 levels; c = child-selection cost at a node, which grows with fan-out (Section 7.3).', fontsize=7.4, style='italic', color='#555')
fig.savefig(os.path.join(OUT, 'Figure09.png'), dpi=600); fig.savefig(os.path.join(OUT, 'Figure09.pdf'))
print('Figure09 written')
