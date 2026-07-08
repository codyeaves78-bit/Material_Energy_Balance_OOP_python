# Process flow diagram for MillFloor objects.
#
# Layout (drawn for any number_of_mills >= 2):
#   - Each mill is a 3-roller glyph (two bottom rollers, one top) on a base.
#   - Cane enters Mill 1 from the left; bagasse passes mill-to-mill through
#     the roller nip and exits the last mill to the boilers.
#   - Counter-current maceration: juice from mill k routes below the train
#     and up onto the BAGASSE LINE just before it enters mill k-1, so the
#     liquid wets the bagasse ahead of the mill (per factory convention).
#   - Imbibition water drops onto the bagasse line just before the last mill.
#   - Juice from mills 1 and 2 drops to a header and exits left as mixed juice.

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def plot_mill_floor(mill, show: bool = True, save_path: str = None) -> plt.Figure:
    """Draw a process flow diagram for a MillFloor. Returns the Figure."""
    n   = mill.number_of_mills
    mb  = mill.mill_balances
    mj  = mill.mixed_juice_stream
    bag = mill.bagasse_stream

    # ── Layout ────────────────────────────────────────────────────────────
    PITCH = 4.6               # mill center-to-center spacing
    GW    = 1.05              # mill glyph half-width
    L_PAD = 4.2
    R_PAD = 4.2

    DW = L_PAD + (n - 1) * PITCH + 2 * GW + R_PAD
    DH = 9.6

    Y_TTL = DH - 0.45
    Y_SUB = DH - 1.05
    Y_IMB = DH - 2.1          # imbibition supply level
    Y_BAG = 5.4               # bagasse line through the roller nips
    Y_JEX = Y_BAG - 1.05      # juice exit under each mill base
    Y_MAC = 3.0               # maceration routing level (staggered per arc)
    Y_MJ  = 1.3               # mixed juice header level

    centers = [L_PAD + GW + i * PITCH for i in range(n)]
    x_lft   = 0.55
    x_rgt   = DW - 0.55

    # ── Colors ────────────────────────────────────────────────────────────
    BAGC    = '#7b4f2e'       # cane / bagasse
    WATC    = '#2980b9'       # imbibition water
    MACC    = '#b7950b'       # maceration juice
    MJC     = '#1e8449'       # mixed juice
    ROLL_FC = '#58d68d'       # roller fill
    ROLL_EC = '#196f3d'       # roller edge
    BASEC   = '#5d6d7e'       # mill base

    fig, ax = plt.subplots(figsize=(max(10.0, DW * 0.62), DH * 0.62))
    ax.set_xlim(0, DW)
    ax.set_ylim(0, DH)
    ax.set_aspect('equal')    # keeps the rollers circular
    ax.axis('off')
    fig.patch.set_facecolor('#f8f9fa')

    # ── Drawing helpers ───────────────────────────────────────────────────
    def arr(x1, y1, x2, y2, color, lw=1.8):
        ann = ax.annotate(
            '', xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                            shrinkA=0, shrinkB=0),
            clip_on=False)
        ann.arrow_patch.set_zorder(5)

    def seg(x1, y1, x2, y2, color, lw=1.8):
        ax.plot([x1, x2], [y1, y2], color=color, lw=lw, zorder=4, clip_on=False)

    def lbl(x, y, text, ha='center', va='center', fs=8.5, color='black', bold=False):
        ax.text(x, y, text, ha=ha, va=va, fontsize=fs, color=color,
                fontweight='bold' if bold else 'normal', clip_on=False, zorder=7)

    def draw_mill(cx, i):
        """Three-roller mill glyph: two bottom rollers, one top, on a base."""
        r = 0.45
        for dx, dy in [(-0.52, -0.48), (0.52, -0.48), (0.0, 0.48)]:
            ax.add_patch(mpatches.Circle(
                (cx + dx, Y_BAG + dy), r,
                facecolor=ROLL_FC, edgecolor=ROLL_EC, lw=1.8, zorder=6))
        # base under the bottom rollers
        ax.plot([cx - GW, cx + GW], [Y_JEX + 0.10] * 2,
                color=BASEC, lw=3.5, zorder=6, solid_capstyle='round')
        name = f'Mill {i + 1}' + ('  (Last Mill)' if i == n - 1 else '')
        lbl(cx, Y_BAG + 1.25, name, fs=10.5, bold=True, color='#1a3a5c')

    # ── Title ─────────────────────────────────────────────────────────────
    lbl(DW / 2, Y_TTL, mill.name, fs=14, bold=True, color='#1c2833')
    lbl(DW / 2, Y_SUB,
        f'{mill.cane_tpd:,.0f} TPD cane  |  {n} mills  |  '
        f'imbibition {mill.imbibition_pct_on_cane:.0f}% on cane  |  '
        f'extraction {mill.mill_extraction_pct:.2f}%',
        fs=9.5, color='#566573')

    # ── Mills ─────────────────────────────────────────────────────────────
    for i, cx in enumerate(centers):
        draw_mill(cx, i)

    # ── Cane feed ─────────────────────────────────────────────────────────
    x0 = centers[0] - GW
    arr(x_lft, Y_BAG, x0, Y_BAG, BAGC, lw=2.4)
    lbl((x_lft + x0) / 2, Y_BAG + 0.35, 'Prepared Cane', fs=9.5, bold=True, color=BAGC)
    lbl((x_lft + x0) / 2, Y_BAG - 0.42,
        f'{mill.cane_tpd:,.0f} TPD\n{mill.cane_lb_hr:,.0f} lb/hr',
        fs=8, color=BAGC)

    # ── Bagasse mill-to-mill and out to boilers ───────────────────────────
    for i in range(n - 1):
        xa = centers[i] + GW
        xb = centers[i + 1] - GW
        arr(xa, Y_BAG, xb, Y_BAG, BAGC, lw=2.0)
        lbl(xa + (xb - xa) * 0.30, Y_BAG + 0.32,
            f'{mb[i]["bagasse_out_tpd"]:,.0f} TPD', fs=8, color=BAGC)

    xe = centers[-1] + GW
    arr(xe, Y_BAG, x_rgt, Y_BAG, BAGC, lw=2.4)
    lbl((xe + x_rgt) / 2, Y_BAG + 0.35, 'Bagasse to Boilers', fs=9.5, bold=True, color=BAGC)
    lbl((xe + x_rgt) / 2, Y_BAG - 0.72,
        f'{bag.flowrate_lb_hr / 2000 * 24:,.0f} TPD\n'
        f'{bag.flowrate_lb_hr:,.0f} lb/hr\n'
        f'{bag.moisture_pct:.1f}% moist | {bag.fiber_pct:.1f}% fiber',
        fs=8, color=BAGC)

    # ── Imbibition water onto bagasse entering the last mill ─────────────
    x_imb = centers[n - 2] + GW + (PITCH - 2 * GW) * 0.62 if n >= 2 else centers[0]
    arr(x_imb, Y_IMB, x_imb, Y_BAG + 0.10, WATC, lw=2.0)
    lbl(x_imb, Y_IMB + 0.30, 'Imbibition Water', fs=9.5, bold=True, color=WATC)
    lbl(x_imb - 0.25, Y_IMB - 0.55,
        f'{mill.imbibition_tph * 24:,.0f} TPD\n{mill.imbibition_gpm:,.0f} GPM',
        fs=8, color=WATC, ha='right')

    # ── Counter-current maceration:  mill k juice -> bagasse into mill k-1 ─
    # (0-indexed: juice from mill i, i >= 2, lands on the bagasse line in the
    #  gap between mill i-2 and mill i-1, staggered depth to keep arcs apart)
    for i in range(2, n):
        src   = centers[i]
        gap_l = centers[i - 2] + GW
        gap_r = centers[i - 1] - GW
        x_t   = gap_l + (gap_r - gap_l) * 0.62
        y_arc = Y_MAC - 0.45 * (i % 2)
        seg(src, Y_JEX, src, y_arc, MACC)
        seg(src, y_arc, x_t, y_arc, MACC)
        arr(x_t, y_arc, x_t, Y_BAG - 0.10, MACC)
        lbl((src + x_t) / 2, y_arc - 0.28,
            f'{mb[i]["juice_out_tpd"]:,.0f} TPD', fs=8, color=MACC)

    # ── Mixed juice from mills 1 and 2 ────────────────────────────────────
    x_hdr = x_lft + 0.9
    for i in range(min(2, n)):
        seg(centers[i], Y_JEX, centers[i], Y_MJ, MJC)
        lbl(centers[i] + 0.15, Y_MJ + 0.55,
            f'{mb[i]["juice_out_tpd"]:,.0f} TPD', fs=8, color=MJC, ha='left')
    arr(centers[min(1, n - 1)], Y_MJ, x_hdr, Y_MJ, MJC, lw=2.4)
    lbl(x_hdr - 0.25, Y_MJ - 0.35,
        f'Mixed Juice\n{mj.flow_lb_per_hr:,.0f} lb/hr\n'
        f'{mj.cu_ft_hr * 7.4805 / 60:,.0f} GPM\n'
        f'{mj.brix:.2f} brix | {mj.purity:.1f} purity',
        fs=8.5, bold=True, color=MJC, ha='left', va='top')

    fig.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=200, bbox_inches='tight')
    if show:
        plt.show()
    return fig
