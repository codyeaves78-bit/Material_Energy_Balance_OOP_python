# Process flow diagram for JuiceHeatingStation objects.
#
# Two layouts, matching the notebook sketch:
#   parallel — juice header along the bottom feeds each heater; hot juice
#              collects in a top header and leaves right ("to flash tank").
#   series   — juice passes through the heaters left-to-right.
# Every heater gets heating steam in the top and condensate out the bottom.
# The drawing carries NO data — numbered tags only; the data lives in the
# tables (in the figure, or in Excel cells when include_table=False).

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def _collect_streams(st):
    """[(tag, name, lb/hr, temp_F, psia)] in tag order for either mode."""
    rows = []
    k = 1
    if st.mode == 'parallel':
        rows.append((k, "Juice In", st.cold_stream.flow_lb_per_hr,
                     st.cold_stream.temp_deg_F, "")); k += 1
        for h in st.heaters:
            rows.append((k, f"Juice to {h.name}", h.cold_stream.flow_lb_per_hr,
                         h.cold_stream.temp_deg_F, "")); k += 1
        for h in st.heaters:
            rows.append((k, f"Hot Juice from {h.name}", h.juice_out.flow_lb_per_hr,
                         h.juice_out.temp_deg_F, "")); k += 1
        rows.append((k, "Hot Juice (combined)", st.juice_out.flow_lb_per_hr,
                     st.juice_out.temp_deg_F, "")); k += 1
    else:  # series
        rows.append((k, "Juice In", st.cold_stream.flow_lb_per_hr,
                     st.cold_stream.temp_deg_F, "")); k += 1
        for h in st.heaters[:-1]:
            rows.append((k, f"Juice out of {h.name}", h.juice_out.flow_lb_per_hr,
                         h.juice_out.temp_deg_F, "")); k += 1
        rows.append((k, "Hot Juice Out", st.juice_out.flow_lb_per_hr,
                     st.juice_out.temp_deg_F, "")); k += 1
    for h in st.heaters:
        rows.append((k, f"Steam to {h.name}", h.steam_required_lb_per_hr,
                     h.hot_stream.T, h.hot_stream.P)); k += 1
    for h in st.heaters:
        rows.append((k, f"Condensate from {h.name}", h.steam_required_lb_per_hr,
                     h.hot_stream.T, h.hot_stream.P)); k += 1
    return rows


def plot_juice_heating_station(st, show: bool = True, save_path: str = None,
                               include_table: bool = True) -> plt.Figure:
    """Draw the station PFD (parallel or series per st.mode)."""
    n = len(st.heaters)
    PITCH, HW, HH = 5.6, 1.7, 0.65          # heater half-width / half-height
    L_PAD = 2.4
    DW = L_PAD + 1.8 + (n - 1) * PITCH + HW + 4.2
    DH = 11.0
    CY = 6.05                                # heater centerline
    centers = [L_PAD + 1.8 + i * PITCH for i in range(n)]

    JC   = '#1e8449'   # juice
    STMC = '#c0392b'   # heating steam
    CNDC = '#7f8c8d'   # condensate
    EQ_EC, EQ_FC = '#2471a3', '#d6eaf8'
    GRAY = '#5d6d7e'

    if include_table:
        rows_n = len(_collect_streams(st)) + n + 2
        tab_h = 0.30 * (rows_n + 4)
        fig = plt.figure(figsize=(max(10.5, DW * 0.62), DH * 0.62 + tab_h))
        gs  = fig.add_gridspec(2, 1, height_ratios=[DH * 0.62, tab_h], hspace=0.05)
        ax  = fig.add_subplot(gs[0])
        axt = fig.add_subplot(gs[1])
        axt.axis('off')
    else:
        fig, ax = plt.subplots(figsize=(max(10.5, DW * 0.62), DH * 0.62))
        axt = None
    fig.patch.set_facecolor('#f8f9fa')

    ax.set_xlim(0, DW)
    ax.set_ylim(0, DH)
    ax.set_aspect('equal')
    ax.axis('off')

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

    def heater(cx, name):
        """Shell-and-tube glyph: rectangle with a tube bundle inside."""
        ax.add_patch(mpatches.Rectangle((cx - HW, CY - HH), 2 * HW, 2 * HH,
                                        facecolor=EQ_FC, edgecolor=EQ_EC,
                                        lw=1.8, zorder=2))
        for dy in (-0.3, 0.0, 0.3):
            ax.plot([cx - HW + 0.25, cx + HW - 0.25], [CY + dy] * 2,
                    color=EQ_EC, lw=1.0, zorder=3)
        # two-line label so it clears the riser and condensate lines
        lbl(cx, CY - HH - 0.55, name.replace(' ', '\n', 1) if ' ' in name else name,
            fs=7.5, color=GRAY, va='top')

    for cx, h in zip(centers, st.heaters):
        heater(cx, h.name)

    # ── steam in (top) and condensate out (bottom) for every heater ──────
    rows = _collect_streams(st)
    steam_tag0 = (2 * n + 3) if st.mode == 'parallel' else (n + 2)
    for i, cx in enumerate(centers):
        arr(cx - 0.3, 8.1, cx - 0.3, CY + HH, STMC)
        lbl(cx - 0.3, 8.5, 'Heating Steam', fs=8, bold=True, color=STMC)
        tag(cx - 0.3, 7.4, steam_tag0 + i, STMC)

        seg([(cx + 1.2, CY - HH), (cx + 1.2, 4.5)], CNDC)
        arr(cx + 1.2, 4.5, cx + 2.6, 4.5, CNDC)
        lbl(cx + 2.7, 4.5, 'Cond.', fs=8, bold=True, color=CNDC, ha='left')
        tag(cx + 1.9, 4.5, steam_tag0 + n + i, CNDC)

    # ── juice path ────────────────────────────────────────────────────────
    if st.mode == 'parallel':
        # bottom feed header with a riser into each heater
        seg([(0.8, 3.2), (centers[-1] - 1.0, 3.2)], JC, lw=2.2)
        lbl(0.8, 3.6, 'Juice', fs=9.5, bold=True, color=JC, ha='left')
        tag(1.6, 3.2, 1, JC)
        for i, cx in enumerate(centers):
            if i < n - 1:
                dot(cx - 1.0, 3.2, JC)
            arr(cx - 1.0, 3.2, cx - 1.0, CY - HH, JC)
            tag(cx - 1.0, 4.3, 2 + i, JC)
        # top collection header out to the right
        seg([(centers[0] + 1.0, 9.2), (DW - 1.2, 9.2)], JC, lw=2.2)
        arr(DW - 1.2, 9.2, DW - 0.5, 9.2, JC, lw=2.2)
        lbl(DW - 0.5, 9.65, 'Hot Juice', fs=9.5, bold=True, color=JC, ha='right')
        for i, cx in enumerate(centers):
            seg([(cx + 1.0, CY + HH), (cx + 1.0, 9.2)], JC)
            if i > 0:
                dot(cx + 1.0, 9.2, JC)
            tag(cx + 1.0, 7.95, n + 2 + i, JC)
        tag(centers[-1] + 2.6, 9.2, 2 * n + 2, JC)
    else:
        # series: straight through, left to right
        arr(0.8, CY, centers[0] - HW, CY, JC, lw=2.2)
        lbl(0.8, CY + 0.45, 'Juice', fs=9.5, bold=True, color=JC, ha='left')
        tag(1.5, CY, 1, JC)
        for i in range(n - 1):
            xa = centers[i] + HW
            xb = centers[i + 1] - HW
            arr(xa, CY, xb, CY, JC, lw=2.2)
            tag((xa + xb) / 2, CY, 2 + i, JC)
        arr(centers[-1] + HW, CY, DW - 0.5, CY, JC, lw=2.2)
        lbl(DW - 0.5, CY + 0.45, 'Hot Juice', fs=9.5, bold=True, color=JC, ha='right')
        tag(centers[-1] + HW + 1.4, CY, n + 1, JC)

    mode_txt = f' — {st.mode.title()}' if n > 1 else ''
    lbl(DW / 2, DH - 0.15, f'{st.name}{mode_txt} — PFD', fs=14, bold=True)

    # ── Tables ────────────────────────────────────────────────────────────
    if not include_table:
        if save_path:
            fig.savefig(save_path, dpi=170, bbox_inches='tight')
        if show:
            plt.show()
        return fig

    def style(tab):
        tab.auto_set_font_size(False)
        tab.set_fontsize(8.5)
        for (r, c), cell in tab.get_celld().items():
            cell.set_edgecolor('#bfbfbf')
            if r == 0:
                cell.set_facecolor('#305496')
                cell.set_text_props(color='white', fontweight='bold', ha='center')
            elif r % 2 == 0:
                cell.set_facecolor('#f2f2f2')
            if c in (0, 1) and r > 0:
                cell.set_text_props(ha='left')

    def num(v, f='{:,.0f}'):
        return f.format(v) if isinstance(v, (int, float)) else str(v) if v else '-'

    cells = [[str(r[0]), r[1], num(r[2]), num(r[3], '{:.1f}'), num(r[4], '{:.1f}')]
             for r in rows]
    tab = axt.table(cellText=cells,
                    colLabels=['#', 'Stream', 'lb/hr', '°F', 'psia'],
                    cellLoc='right', bbox=[0.06, 0.44, 0.88, 0.54])
    style(tab)
    tab.auto_set_column_width([0, 1, 2, 3, 4])

    axt.text(0.5, 0.38, 'HEATER PERFORMANCE', transform=axt.transAxes,
             fontsize=9.5, fontweight='bold', color='#305496', ha='center')
    perf = [[h.name, num(h.cold_stream.flow_lb_per_hr),
             num(h.cold_stream.temp_deg_F, '{:.1f}'),
             num(h.juice_out_temp_degF, '{:.1f}'), num(h.LMTD_degF, '{:.1f}'),
             num(h.Q_btu_per_hr), num(h.U, '{:.0f}'),
             num(h.required_area_ft2), num(h.installed_area_ft2),
             num(h.steam_required_lb_per_hr)]
            for h in st.heaters]
    perf.append(['TOTAL', '', '', '', '', num(st.total_duty_btu_hr), '', '', '',
                 num(st.total_steam_lb_hr)])
    tab2 = axt.table(cellText=perf,
                     colLabels=['Heater', 'Juice\nlb/hr', 'T in\n°F', 'T out\n°F',
                                'LMTD\n°F', 'Duty\nBTU/hr', 'U', 'Req\nft²',
                                'Inst\nft²', 'Steam\nlb/hr'],
                     cellLoc='right', bbox=[0.03, 0.02, 0.94, 0.32])
    style(tab2)
    tab2.auto_set_column_width(list(range(10)))

    if save_path:
        fig.savefig(save_path, dpi=170, bbox_inches='tight')
    if show:
        plt.show()
    return fig
