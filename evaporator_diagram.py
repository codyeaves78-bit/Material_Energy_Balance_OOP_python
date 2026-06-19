# Process flow diagram for EvaporatorSet objects.
#
# Vapor routing between effects (4-segment inverted-U):
#   1. UP   from body top-centre to Y_ROUTE (above all bodies)
#   2. RIGHT along Y_ROUTE to the midpoint of the gap between bodies
#   3. DOWN  in the open gap space (x_turn) to Y_MID
#   4. RIGHT with arrowhead into the centre of the next body's left side
#
# Bleeds exit from slightly LEFT of body top-centre so they never cross
# the rightward horizontal routing segment, and are drawn last (on top).
#
# Pressure labels show psia on one line and psig (>atm) or "Hg Vac (<atm)
# on the next line.  Bodies also show BPE, U-calc, and U-dessin.

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from EvaporatorSet import EvaporatorSet
from evaporator_functions import convert_psia_to_inHgVac


def _fmt_p2(psia: float) -> str:
    """Secondary pressure label: psig above atm, inches-Hg vacuum below."""
    if psia >= 14.696:
        return f'{psia - 14.696:.2f} psig'
    return f'{convert_psia_to_inHgVac(psia):.2f}" Hg Vac'


def plot_set_diagram(
    evap_set: EvaporatorSet,
    set_name: str = "",
    show: bool = True,
    save_path: str = None,
) -> plt.Figure:
    """
    Draw a process flow diagram for a single EvaporatorSet.
    Returns the matplotlib Figure.
    """
    n     = evap_set.number_of_effects
    evaps = evap_set.evaporator_list
    steam = evap_set.supply_steam

    # ── Layout ────────────────────────────────────────────────────────────
    BOX_W   = 3.0
    BOX_GAP = 2.0
    L_PAD   = 3.6
    R_PAD   = 3.6

    DW = L_PAD + n * BOX_W + (n - 1) * BOX_GAP + R_PAD
    DH = 11.8

    Y_TTL   = DH - 0.25
    Y_BLEED = DH - 0.85
    Y_ROUTE = DH - 1.70   # horizontal vapor pipe level above bodies
    Y_TOP   = 8.10        # TOP  edge of body = vapor exit
    Y_BOT   = 2.70        # BOT  edge of body = juice connection (lowered for label room)
    Y_MID   = (Y_TOP + Y_BOT) / 2   # MID height = steam/vapor inlet
    Y_COND  = 1.45
    Y_FOOT  = 0.40

    centers = [L_PAD + BOX_W / 2 + i * (BOX_W + BOX_GAP) for i in range(n)]
    x_lft   = 0.12 * L_PAD
    x_rgt   = DW - 0.12 * R_PAD

    SC = '#c0392b'
    VC = '#d35400'
    JC = '#154360'
    CC = '#7f8c8d'
    BC = '#1e8449'
    BOX_EC = '#2471a3'
    BOX_FC = '#d6eaf8'

    fig_w_in = max(10.0, DW * 0.72)
    fig, ax  = plt.subplots(figsize=(fig_w_in, 9.5))
    ax.set_xlim(0, DW)
    ax.set_ylim(0.2, DH)
    ax.axis('off')
    fig.patch.set_facecolor('#f8f9fa')

    # ── Drawing helpers ───────────────────────────────────────────────────
    def arr(x1, y1, x2, y2, color, lw=1.8, ls='solid'):
        ann = ax.annotate(
            '', xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                            linestyle=ls, shrinkA=0, shrinkB=0),
            clip_on=False,
        )
        ann.arrow_patch.set_zorder(5)

    def seg(x1, y1, x2, y2, color, lw=1.8, ls='solid'):
        ax.plot([x1, x2], [y1, y2], color=color, lw=lw, ls=ls,
                zorder=4, clip_on=False)

    def lbl(x, y, text, ha='center', va='center',
            fs=8.5, color='black', bold=False):
        ax.text(x, y, text, ha=ha, va=va, fontsize=fs,
                color=color, fontweight='bold' if bold else 'normal',
                clip_on=False, zorder=6)

    # ── Title ─────────────────────────────────────────────────────────────
    lbl(DW / 2, Y_TTL, set_name or 'Evaporator Set', fs=14, bold=True, color='#1c2833')

    # ── Effect bodies ──────────────────────────────────────────────────────
    for i, (cx, evap) in enumerate(zip(centers, evaps)):
        rect = mpatches.FancyBboxPatch(
            (cx - BOX_W / 2, Y_BOT), BOX_W, Y_TOP - Y_BOT,
            boxstyle='round,pad=0.06', lw=2.0,
            edgecolor=BOX_EC, facecolor=BOX_FC, zorder=3)
        ax.add_patch(rect)

        vp = evap.vapor_pressure_psia

        lbl(cx, Y_MID + 1.95, f'Effect {i + 1}',           fs=11,  bold=True, color='#1a3a5c')
        lbl(cx, Y_MID + 1.32, f'{evap.area_ft2:,.0f} ft²', fs=9,   color='#566573')

        # Pressure — psia then psig / Hg-vac
        lbl(cx, Y_MID + 0.70, f'P: {vp:.2f} psia',  fs=8.5, color='#1a5276')
        lbl(cx, Y_MID + 0.30, _fmt_p2(vp),           fs=8,   color='#1a5276')

        # Temperatures
        lbl(cx, Y_MID - 0.15, f'Cald: {evap.calandria_side.sat_temp_deg_F:.1f} °F', fs=8, color=SC)
        lbl(cx, Y_MID - 0.55, f'Juice: {evap.juice_side_out.temp_deg_F:.1f} °F',    fs=8, color=JC)

        # Boiling point elevation
        lbl(cx, Y_MID - 0.92, f'BPE: {evap.bpe_juice:.2f} °F', fs=7.5, color='#6c3483')

        # Heat transfer coefficients
        lbl(cx, Y_MID - 1.28, f'U = {evap.heat_xfer_U:.1f}', fs=7.5, color='#117a65')
        lbl(cx, Y_MID - 1.63,
            f'Ud = {evap.dessin_U:.1f}  BTU/hr·ft²·°F', fs=7, color='#555555')

        # Latent heats
        lbl(cx, Y_MID - 1.98,
            f'hfg stm: {evap.calandria_side.h_fg:.1f} BTU/lb', fs=7, color='#922b21')
        lbl(cx, Y_MID - 2.32,
            f'hfg vap: {evap.juice_side_out.latent_heat_btu_per_lb:.1f} BTU/lb', fs=7, color='#1a5276')

    # ── Supply steam → centre-left of body 1 ──────────────────────────────
    arr(x_lft, Y_MID, centers[0] - BOX_W / 2, Y_MID, color=SC, lw=2.2)
    lbl(x_lft, Y_MID + 0.68, 'Supply Steam',                           ha='left', fs=9,   color=SC, bold=True)
    lbl(x_lft, Y_MID + 0.28, f'{steam.flow_lb_per_hr:,.0f} lb/hr',    ha='left', fs=8.5, color=SC)
    lbl(x_lft, Y_MID - 0.10, f'{steam.P_psia:.1f} psia',              ha='left', fs=7.5, color=SC)
    lbl(x_lft, Y_MID - 0.44, _fmt_p2(steam.P_psia),                   ha='left', fs=7.5, color=SC)

    # ── Condensate ────────────────────────────────────────────────────────
    for i, (cx, evap) in enumerate(zip(centers, evaps)):
        arr(cx, Y_BOT, cx, Y_COND + 0.12, color=CC, lw=1.5)
        lbl(cx, Y_COND - 0.10,
            f'Condensate\n{evap.condensate_out:,.0f} lb/hr', fs=7.5, color=CC)

    # ── Vapor routing: top-centre exit, inverted-U path, then bleed ───────
    for i, (cx, evap) in enumerate(zip(centers, evaps)):
        bleed     = evap.vapor_bleed.flow_lb_per_hr
        vapor_fwd = evap.vapor_out.flow_lb_per_hr - bleed

        if i < n - 1:
            next_cx = centers[i + 1]
            x_gap_l = cx      + BOX_W / 2   # right edge of body i
            x_gap_r = next_cx - BOX_W / 2   # left  edge of body i+1
            x_turn  = (x_gap_l + x_gap_r) / 2   # centre of gap — descent here

            # Segment 1 — UP
            seg(cx, Y_TOP, cx, Y_ROUTE, color=VC, lw=1.8)
            # Segment 2 — RIGHT to gap centre
            seg(cx, Y_ROUTE, x_turn, Y_ROUTE, color=VC, lw=1.8)
            # Segment 3 — DOWN in open gap space
            seg(x_turn, Y_ROUTE, x_turn, Y_MID, color=VC, lw=1.8)
            # Segment 4 — RIGHT with arrowhead into next body
            arr(x_turn, Y_MID, x_gap_r, Y_MID, color=VC, lw=1.8)

            # Labels on segment 2 (horizontal above body i — clear of both bodies)
            mid_x = (cx + x_turn) / 2
            lbl(mid_x, Y_ROUTE + 0.30, f'Vapor {i + 1}→{i + 2}', fs=8, color=VC, bold=True)
            lbl(mid_x, Y_ROUTE - 0.12, f'{vapor_fwd:,.0f} lb/hr',  fs=8, color=VC)

        else:
            # Last body — exits top, routes right to condenser
            seg(cx, Y_TOP, cx, Y_ROUTE, color=VC, lw=1.8)
            arr(cx, Y_ROUTE, x_rgt, Y_ROUTE, color=VC, lw=1.8, ls='dashed')
            lbl(x_rgt, Y_ROUTE + 0.52, 'To Condenser',             ha='right', fs=9,   color=VC, bold=True)
            lbl(x_rgt, Y_ROUTE + 0.14, f'{vapor_fwd:,.0f} lb/hr',  ha='right', fs=8.5, color=VC)
            lbl(x_rgt, Y_ROUTE - 0.22,
                f'{evap.vapor_pressure_psia:.2f} psia | {evap.vapor_temperature:.1f} °F',
                ha='right', fs=7.5, color=VC)

        # Vapor bleed — drawn AFTER vapor routing so it renders on top.
        # Exit from slightly LEFT of body top-centre so it never crosses the
        # rightward horizontal routing segment (which starts at cx and goes right).
        if bleed > 0.1:
            bx = cx - BOX_W * 0.20   # left of centre → clear of the rightward routing
            arr(bx, Y_TOP, bx, Y_BLEED, color=BC, lw=1.5)
            lbl(bx - 0.18, (Y_TOP + Y_BLEED) / 2 + 0.08,
                f'Bleed\n{bleed:,.0f} lb/hr', ha='right', fs=7.5, color=BC)

    # ── Juice stream at Y_BOT ─────────────────────────────────────────────
    juice_in = evap_set.juice_in

    arr(x_lft, Y_BOT, centers[0] - BOX_W / 2, Y_BOT, color=JC, lw=2.2)
    lbl(x_lft, Y_BOT + 0.62, 'Juice In',                                ha='left', fs=9,   color=JC, bold=True)
    lbl(x_lft, Y_BOT + 0.22, f'{juice_in.flow_lb_per_hr:,.0f} lb/hr',  ha='left', fs=8.5, color=JC)
    lbl(x_lft, Y_BOT - 0.17,
        f'{juice_in.brix:.2f}° Brix | {juice_in.temp_deg_F:.1f} °F',
        ha='left', fs=7.5, color=JC)

    for i in range(n - 1):
        cx, next_cx = centers[i], centers[i + 1]
        jout  = evaps[i].juice_side_out
        mid_x = (cx + next_cx) / 2
        arr(cx + BOX_W / 2, Y_BOT, next_cx - BOX_W / 2, Y_BOT, color=JC, lw=1.8)
        lbl(mid_x, Y_BOT - 0.25, f'{jout.flow_lb_per_hr:,.0f} lb/hr', fs=8, color=JC)
        lbl(mid_x, Y_BOT - 0.60, f'{jout.brix:.2f}° Brix',            fs=8, color=JC)

    last_out = evaps[-1].juice_side_out
    arr(centers[-1] + BOX_W / 2, Y_BOT, x_rgt, Y_BOT, color=JC, lw=2.2)
    lbl(x_rgt, Y_BOT + 0.62, 'Syrup Out',                               ha='right', fs=9,   color=JC, bold=True)
    lbl(x_rgt, Y_BOT + 0.22, f'{last_out.flow_lb_per_hr:,.0f} lb/hr',  ha='right', fs=8.5, color=JC)
    lbl(x_rgt, Y_BOT - 0.17,
        f'{last_out.brix:.2f}° Brix | {last_out.temp_deg_F:.1f} °F',
        ha='right', fs=7.5, color=JC)

    # ── Footer ────────────────────────────────────────────────────────────
    u_parts = [f'Eff {i + 1}: U={e.U_ratio:.3f}' for i, e in enumerate(evaps)]
    lbl(DW / 2, Y_FOOT,
        'U Ratios (calc / dessin)  —  ' + '   |   '.join(u_parts),
        fs=8, color='#666666')

    fig.tight_layout(pad=0.4)
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    return fig


def plot_all_diagrams(
    evap_sets: list,
    online: list,
    set_names: list = None,
    show: bool = True,
    save_prefix: str = None,
) -> list:
    """
    Plot one process flow diagram per active EvaporatorSet.
    Returns list of Figure objects (one per active set).
    """
    figs = []
    for i, (evap_set, on) in enumerate(zip(evap_sets, online)):
        if not on:
            continue
        name = set_names[i] if (set_names and i < len(set_names)) else f'Set {i + 1}'
        path = f'{save_prefix}_set{i + 1}.png' if save_prefix else None
        figs.append(plot_set_diagram(evap_set, set_name=name, show=show, save_path=path))
    return figs
