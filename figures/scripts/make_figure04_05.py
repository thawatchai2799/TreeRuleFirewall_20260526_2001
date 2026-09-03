"""Figures 4 and 5 - protocol hierarchy expansion and 4D decomposition (illustrative examples).
The example rules are listed in first-match order so that the specific rule precedes the general one.
Output: Figure04/05.png and .pdf at 600 dpi."""
import os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
MONO = 'DejaVu Sans Mono'
def box(ax, x, y, w, h, fc, ec, lw=1.6): ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.02,rounding_size=0.08', fc=fc, ec=ec, lw=lw))

# ---- Figure 4
W, H = 6.7, 7.0
fig = plt.figure(figsize=(W, H), dpi=600); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
ax.text(W/2, H-0.35, 'Protocol Hierarchy Expansion', ha='center', fontsize=14, fontweight='bold', color='#1f3a5f')
ax.text(W/2, H-0.7, 'Phase 1 of Stage 4 (4D Decomposition)', ha='center', fontsize=9.5, color='#555')
box(ax, 0.5, H-2.3, W-1, 1.35, '#fbe0e0', '#b03a2e')
ax.text(W/2, H-1.25, 'Original LRF Rules (first-match order)', ha='center', fontsize=11, fontweight='bold', color='#b03a2e')
ax.text(0.85, H-1.65, 'r1:  TCP   192.168.1.5        ANY   443   \u2192 ALLOW', fontsize=9.5, family=MONO, color='#222')
ax.text(0.85, H-2.0, 'r2:  IP     192.168.0.0/16   ANY   ANY   \u2192 DENY', fontsize=9.5, family=MONO, color='#222')
ax.annotate('', xy=(W/2, H-3.1), xytext=(W/2, H-2.4), arrowprops=dict(arrowstyle='-|>', color='#333', lw=1.4)); ax.text(W/2+0.15, H-2.75, 'protocol\nexpansion', fontsize=8.5, style='italic', color='#333', va='center')
box(ax, 0.5, H-5.1, W-1, 1.95, '#dff2e4', '#1e8449')
ax.text(W/2, H-3.45, 'After Atomic Expansion (order preserved)', ha='center', fontsize=11, fontweight='bold', color='#1e8449')
for i, t in enumerate(['TCP:   192.168.1.5 / 443          \u2192 ALLOW   (from r1)', 'TCP:   192.168.0.0/16 (rest)      \u2192 DENY    (from r2)', 'UDP:   192.168.0.0/16              \u2192 DENY    (from r2)', 'ICMP:  192.168.0.0/16              \u2192 DENY    (from r2; type [0, 255])']):
    ax.text(0.85, H-3.85-0.33*i, t, fontsize=9, family=MONO, color='#222')
ax.text(W/2, H-5.55, '\u03a0(IP) = {TCP, UDP, ICMP}    (super-set: r2 yields three sub-rules)', ha='center', fontsize=9.5, color='#1f3a5f')
ax.text(W/2, H-5.9, '\u03a0(TCP) = {TCP}    (already atomic: r1 yields one sub-rule)', ha='center', fontsize=9.5, color='#1f3a5f')
ax.text(W/2, H-6.45, 'Sub-rules inherit the position of their parent rule, so first-match priority\nis preserved within each atomic protocol class before the sweep-line phase.', ha='center', fontsize=8.5, style='italic', color='#555')
fig.savefig(os.path.join(OUT, 'Figure04.png'), dpi=600); fig.savefig(os.path.join(OUT, 'Figure04.pdf')); plt.close(fig)

# ---- Figure 5
W, H = 6.7, 7.9
fig = plt.figure(figsize=(W, H), dpi=600); ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
ax.text(W/2, H-0.35, '4D Decomposition', ha='center', fontsize=14, fontweight='bold', color='#1f3a5f')
ax.text(W/2, H-0.7, 'Overlapping Rules \u2192 Disjoint Cells \u2192 TRF', ha='center', fontsize=9.5, color='#555')
box(ax, 0.5, H-2.1, W-1, 1.2, '#fbe0e0', '#b03a2e')
ax.text(W/2, H-1.2, 'Input LRF (first-match order)', ha='center', fontsize=11, fontweight='bold', color='#b03a2e')
ax.text(0.85, H-1.55, 'r1:  TCP  10.0.0.x / 80\u20131023  \u2192 DENY', fontsize=9.5, family=MONO, color='#222')
ax.text(0.85, H-1.9, 'r2:  IP   ANY                 \u2192 ALLOW   (r2 generalizes r1)', fontsize=9.5, family=MONO, color='#222')
ax.annotate('', xy=(W/2, H-2.55), xytext=(W/2, H-2.15), arrowprops=dict(arrowstyle='-|>', color='#333', lw=1.4)); ax.text(W/2+0.12, H-2.35, 'sweep-line 3D', fontsize=8.5, style='italic', color='#333', va='center')
box(ax, 0.5, H-4.75, W-1, 2.15, '#dff2e4', '#1e8449')
ax.text(W/2, H-2.85, 'After 4D Decomposition (disjoint cells)', ha='center', fontsize=11, fontweight='bold', color='#1e8449')
ax.text(W/2, H-3.3, '(UDP and ICMP: one ALLOW cell each, inherited from r2)', ha='center', fontsize=8, style='italic', color='#555')
cells = [('TCP \u00b7 src \u2260 10.0.0.x', 'port 0\u201365535', '\u2192 ALLOW', '#1e8449'), ('TCP \u00b7 10.0.0.x', 'port 0\u201379', '\u2192 ALLOW', '#1e8449'), ('TCP \u00b7 10.0.0.x', 'port 80\u20131023', '\u2192 DENY', '#b03a2e'), ('TCP \u00b7 10.0.0.x', 'port 1024\u201365535', '\u2192 ALLOW', '#1e8449')]
pos = [(0.75, H-3.95), (3.55, H-3.95), (0.75, H-4.65), (3.55, H-4.65)]
for (a, b, c, col), (px, py) in zip(cells, pos):
    box(ax, px, py, 2.45, 0.62, 'white', '#7f8c8d', 1.0); ax.text(px+1.225, py+0.45, a, ha='center', fontsize=8.3, fontweight='bold', color='#222'); ax.text(px+1.225, py+0.27, b, ha='center', fontsize=7.6, color='#444'); ax.text(px+1.225, py+0.09, c, ha='center', fontsize=8.3, fontweight='bold', color=col)
ax.annotate('', xy=(W/2, H-5.2), xytext=(W/2, H-4.8), arrowprops=dict(arrowstyle='-|>', color='#333', lw=1.4)); ax.text(W/2+0.12, H-5.0, 'directional merge', fontsize=8.5, style='italic', color='#333', va='center')
box(ax, 0.5, H-7.15, W-1, 1.9, '#dbe9f6', '#2c6fad')
ax.text(W/2, H-5.5, 'TRF Output (TCP subtree, Ordering 4)', ha='center', fontsize=11, fontweight='bold', color='#2c6fad')
ax.text(W/2, H-5.88, '[protocol]=TCP \u2192 [dst_ip]=ANY \u2192 [dst_port] \u2192 [src_ip]', ha='center', fontsize=9, family=MONO, color='#222')
ax.text(W/2, H-6.25, 'port 0\u201379 \u2192 ALLOW          port 1024\u201365535 \u2192 ALLOW', ha='center', fontsize=8.3, color='#222')
ax.text(W/2, H-6.52, 'port 80\u20131023 \u2192 [src_ip]: 10.0.0.x \u2192 DENY,  other \u2192 ALLOW', ha='center', fontsize=8.3, color='#222')
ax.text(W/2, H-6.9, 'Every packet reaches exactly one leaf; the DENY region equals M(r1), as first match requires.', ha='center', fontsize=7.9, style='italic', color='#555')
ax.text(W/2, 0.35, 'Conversion phases: \u2460 protocol expansion  \u2461 sweep-line 3D  \u2462 action assignment  \u2463 adjacent-cell merge', ha='center', fontsize=8.5, color='#1f3a5f')
fig.savefig(os.path.join(OUT, 'Figure05.png'), dpi=600); fig.savefig(os.path.join(OUT, 'Figure05.pdf'))
print('Figure04 and Figure05 written')
