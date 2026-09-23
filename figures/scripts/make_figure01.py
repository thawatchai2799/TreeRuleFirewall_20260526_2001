"""Figure 1 - protocol-dependent dst_port domain (Definition 2).  Output: Figure01.png/.pdf at 600 dpi."""
import os
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
NAVY = '#1f3a5f'; BLUE = '#0b5a93'; RED = '#c0392b'; DRED = '#7b1a12'
fig = plt.figure(figsize=(3.347, 3.578), dpi=600)
fig.text(0.5, 0.965, 'Protocol-dependent dst_port domain', ha='center', va='center', fontsize=9.6, fontweight='bold', color=NAVY)

def axis(ax, xlabel):
    ax.set_xlim(0, 65535); ax.set_ylim(0, 1)
    ax.set_xticks([0, 16384, 32768, 49152, 65535]); ax.set_xticklabels(['0', '16k', '32k', '48k', '65,535'], fontsize=6.2)
    ax.set_yticks([]); ax.tick_params(axis='x', length=0, pad=2)
    for s in ('left', 'right', 'top'): ax.spines[s].set_visible(False)
    ax.spines['bottom'].set_linewidth(1.0)
    for x in [16384, 32768, 49152, 65535]: ax.axvline(x, color='#bbbbbb', ls=':', lw=0.5, zorder=0)
    ax.axvline(0, color='#bbbbbb', ls=':', lw=0.5, zorder=0)
    ax.set_xlabel(xlabel, fontsize=6.6, labelpad=2)

# --- top panel: TCP / UDP
ax1 = fig.add_axes([0.035, 0.55, 0.915, 0.29])
axis(ax1, 'dst_port value')
ax1.set_title('TCP / UDP :  dst_port ∈ [0, 65,535]', fontsize=7.6, fontweight='bold', color=NAVY, pad=12)
ax1.add_patch(Rectangle((0, 0.28), 65535, 0.42, fc=BLUE, ec=NAVY, lw=0.8))
ax1.text(32768, 0.49, '16-bit port number\n(2$^{16}$ = 65,536 distinct values)', ha='center', va='center', fontsize=6.9, fontweight='bold', color='white', linespacing=1.5)

# --- bottom panel: ICMP
ax2 = fig.add_axes([0.035, 0.09, 0.915, 0.29])
axis(ax2, 'dst_port value  (= ICMP type)')
ax2.set_title('ICMP :  dst_port stores ICMP type ∈ [0, 255]  (per RFC 792)', fontsize=7.2, fontweight='bold', color=NAVY, pad=12)
ax2.add_patch(Rectangle((0, 0.28), 255, 0.42, fc=DRED, ec=DRED, lw=0.8))
ax2.annotate('', xy=(600, 0.49), xytext=(9500, 0.49), arrowprops=dict(arrowstyle='-|>', color=RED, lw=1.0))
ax2.text(10500, 0.49, 'Only 256 values used (2$^8$ = 256)\n→ decomposition uses [0, 255] as the\n    domain, not [0, 65,535]', ha='left', va='center', fontsize=6.2, color=RED, linespacing=1.4)

fig.savefig(os.path.join(OUT, 'Figure01.png'), dpi=600); fig.savefig(os.path.join(OUT, 'Figure01.pdf'))
print('Figure01 written')
