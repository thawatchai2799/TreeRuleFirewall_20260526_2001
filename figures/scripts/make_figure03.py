"""Figure 3 - LRF anomaly types (match-space visualization).  Output: Figure03.png/.pdf at 600 dpi."""
import os
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ROOT = os.path.abspath(os.path.join(OUT, '..'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['hatch.linewidth'] = 0.6
from matplotlib.patches import FancyBboxPatch, Rectangle

W, H = 2.733, 4.487  # inches -> 1640 x 2692 px at 600 dpi
fig = plt.figure(figsize=(W, H))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 100); ax.set_ylim(0, 164); ax.axis('off')
NAVY = '#1F3A5F'; TXT = '#333333'

ax.text(50, 160.3, 'LRF Anomaly Types', ha='center', va='center', fontsize=10.5, fontweight='bold', color=NAVY)
ax.text(50, 153.8, 'Match-Space Visualization', ha='center', va='center', fontsize=7.2, color='#555555')

def panel(y0, y1, face, edge, title, tcol, formula, fixtxt):
    ax.add_patch(FancyBboxPatch((4, y0), 92, y1 - y0, boxstyle='round,pad=0,rounding_size=2',
                                fc=face, ec=edge, lw=1.3))
    ax.text(50, y1 - 3.6, title, ha='center', va='center', fontsize=9.6, fontweight='bold', color=tcol)
    ax.text(50, y1 - 9.0, formula, ha='center', va='center', fontsize=6.6, color=TXT)
    ax.add_patch(FancyBboxPatch((48, y0 + 2.5), 45, 6, boxstyle='round,pad=0,rounding_size=1.2',
                                fc='#E4F2E1', ec='#2E7D32', lw=1.0))
    ax.text(70.5, y0 + 5.5, fixtxt, ha='center', va='center', fontsize=6.4, fontweight='bold', color='#2E7D32')

def note(x, y, lines, size=6.4):
    ax.text(x, y, lines, ha='left', va='top', fontsize=size, color=TXT, linespacing=1.35)

# ---------------- Shadow
panel(103, 151, '#FBEAE8', '#D9A09A', 'Shadow', '#C0392B', r'M(r$_j$) ⊆ M(r$_i$),  α$_i$ ≠ α$_j$', 'Fix: Triad removes r$_j$')
ax.add_patch(Rectangle((8, 113), 37, 24, fc='#DCE8F3', ec=NAVY, lw=1.4))
ax.text(26.5, 133, r'r$_i$ : DENY', ha='center', va='center', fontsize=7.0, fontweight='bold', color=NAVY)
ax.add_patch(Rectangle((16, 118), 21, 11, fc='#F4D8D6', ec='#D98C86', lw=1.1, ls=(0, (3, 2))))
ax.text(26.5, 123.5, r'r$_j$ : ALLOW', ha='center', va='center', fontsize=6.6, fontweight='bold', color='#C0392B')
note(49, 136.5, 'r$_j$ unreachable: r$_i$\nintercepts all M(r$_j$)\nfirst — wrong action\napplied')

# ---------------- Redundancy
panel(53, 101, '#FCF5E3', '#E2C878', 'Redundancy', '#B8860B', r'M(r$_j$) ⊆ M(r$_i$),  α$_i$ = α$_j$', 'Fix: removed (Prop. 1)')
ax.add_patch(Rectangle((8, 63), 37, 24, fc='#DCE8F3', ec=NAVY, lw=1.4))
ax.text(26.5, 83, r'r$_i$ : ALLOW', ha='center', va='center', fontsize=7.0, fontweight='bold', color=NAVY)
ax.add_patch(Rectangle((16, 68), 21, 11, fc='#F4D8D6', ec='#D9B85C', lw=1.1, ls=(0, (3, 2))))
ax.text(26.5, 73.5, r'r$_j$ : ALLOW', ha='center', va='center', fontsize=6.6, fontweight='bold', color='#B8860B')
note(49, 86.5, 'r$_j$ unreachable;\nsame action as r$_i$\n→ wastes scan\ntime and space')

# ---------------- Correlation
panel(3, 51, '#EEEAF7', '#B9A9E0', 'Correlation', '#5B2C9E', r'M(r$_i$) ∩ M(r$_j$) ≠ ∅,  neither ⊆', 'Fix: 4D-decompose')
# r_i box (upper-left) and r_j box (lower-right), overlapping region hatched
ri = (8, 22, 26, 16)   # x, y, w, h
rj = (22, 11, 24, 16)
ax.add_patch(Rectangle(ri[:2], ri[2], ri[3], fc='#DCE8F3', ec=NAVY, lw=1.4))
ax.add_patch(Rectangle(rj[:2], rj[2], rj[3], fc='#F4D8D6', ec='#B9A9E0', lw=1.1, ls=(0, (3, 2)), alpha=0.95))
ox0, oy0 = max(ri[0], rj[0]), max(ri[1], rj[1])
ox1, oy1 = min(ri[0] + ri[2], rj[0] + rj[2]), min(ri[1] + ri[3], rj[1] + rj[3])
ax.add_patch(Rectangle((ox0, oy0), ox1 - ox0, oy1 - oy0, fc='#C9B8EE', ec='#5B2C9E', hatch='////', lw=0))
ax.text(10, 34.5, r'r$_i$ : ALLOW', ha='left', va='center', fontsize=6.8, fontweight='bold', color=NAVY)
ax.text(45, 15.5, r'r$_j$ : DENY', ha='right', va='center', fontsize=6.8, fontweight='bold', color='#5B2C9E')
# overlap label placed outside both boxes, with a short leader into the hatched region
ax.annotate('overlap\n(r$_i$ wins)', xy=(ox0 + 0.3, oy0 + 0.3), xytext=(6.5, 15.5),
            ha='left', va='center', fontsize=5.8, fontstyle='italic', color='#5B2C9E',
            arrowprops=dict(arrowstyle='-', color='#5B2C9E', lw=0.7, shrinkB=1))
note(49, 39.5, 'order-dependent:\nintersection takes r$_i$’s\naction — not removed,\nbut decomposed')

fig.savefig(os.path.join(OUT, 'Figure03.png'), dpi=600)
fig.savefig(os.path.join(OUT, 'Figure03.pdf'))
