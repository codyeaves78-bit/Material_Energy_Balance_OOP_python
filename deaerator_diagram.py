# Process flow diagram for Deaerator objects.
#
# Single direct-contact-heater box: live steam and feedwater enter, vent
# escapes the top, deaerated water leaves the bottom right. Same drawing
# conventions (colors, box style, label layout) as evaporator_diagram.py's
# plot_pre_diagram, scaled down to a simpler three-stream unit.

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def plot_deaerator_diagram(
    da,
    name: str = "Deaerator",
    show: bool = True,
    save_path: str = None,
) -> plt.Figure:
    """Draw a PFD for a single Deaerator. Returns the matplotlib Figure."""
    SC = '#c0392b'   # steam
    JC = '#154360'   # water
    BC = '#1e8449'   # vent

    BOX_EC = '#2471a3'
    BOX_FC = '#d6eaf8'

    DW    = 12.0
    DH    = 11.8
    cx    = DW / 2
    BOX_W = 3.8

    Y_TTL   = DH - 0.25
    Y_ROUTE = DH - 1.70
    Y_TOP   = 8.10
    Y_BOT   = 2.70
    Y_MID   = (Y_TOP + Y_BOT) / 2
    Y_FOOT  = 0.40

    x_lft = 1.0
    x_rgt = DW - 1.0

    fig, ax = plt.subplots(figsize=(10.0, 9.5))
    ax.set_xlim(0, DW)
    ax.set_ylim(0.2, DH)
    ax.axis('off')
    fig.patch.set_facecolor('#f8f9fa')

    def arr(x1, y1, x2, y2, color, lw=1.8, ls='solid'):
        ann = ax.annotate(
            '', xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                            linestyle=ls, shrinkA=0, shrinkB=0),
            clip_on=False,
        )
        ann.arrow_patch.set_zorder(5)

    def seg(x1, y1, x2, y2, color, lw=1.8, ls='solid'):
        ax.plot([x1, x2], [y1, y2], color=color, lw=lw, ls=ls, zorder=4, clip_on=False)

    def lbl(x, y, text, ha='center', va='center', fs=8.5, color='black', bold=False):
        ax.text(x, y, text, ha=ha, va=va, fontsize=fs,
                color=color, fontweight='bold' if bold else 'normal',
                clip_on=False, zorder=6)

    # Title
    lbl(DW / 2, Y_TTL, name, fs=14, bold=True, color='#1c2833')

    # Body
    rect = mpatches.FancyBboxPatch(
        (cx - BOX_W / 2, Y_BOT), BOX_W, Y_TOP - Y_BOT,
        boxstyle='round,pad=0.06', lw=2.0,
        edgecolor=BOX_EC, facecolor=BOX_FC, zorder=3)
    ax.add_patch(rect)

    # Labels inside body
    lbl(cx, Y_MID + 1.60, 'Deaerator',                                     fs=11,  bold=True, color='#1a3a5c')
    lbl(cx, Y_MID + 1.00, f'{da.psia:.2f} psia',                           fs=9,   color='#566573')
    lbl(cx, Y_MID + 0.60, f'{da.psia - 14.696:.2f} psig',                  fs=8,   color='#566573')
    lbl(cx, Y_MID + 0.05, f'T_sat: {da._water_out_state.T:.1f} °F',        fs=8.5, color=JC)
    lbl(cx, Y_MID - 0.40, f'Steam h_fg: {da._steam_state.h_fg:.1f} BTU/lb', fs=7.5, color=SC)
    lbl(cx, Y_MID - 0.80, f'Vent: {da.vent_pct:.1f} %',                    fs=7.5, color=BC)

    # Steam In (enters left side, mid-height)
    arr(x_lft, Y_MID, cx - BOX_W / 2, Y_MID, color=SC, lw=2.2)
    lbl(x_lft, Y_MID + 0.68, 'Steam In',                                   ha='left', fs=9,   color=SC, bold=True)
    lbl(x_lft, Y_MID + 0.28, f'{da.steam_flow_lb_hr:,.0f} lb/hr',          ha='left', fs=8.5, color=SC)
    lbl(x_lft, Y_MID - 0.10, f'{da.psia:.2f} psia',                        ha='left', fs=7.5, color=SC)

    # Vent exits top, routes right (dashed — to atmosphere)
    bx = cx - BOX_W * 0.10
    seg(bx, Y_TOP, bx, Y_ROUTE, color=BC, lw=1.8)
    arr(bx, Y_ROUTE, x_rgt, Y_ROUTE, color=BC, lw=1.8, ls='dashed')
    lbl(x_rgt, Y_ROUTE + 0.52, 'Vent to Atmosphere',                       ha='right', fs=9,   color=BC, bold=True)
    lbl(x_rgt, Y_ROUTE + 0.14, f'{da.vent_flow_lb_hr:,.0f} lb/hr',         ha='right', fs=8.5, color=BC)
    lbl(x_rgt, Y_ROUTE - 0.22, '14.7 psia',                                ha='right', fs=7.5, color=BC)

    # Feedwater In (top left)
    arr(x_lft, Y_TOP, cx - BOX_W / 2, Y_TOP, color=JC, lw=2.2)
    lbl(x_lft, Y_TOP + 0.62, 'Feedwater In',                               ha='left', fs=9,   color=JC, bold=True)
    lbl(x_lft, Y_TOP + 0.22, f'{da.water_in_lb_hr:,.0f} lb/hr',            ha='left', fs=8.5, color=JC)
    lbl(x_lft, Y_TOP - 0.17, f'{da.water_in_deg_F:.1f} °F',                ha='left', fs=7.5, color=JC)

    # Deaerated Water Out (bottom right)
    arr(cx + BOX_W / 2, Y_BOT, x_rgt, Y_BOT, color=JC, lw=2.2)
    lbl(x_rgt, Y_BOT + 0.62, 'Water Out',                                  ha='right', fs=9,   color=JC, bold=True)
    lbl(x_rgt, Y_BOT + 0.22, f'{da.water_out_flow_lb_hr:,.0f} lb/hr',      ha='right', fs=8.5, color=JC)
    lbl(x_rgt, Y_BOT - 0.17, f'{da._water_out_state.T:.1f} °F',            ha='right', fs=7.5, color=JC)

    # Footer
    lbl(DW / 2, Y_FOOT,
        f'Steam In: {da.steam_flow_lb_hr:,.0f} lb/hr   |   '
        f'Water In: {da.water_in_lb_hr:,.0f} lb/hr   |   '
        f'Water Out: {da.water_out_flow_lb_hr:,.0f} lb/hr   |   '
        f'Vent: {da.vent_flow_lb_hr:,.0f} lb/hr',
        fs=8, color='#666666')

    fig.tight_layout(pad=0.4)
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    return fig
