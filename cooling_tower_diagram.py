# Process flow diagram for CoolingTowerSystem objects.
#
# Same conventions as the other diagrams: the drawing carries NO data —
# streams get numbered tags and the data lives in a table (in the figure,
# or in Excel cells when embedded with include_table=False).
#
# Topology (matches the notebook sketch):
#   All condensers (one box — every evap set + every pan) receive vapor and
#   cold injection water; their combined hot water returns to the cooling
#   tower. Blowdown is taken off the hot return; the tower evaporates to
#   atmosphere; cool water recirculates; makeup keeps the basin in balance.

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def _collect_streams(cts):
    """[(tag, name, lb/hr, gpm, temp_F)] for the system stream table."""
    g = cts._GPM
    return [
        (1, "Vapor from Evaporators & Pans", cts.total_vapor_lb_hr, "", ""),
        (2, "Cool Water to Condensers (delivered blend)",
            cts.total_injection_water_lb_hr,
            cts.total_injection_water_lb_hr / g, cts.delivered_water_temp_F),
        (3, "Hot Water Return to Tower", cts.hot_water_return_lb_hr,
            cts.hot_water_return_lb_hr / g, cts.hot_water_return_temp_F),
        (4, "Evaporated to Atmosphere", cts.evaporated_lb_hr,
            cts.evaporated_lb_hr / g, ""),
        (5, "Blowdown", cts.blowdown_lb_hr,
            cts.blowdown_lb_hr / g, cts.hot_water_return_temp_F),
        (6, "Makeup Water", cts.makeup_lb_hr, cts.makeup_lb_hr / g,
            cts.makeup_temp_F),
    ]


def plot_cooling_tower_system(cts, show: bool = True, save_path: str = None,
                              include_table: bool = True) -> plt.Figure:
    """Draw the cooling tower system PFD, with the system stream table and
    condenser inventory below unless include_table=False."""
    DW, DH = 22.5, 11.8

    VAPC = '#c0392b'   # vapor in
    EVPC = '#e67e22'   # evaporated to atmosphere
    HOTC = '#d35400'   # hot water return
    CLDC = '#2980b9'   # cool water supply
    BDC  = '#7f8c8d'   # blowdown
    MUC  = '#16a085'   # makeup
    EQ_EC, EQ_FC = '#2471a3', '#d6eaf8'
    GRAY = '#5d6d7e'

    if include_table:
        n_rows = 6 + len(cts.condensers)
        fig = plt.figure(figsize=(14.0, 12.4 + 0.22 * n_rows))
        gs  = fig.add_gridspec(2, 1, height_ratios=[7.3, 5.1 + 0.22 * n_rows],
                               hspace=0.03)
        ax  = fig.add_subplot(gs[0])
        axt = fig.add_subplot(gs[1])
        axt.axis('off')
    else:
        fig, ax = plt.subplots(figsize=(14.0, 7.4))
        axt = None
    fig.patch.set_facecolor('#f8f9fa')

    ax.set_xlim(0, DW)
    ax.set_ylim(0, DH)
    ax.set_aspect('equal')
    ax.axis('off')

    # ── Drawing helpers ───────────────────────────────────────────────────
    def arr(x1, y1, x2, y2, color, lw=1.8):
        ann = ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                          arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                          shrinkA=0, shrinkB=0), clip_on=False)
        ann.arrow_patch.set_zorder(4)

    def seg(pts, color, lw=1.8):
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=color, lw=lw, zorder=3, clip_on=False,
                solid_joinstyle='miter')

    def dot(x, y, color):
        ax.add_patch(mpatches.Circle((x, y), 0.09, color=color, zorder=5))

    def tag(x, y, num, color):
        ax.add_patch(mpatches.Circle((x, y), 0.30, facecolor='white',
                                     edgecolor=color, lw=1.6, zorder=6))
        ax.text(x, y, str(num), ha='center', va='center', fontsize=7.5,
                fontweight='bold', color=color, zorder=7)

    def lbl(x, y, text, fs=9, color='#1c2833', bold=False, ha='center', va='center'):
        ax.text(x, y, text, ha=ha, va=va, fontsize=fs, color=color,
                fontweight='bold' if bold else 'normal', zorder=7, clip_on=False)

    # ── Equipment ─────────────────────────────────────────────────────────
    # cooling tower: basin + tapered body + fan
    ax.add_patch(mpatches.Rectangle((3.0, 3.4), 3.0, 0.8, facecolor='white',
                                    edgecolor=EQ_EC, lw=1.8, hatch='//', zorder=2))
    ax.add_patch(mpatches.Polygon([(3.2, 4.2), (5.8, 4.2), (5.3, 8.6), (3.7, 8.6)],
                                  closed=True, facecolor=EQ_FC, edgecolor=EQ_EC,
                                  lw=2.0, zorder=2))
    ax.add_patch(mpatches.Circle((4.5, 9.05), 0.45, facecolor='white',
                                 edgecolor=EQ_EC, lw=1.8, zorder=3))
    ax.plot([4.18, 4.82], [8.83, 9.27], color=EQ_EC, lw=1.4, zorder=4)
    ax.plot([4.18, 4.82], [9.27, 8.83], color=EQ_EC, lw=1.4, zorder=4)
    lbl(4.5, 6.4, 'Cooling\nTower', fs=9, bold=True, color='#1a3a5c')
    lbl(4.5, 3.8, '', fs=7)

    # all condensers as one box (every evap set + every pan)
    ax.add_patch(mpatches.Rectangle((13.5, 5.25), 4.0, 3.5, facecolor=EQ_FC,
                                    edgecolor=EQ_EC, lw=2.0, zorder=2))
    lbl(15.5, 7.35, 'ALL\nCONDENSERS', fs=11, bold=True, color='#1a3a5c')
    lbl(15.5, 6.2, f'({len(cts.condensers)} condensers:\nevap sets + pans)',
        fs=7.5, color=GRAY)

    # ══ Streams ═══════════════════════════════════════════════════════════
    # 1 vapor in from the right
    arr(21.3, 7.0, 17.5, 7.0, VAPC, lw=2.2)
    lbl(21.3, 7.6, 'Vapor from\nEvaps & Pans', fs=8.5, bold=True, color=VAPC, ha='right')
    tag(19.2, 7.0, 1, VAPC)

    # 2 cool water: basin -> condensers
    seg([(6.0, 3.8), (12.4, 3.8), (12.4, 7.9)], CLDC, lw=2.0)
    arr(12.4, 7.9, 13.5, 7.9, CLDC, lw=2.0)
    tag(9.2, 3.8, 2, CLDC)

    # 3 hot water return: condensers -> tower top (blowdown tapped off it)
    seg([(15.5, 5.25), (15.5, 2.4), (2.6, 2.4), (2.6, 8.2)], HOTC, lw=2.0)
    arr(2.6, 8.2, 3.66, 8.2, HOTC, lw=2.0)
    tag(9.0, 2.4, 3, HOTC)

    # 4 evaporated to atmosphere
    arr(4.5, 9.5, 4.5, 10.9, EVPC, lw=2.0)
    lbl(4.5, 11.25, 'Evaporated', fs=9.5, bold=True, color=EVPC)
    tag(4.5, 10.2, 4, EVPC)

    # 5 blowdown off the hot return
    dot(2.6, 6.2, HOTC)
    arr(2.6, 6.2, 0.7, 6.2, BDC, lw=2.0)
    lbl(0.7, 6.62, 'Blowdown', fs=9.5, bold=True, color=BDC, ha='left')
    tag(1.6, 6.2, 5, BDC)

    # 6 makeup into the basin (keeps everything in balance)
    arr(8.0, 4.2, 6.0, 4.2, MUC, lw=2.0) # new will be start at x = 9, end x = 6, raise y a bit
    lbl(7.5, 4.6, 'Makeup', fs=9.5, bold=True, color=MUC, ha='left')
    tag(7.0, 4.2, 6, MUC)

    lbl(DW / 2, DH - 0.15, f'{cts.name} — PFD', fs=15, bold=True)

    # ══ Tables ════════════════════════════════════════════════════════════
    if not include_table:
        if save_path:
            fig.savefig(save_path, dpi=170, bbox_inches='tight')
        if show:
            plt.show()
        return fig

    def style(tab, name_col):
        tab.auto_set_font_size(False)
        tab.set_fontsize(8.5)
        for (r, c), cell in tab.get_celld().items():
            cell.set_edgecolor('#bfbfbf')
            if r == 0:
                cell.set_facecolor('#305496')
                cell.set_text_props(color='white', fontweight='bold', ha='center')
            elif r % 2 == 0:
                cell.set_facecolor('#f2f2f2')
            if c == name_col and r > 0:
                cell.set_text_props(ha='left')

    def num(v, f='{:,.0f}'):
        return f.format(v) if isinstance(v, (int, float)) else '-'

    rows = _collect_streams(cts)
    cells = [[str(r[0]), r[1], num(r[2]), num(r[3]), num(r[4], '{:.1f}')]
             for r in rows]
    tab = axt.table(cellText=cells,
                    colLabels=['#', 'Stream', 'lb/hr', 'GPM', '°F'],
                    cellLoc='right', bbox=[0.03, 0.62, 0.94, 0.36])
    style(tab, name_col=1)
    tab.auto_set_column_width([0, 1, 2, 3, 4])

    axt.text(0.5, 0.56, 'CONDENSER INVENTORY', transform=axt.transAxes,
             fontsize=10.5, fontweight='bold', color='#305496', ha='center')
    inv = [[n, num(c.vapor_flow_lb_hr), num(c.vapor_sat_temp_F, '{:.1f}'),
            num(c.heat_load_btu_hr / 1e6, '{:.3f}'),
            num(c.injection_water_flow_lb_hr),
            num(c.injection_water_flow_lb_hr / cts._GPM),
            num(c.water_outlet_temp_F, '{:.1f}'),
            num(c.total_outlet_flow_lb_hr)]
           for n, c in cts.condensers]
    inv.append(['Total', num(cts.total_vapor_lb_hr), '-',
                num(cts.total_heat_load_btu_hr / 1e6, '{:.3f}'),
                num(cts.total_injection_water_lb_hr),
                num(cts.total_injection_water_lb_hr / cts._GPM), '-',
                num(cts.hot_water_return_lb_hr)])
    tab2 = axt.table(cellText=inv,
                     colLabels=['Condenser', 'Vapor lb/hr', 'Sat T °F',
                                'MM BTU/hr', 'Inj lb/hr', 'Inj GPM',
                                'Out T °F', 'Total lb/hr'],
                     cellLoc='right', bbox=[0.03, 0.10, 0.94, 0.44])
    style(tab2, name_col=0)
    tab2.auto_set_column_width(list(range(8)))

    bal = cts.balance_check
    axt.text(0.03, 0.04,
             f"Balance:  in (vapor + makeup) = {bal['in_lb_hr']:,.0f} lb/hr    "
             f"out (evap + blowdown + surplus) = {bal['out_lb_hr']:,.0f} lb/hr    "
             f"net = {bal['diff_lb_hr']:,.2f} lb/hr",
             transform=axt.transAxes, fontsize=9, color='#1c2833', fontweight='bold')

    if save_path:
        fig.savefig(save_path, dpi=170, bbox_inches='tight')
    if show:
        plt.show()
    return fig
