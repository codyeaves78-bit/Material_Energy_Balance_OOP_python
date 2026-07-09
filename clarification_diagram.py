# Process flow diagram for Clarification objects.
#
# Same conventions as the pan-floor diagrams: the drawing carries NO data —
# every stream gets a numbered tag, and a table below lists each stream's
# flow, GPM, brix, pol, purity, % on cane, and temperature.
#
# Topology (matches Clarification.__init__ and the streams dict):
#   Mixed Juice + Milk of Lime + Polymer Solution + Filtrate -> Liming Tank
#   Limed Juice (cold) -> Juice Heaters (external steam) -> Limed Juice (hot)
#   -> Flash Tank -> Flash Vapors + Flashed Juice -> Clarifier
#   -> Clarified Juice + Underflow;  Underflow + Wash Water -> Rotary Filter
#   -> Filter Cake + Filtrate (recycled to the Liming Tank)

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# tag order: In (1-6), Out (7-9), Internal (10-16) — keys of Clarification.streams
TAG_ORDER = [
    "Mixed Juice", "Lime", "Water for Lime", "Polymer", "Polymer Water",
    "Filter Wash Water",
    "Flash Vapors", "Clarified Juice", "Filter Cake",
    "Milk of Lime", "Polymer Solution", "Limed Juice Cold", "Limed Juice Hot",
    "Flashed Juice", "Clarifier Underflow", "Filtrate",
]


def _collect_streams(cl):
    """Return [(tag, name, dir, lb/hr, gpm, brix lb/hr, pol lb/hr,
                brix%, pol%, purity%, %cane, temp)] from the streams dict."""
    rows = []
    for i, name in enumerate(TAG_ORDER, 1):
        s = cl.streams[name]
        rows.append((i, name, s["direction"], s["lb_per_hr"], s["gpm"],
                     s["brix_lb_per_hr"], s["pol_lb_per_hr"],
                     s["brix_pct"], s["pol_pct"],
                     s["purity_pct"] if s["brix_pct"] > 0 else "",
                     s["pct_on_cane"],
                     s["temp_f"] if s["temp_f"] is not None else ""))
    return rows


def plot_clarification(cl, show: bool = True, save_path: str = None,
                       include_table: bool = True) -> plt.Figure:
    """Draw the clarification PFD, with a stream table below unless
    include_table=False (diagram only, e.g. for embedding in Excel)."""
    DW, DH = 24.0, 15.0

    JC   = '#1e8449'   # juice (mixed / limed / clarified)
    LIMC = '#7f8c8d'   # lime
    POLC = '#8e44ad'   # polymer
    WATC = '#2980b9'   # water
    VAPC = '#c0392b'   # flash vapor
    MUDC = '#7b4f2e'   # underflow / cake
    FILC = '#b7950b'   # filtrate
    EQ_EC, EQ_FC = '#2471a3', '#d6eaf8'
    GRAY = '#5d6d7e'

    if include_table:
        fig = plt.figure(figsize=(15.0, 15.6))
        gs  = fig.add_gridspec(2, 1, height_ratios=[9.3, 6.0], hspace=0.03)
        ax  = fig.add_subplot(gs[0])
        axt = fig.add_subplot(gs[1])
        axt.axis('off')
    else:
        fig, ax = plt.subplots(figsize=(15.0, 9.5))
        axt = None
    fig.patch.set_facecolor('#f8f9fa')

    ax.set_xlim(0, DW)
    ax.set_ylim(0, DH)
    ax.set_aspect('equal')
    ax.axis('off')

    # ── Drawing helpers ───────────────────────────────────────────────────
    def arr(x1, y1, x2, y2, color, lw=1.7):
        ann = ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                          arrowprops=dict(arrowstyle='->', color=color, lw=lw,
                                          shrinkA=0, shrinkB=0), clip_on=False)
        ann.arrow_patch.set_zorder(4)

    def seg(pts, color, lw=1.7):
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

    def open_tank(cx, cy, w, h):
        ax.plot([cx - w/2, cx - w/2, cx + w/2, cx + w/2],
                [cy + h/2, cy - h/2, cy - h/2, cy + h/2],
                color=EQ_EC, lw=1.8, zorder=2)

    def box(x0, y0, x1, y1):
        ax.add_patch(mpatches.Rectangle((x0, y0), x1 - x0, y1 - y0,
                                        facecolor=EQ_FC, edgecolor=EQ_EC,
                                        lw=1.8, zorder=2))

    # ── Equipment ─────────────────────────────────────────────────────────
    open_tank(2.2, 12.3, 1.4, 1.0)            # MOL tank
    lbl(2.2, 13.15, 'MOL Tank', fs=7.5, color=GRAY)
    open_tank(14.6, 12.3, 1.4, 1.0)            # polymer tank
    lbl(14.6, 13.15, 'Polymer Tank', fs=7.5, color=GRAY)
    open_tank(4.1, 8.6, 2.2, 1.4)               # liming tank
    lbl(4.1, 7.5, 'Liming Tank', fs=7.5, color=GRAY)

    box(8.0, 8.0, 9.6, 9.2)                    # juice heaters
    lbl(8.8, 8.6, 'Juice\nHeaters', fs=7.5, color='#1a3a5c')

    box(11.6, 7.3, 13.0, 9.9)                  # flash tank
    lbl(12.3, 8.85, 'Flash\nTank', fs=7.5, color='#1a3a5c')

    clar = [(15.7, 9.6), (19.3, 9.6), (19.3, 8.0), (18.1, 7.2),
            (16.9, 7.2), (15.7, 8.0)]          # clarifier with cone bottom
    ax.add_patch(mpatches.Polygon(clar, closed=True, facecolor=EQ_FC,
                                  edgecolor=EQ_EC, lw=2.0, zorder=2))
    lbl(17.5, 8.7, 'Clarifier', fs=10, bold=True, color='#1a3a5c')

    ax.add_patch(mpatches.Circle((13.5, 3.6), 1.1, facecolor=EQ_FC,
                                 edgecolor=EQ_EC, lw=1.8, zorder=2))
    lbl(13.5, 3.6, 'Rotary\nFilter', fs=7.5, color='#1a3a5c')

    # ══ Streams ═══════════════════════════════════════════════════════════
    # 1 mixed juice in
    arr(0.5, 8.4, 3.0, 8.4, JC, lw=2.2)
    lbl(0.5, 8.85, 'Mixed Juice', fs=9.5, bold=True, color=JC, ha='left')
    tag(1.7, 8.4, 1, JC)

    # 2/3 lime + water into MOL tank
    arr(0.4, 12.55, 1.5, 12.55, LIMC)
    lbl(0.4, 12.95, 'Lime', fs=8, bold=True, color=LIMC, ha='left')
    tag(0.95, 12.55, 2, LIMC)
    arr(0.4, 11.95, 1.5, 11.95, WATC)
    lbl(0.4, 11.55, 'Water', fs=8, bold=True, color=WATC, ha='left')
    tag(0.95, 11.95, 3, WATC)

    # 4/5 polymer + water into the polymer tank from the right
    arr(16.4, 12.55, 15.3, 12.55, POLC)
    lbl(16.5, 12.95, 'Polymer', fs=8, bold=True, color=POLC, ha='left')
    tag(15.95, 12.55, 4, POLC)
    arr(16.4, 11.95, 15.3, 11.95, WATC)
    lbl(16.5, 11.55, 'Water', fs=8, bold=True, color=WATC, ha='left')
    tag(15.95, 11.95, 5, WATC)

    # 10 milk of lime down into the liming tank
    seg([(2.2, 11.8), (2.2, 10.3), (3.6, 10.3)], LIMC)
    arr(3.6, 10.3, 3.6, 9.3, LIMC)
    tag(2.2, 10.9, 10, LIMC)

    # 11 polymer solution straight down into the flashed juice ahead of the clarifier
    arr(14.6, 11.8, 14.6, 8.4, POLC)
    dot(14.6, 8.4, JC)
    tag(14.6, 10.4, 11, POLC)

    # 12 limed juice cold -> heaters ; 13 hot -> flash tank
    arr(5.2, 8.6, 8.0, 8.6, JC, lw=2.0)
    tag(6.6, 8.6, 12, JC)
    arr(9.6, 8.6, 11.6, 8.6, JC, lw=2.0)
    tag(10.6, 8.6, 13, JC)

    # 7 flash vapors up and out
    arr(12.3, 9.9, 12.3, 11.4, VAPC, lw=2.0)
    lbl(12.3, 11.75, 'Flash Vapors', fs=9.5, bold=True, color=VAPC)
    tag(12.3, 10.65, 7, VAPC)

    # 14 flashed juice -> clarifier
    arr(13.0, 8.4, 15.7, 8.4, JC, lw=2.0)
    tag(13.6, 8.4, 14, JC)

    # 8 clarified juice out
    arr(19.3, 8.9, 22.7, 8.9, JC, lw=2.2)
    lbl(22.7, 9.35, 'Clarified Juice', fs=9.5, bold=True, color=JC, ha='right')
    tag(21.0, 8.9, 8, JC)

    # 15 clarifier underflow -> rotary filter
    seg([(17.5, 7.2), (17.5, 3.6)], MUDC)
    arr(17.5, 3.6, 14.6, 3.6, MUDC)
    tag(16.2, 3.6, 15, MUDC)

    # 6 filter wash water down into the drum
    arr(13.5, 6.3, 13.5, 4.75, WATC)
    lbl(13.5, 6.65, 'Wash Water', fs=8, bold=True, color=WATC)
    tag(13.5, 5.55, 6, WATC)

    # 9 filter cake out
    seg([(13.5, 2.5), (13.5, 1.6)], MUDC)
    arr(13.5, 1.6, 16.2, 1.6, MUDC, lw=2.0)
    lbl(16.4, 1.6, 'Filter Cake', fs=9.5, bold=True, color=MUDC, ha='left')
    tag(15.0, 1.6, 9, MUDC)

    # 16 filtrate recycled to the liming tank
    seg([(12.4, 3.6), (3.4, 3.6), (3.4, 7.6)], FILC)
    arr(3.4, 7.6, 3.4, 7.9, FILC)
    tag(7.5, 3.6, 16, FILC)

    lbl(DW / 2, DH - 0.15, f'{cl.name} — PFD', fs=15, bold=True)

    # ══ Stream table ══════════════════════════════════════════════════════
    if not include_table:
        if save_path:
            fig.savefig(save_path, dpi=170, bbox_inches='tight')
        if show:
            plt.show()
        return fig

    rows = _collect_streams(cl)
    col_labels = ['#', 'Stream', 'Dir', 'lb/hr', 'GPM', 'Brix lb/hr',
                  'Pol lb/hr', 'Brix %', 'Pol %', 'Purity %', '% Cane', '°F']

    def num(v, f='{:,.0f}'):
        return f.format(v) if isinstance(v, (int, float)) else '-'

    cells = [[str(r[0]), r[1], r[2], num(r[3]), num(r[4]), num(r[5]), num(r[6]),
              num(r[7], '{:.2f}'), num(r[8], '{:.2f}'), num(r[9], '{:.1f}'),
              num(r[10], '{:.2f}'), num(r[11], '{:.0f}')] for r in rows]

    tab = axt.table(cellText=cells, colLabels=col_labels, cellLoc='right',
                    bbox=[0.01, 0.16, 0.98, 0.82])
    tab.auto_set_font_size(False)
    tab.set_fontsize(8.5)
    for (r, c), cell in tab.get_celld().items():
        cell.set_edgecolor('#bfbfbf')
        if r == 0:
            cell.set_facecolor('#305496')
            cell.set_text_props(color='white', fontweight='bold', ha='center')
        elif r % 2 == 0:
            cell.set_facecolor('#f2f2f2')
        if c == 1 and r > 0:
            cell.set_text_props(ha='left')
    tab.auto_set_column_width(list(range(len(col_labels))))

    bal = cl.balance_check
    axt.text(0.01, 0.10,
             f"Balance (In / Out / Diff):  "
             f"Flow {bal['in']['lb_per_hr']:,.0f} / {bal['out']['lb_per_hr']:,.0f} / "
             f"{bal['difference']['lb_per_hr']:,.1f} lb/hr      "
             f"Brix {bal['in']['brix_lb_per_hr']:,.0f} / {bal['out']['brix_lb_per_hr']:,.0f} / "
             f"{bal['difference']['brix_lb_per_hr']:,.1f} lb/hr      "
             f"Pol {bal['in']['pol_lb_per_hr']:,.0f} / {bal['out']['pol_lb_per_hr']:,.0f} / "
             f"{bal['difference']['pol_lb_per_hr']:,.1f} lb/hr",
             transform=axt.transAxes, fontsize=9, color='#1c2833', fontweight='bold')
    axt.text(0.01, 0.04,
             f"Flash vapor = {cl.flash_vapor_pct:.3f}% of limed juice      "
             f"Filter cake pol loss = {cl.filter_cake_pol_lb_per_day:,.0f} lb/day      "
             f"(Juice heater steam is external — see Juice Heater sheet)",
             transform=axt.transAxes, fontsize=9, color='#566573', style='italic')

    if save_path:
        fig.savefig(save_path, dpi=170, bbox_inches='tight')
    if show:
        plt.show()
    return fig
