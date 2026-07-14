# Shared PFD + Excel export for turbine group classes
# (MillTurbines, CanePrepTurbines, AuxillaryTurbines).
#
# The drawing keeps it simple: ONE sideways trapezoid turbine (small face
# left, large face right) with labels only —
#   (1) live steam in at the top-left corner,
#   (2) exhaust out of the bottom-right corner,
#   (HP) shaft power out of the center of the right face.
# Every turbine in the group gets a ROW in the tables, not its own glyph.

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def _fmt_x(x):
    return "Superheat" if x is None or x >= 1.0 else x


def _group_info(group):
    """Duck-typed adapter for the three turbine group classes.

    Returns dict with: title, sheet_name, tfh_list (or None), skip flags,
    and the per-turbine row data used by both the figure and Excel tables.
    """
    if hasattr(group, 'mill_turbines'):
        tfh   = group.mill_turbines['hp_ton_fiber_hr']
        skip  = [False] * len(group.turbines)
        title = f"Mill Turbines — {group.tons_fiber_hr:,.0f} Ton Fiber/hr"
        sheet = "Mill Turbines"
    elif hasattr(group, 'cane_prep_turbines'):
        tfh   = group.cane_prep_turbines['hp_ton_fiber_hr']
        skip  = [v == 0 for v in tfh]
        title = f"Cane Prep Turbines — {group.tons_fiber_hr:,.0f} Ton Fiber/hr"
        sheet = "Cane Prep Turbines"
    else:  # AuxillaryTurbines
        tfh   = None
        skip  = [hp == 0 for hp in group.auxillary_turbines['hp_list']]
        title = group.group_name
        sheet = group.group_name[:31]

    rows = []
    for i, trb in enumerate(group.turbines):
        if skip[i]:
            continue
        ex = trb.exhaust_steam
        row = [trb.name, trb.steam_flow_lb_hr, trb.exhaust_available, trb.hp_demand]
        if tfh is not None:
            row.append(tfh[i])
        row += [trb.steam_rate, trb.inlet_steam.P, trb.inlet_steam.T,
                ex.P, ex.T, _fmt_x(ex.x)]
        rows.append(row)

    total = ["TOTAL", group.total_inlet_flow_lb_hr,
             group.total_exhaust_available_lb_hr, group.total_hp]
    if tfh is not None:
        total.append(sum(tfh))
    total += [group.total_inlet_flow_lb_hr / group.total_hp, "", "", "", "", ""]

    headers = ["Unit", "(1) Inlet Flow (lb/hr)", "(2) Exhaust Avail (lb/hr)", "HP"]
    fmts    = ["@", "#,##0", "#,##0", "#,##0"]
    if tfh is not None:
        headers.append("HP/TFH")
        fmts.append("0.0")
    headers += ["Steam Rate (lb/HP-hr)", "Inlet psia", "Inlet °F",
                "Outlet psia", "Outlet °F", "Outlet Quality"]
    fmts    += ["0.00", "0.0", "0.0", "0.0", "0.0", "0.0000"]

    return {"title": title, "sheet": sheet, "headers": headers, "fmts": fmts,
            "rows": rows, "total": total}


def plot_turbine_group(group, show: bool = True, save_path: str = None,
                       include_table: bool = True) -> plt.Figure:
    """Draw one representative turbine with tagged streams; the group's
    turbines each get a row in the tables below (unless include_table=False)."""
    info = _group_info(group)
    DW, DH = 14.0, 8.2

    STMC = '#c0392b'   # live steam
    EXHC = '#d35400'   # exhaust
    HPC  = '#2c3e50'   # shaft power
    EQ_EC, EQ_FC = '#2471a3', '#d6eaf8'
    GRAY = '#5d6d7e'

    if include_table:
        n = len(info["rows"])
        tab_h = 0.32 * (2 * n + 8)
        fig = plt.figure(figsize=(11.5, 5.4 + tab_h))
        gs  = fig.add_gridspec(2, 1, height_ratios=[5.1, tab_h], hspace=0.05)
        ax  = fig.add_subplot(gs[0])
        axt = fig.add_subplot(gs[1])
        axt.axis('off')
    else:
        fig, ax = plt.subplots(figsize=(8.8, 5.2))
        axt = None
    fig.patch.set_facecolor('#f8f9fa')

    ax.set_xlim(0, DW)
    ax.set_ylim(0, DH)
    ax.set_aspect('equal')
    ax.axis('off')

    def arr(x1, y1, x2, y2, color, lw=2.0):
        ann = ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                          arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                          shrinkA=0, shrinkB=0), clip_on=False)
        ann.arrow_patch.set_zorder(4)

    def seg(pts, color, lw=2.0):
        xs, ys = zip(*pts)
        ax.plot(xs, ys, color=color, lw=lw, zorder=3, clip_on=False,
                solid_joinstyle='miter')

    def tag(x, y, text, color):
        ax.add_patch(mpatches.Circle((x, y), 0.32, facecolor='white',
                                     edgecolor=color, lw=1.6, zorder=6))
        ax.text(x, y, str(text), ha='center', va='center',
                fontsize=7.5 if len(str(text)) < 2 else 6.5,
                fontweight='bold', color=color, zorder=7)

    def lbl(x, y, text, fs=9, color='#1c2833', bold=False, ha='center', va='center'):
        ax.text(x, y, text, ha=ha, va=va, fontsize=fs, color=color,
                fontweight='bold' if bold else 'normal', zorder=7, clip_on=False)

    # ── Turbine: sideways trapezoid, small face left / large face right ───
    ax.add_patch(mpatches.Polygon([(5.0, 4.3), (5.0, 5.7), (9.0, 6.7), (9.0, 3.3)],
                                  closed=True, facecolor=EQ_FC, edgecolor=EQ_EC,
                                  lw=2.0, zorder=2))
    lbl(7.0, 5.0, 'Turbine', fs=10, bold=True, color='#1a3a5c')
    lbl(7.0, 2.75, f'(1 shown — {len(info["rows"])} units, one row each)',
        fs=7.5, color=GRAY)

    # (1) live steam in at the top-left corner
    seg([(1.0, 7.3), (5.0, 7.3)], STMC)
    arr(5.0, 7.3, 5.0, 5.75, STMC)
    lbl(1.0, 7.7, 'Live Steam', fs=9.5, bold=True, color=STMC, ha='left')
    tag(2.7, 7.3, 1, STMC)

    # (2) exhaust out of the bottom-right corner
    seg([(9.0, 3.3), (9.0, 1.6)], EXHC)
    arr(9.0, 1.6, 12.6, 1.6, EXHC)
    lbl(12.6, 2.0, 'Exhaust', fs=9.5, bold=True, color=EXHC, ha='right')
    tag(10.6, 1.6, 2, EXHC)

    # (HP) shaft power out of the center of the right face
    arr(9.0, 5.0, 11.9, 5.0, HPC)
    lbl(12.05, 5.0, 'HP Out', fs=9.5, bold=True, color=HPC, ha='left')
    tag(10.4, 5.0, 'HP', HPC)

    lbl(DW / 2, DH - 0.15, f'{info["title"]} — PFD', fs=14, bold=True)

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
            if c == 0 and r > 0:
                cell.set_text_props(ha='left')

    def num(v, f='{:,.0f}'):
        return f.format(v) if isinstance(v, (int, float)) else str(v) if v else ''

    # short two-line headers so the columns fit the figure width
    fig_headers = ['Unit', '(1) Inlet\nlb/hr', '(2) Exhaust\nlb/hr', 'HP']
    if len(info["headers"]) == 11:          # group with an HP/TFH column
        fig_headers.append('HP/\nTFH')
    fig_headers += ['Steam Rate\nlb/HP-hr', 'Inlet\npsia', 'Inlet\n°F',
                    'Outlet\npsia', 'Outlet\n°F', 'Outlet\nQuality']

    n_cols = len(fig_headers)
    body = info["rows"] + [info["total"]]
    cells = []
    for row in body:
        out = [row[0]]
        for j, v in enumerate(row[1:], 1):
            f = '{:,.0f}' if j <= 3 else '{:,.2f}'
            out.append(num(v, f))
        cells.append(out)
    tab = axt.table(cellText=cells, colLabels=fig_headers,
                    cellLoc='right', bbox=[0.01, 0.44, 0.98, 0.54])
    style(tab)
    tab.auto_set_column_width(list(range(n_cols)))

    axt.text(0.5, 0.37, 'STREAM TAGS PER UNIT', transform=axt.transAxes,
             fontsize=9.5, fontweight='bold', color='#305496', ha='center')
    tag_cells = [[r[0], num(r[1]), num(r[2]), num(r[3])] for r in info["rows"]]
    tab2 = axt.table(cellText=tag_cells,
                     colLabels=['Unit', '(1) Live Steam lb/hr',
                                '(2) Exhaust lb/hr', 'HP Out'],
                     cellLoc='right', bbox=[0.14, 0.02, 0.72, 0.32])
    style(tab2)
    tab2.auto_set_column_width([0, 1, 2, 3])

    if save_path:
        fig.savefig(save_path, dpi=170, bbox_inches='tight')
    if show:
        plt.show()
    return fig


def group_to_excel(group, workbook):
    """Write a turbine group to its own styled sheet: PFD (diagram only),
    the neat_display table, and the stream-tag table."""
    from excel_export import SheetWriter

    info = _group_info(group)
    sw = SheetWriter(workbook, info["sheet"], ncols=len(info["headers"]))
    sw.title(info["title"],
             f"{len(info['rows'])} units | total HP = {group.total_hp:,.0f} "
             f"| steam = {group.total_inlet_flow_lb_hr:,.0f} lb/hr "
             f"| exhaust available = {group.total_exhaust_available_lb_hr:,.0f} lb/hr")

    sw.section("PROCESS FLOW DIAGRAM  (one representative turbine)")
    sw.blank()
    fig = plot_turbine_group(group, show=False, include_table=False)
    sw.image(fig, scale=0.55)
    plt.close(fig)

    sw.section("TURBINE TABLE")
    sw.table(info["headers"], info["rows"], fmts=info["fmts"],
             totals=[info["total"]])

    ws = sw.finish()
    if len(info["headers"]) == 11:          # group with an HP/TFH column
        col_widths_px = {'A': 63, 'B': 119, 'C': 137, 'D': 38, 'E': 48, 'F': 130,
                         'G': 56, 'H': 45, 'I': 67, 'J': 56, 'K': 85}
    else:                                    # Fan and Pump / Auxillary — no HP/TFH column
        col_widths_px = {'A': 43, 'B': 119, 'C': 137, 'D': 38, 'E': 130,
                         'F': 56, 'G': 45, 'H': 67, 'I': 56, 'J': 85}
    for letter, px in col_widths_px.items():
        ws.column_dimensions[letter].width = (px - 5) / 7
    return ws
