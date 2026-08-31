# Process flow diagram for ThreeBoiling objects (single magma stage).
#
# Same conventions as three_boiling_diagram: the drawing carries NO data —
# every process stream gets a numbered tag, and a table below lists each
# stream's flow, brix, and purity. Water additions are tabulated separately.
#
# Topology (matches ThreeBoiling._solve):
#   syrup+remelt -> A / Grain           A mol -> A top-off / B / Grain
#   B mol -> Grain / C                  B sugar -> Raw Sugar (terminal, no B magma)
#   Grain massecuite -> C pans          C: pan -> cryst -> reheater -> cen
#   C magma -> A footing + B footing + remelt      A sugar -> Raw Sugar
#   C molasses -> Final Molasses        remelt -> back to syrup

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def _collect_streams(tb):
    """Return [(tag, name, flow_lb_hr, brix, purity)] for the stream table."""
    saf = tb.syrup_as_fed

    def split(stream, pct):
        return stream.flow_lb_per_hr * pct / 100

    am, bm = tb._a_mol_diluted, tb._b_mol_diluted
    cmag   = tb._c_magma
    a_s    = tb.A_centrifugals.sugar_stream
    b_s    = tb.B_centrifugals.sugar_stream
    cr     = tb._c_remelt

    def pan_masse(pan):
        return pan.massecuite_flow_lb_hr, pan.masse_brix, pan.masse_purity

    rows = [
        (1,  "Syrup from Evaporators",  tb.syrup.flow_lb_per_hr, tb.syrup.brix, tb.syrup.purity),
        (2,  "Remelt Return to Syrup",  cr.flow_lb_per_hr, cr.brix, cr.purity),
        (3,  "Syrup to A Pans",         split(saf, tb.syrup_to_A_pans_pct), saf.brix, saf.purity),
        (4,  "Syrup to Grain Pans",     split(saf, tb.syrup_to_grain_pct),  saf.brix, saf.purity),
        (5,  "A Massecuite",            *pan_masse(tb.A_pans)),
        (6,  "A Sugar (Raw Sugar)",     a_s.flow_lb_per_hr, a_s.brix, a_s.purity),
        (7,  "A Molasses (diluted)",    am.flow_lb_per_hr, am.brix, am.purity),
        (8,  "A Mol Top-off to A Pans", split(am, tb.a_mol_top_off_pct), am.brix, am.purity),
        (9,  "A Molasses to B Pans",    split(am, tb.a_mol_B_pans_pct),  am.brix, am.purity),
        (10, "A Molasses to Grain",     split(am, tb.a_mol_to_grain_pct), am.brix, am.purity),
        (11, "B Massecuite",            *pan_masse(tb.B_pans)),
        (12, "B Sugar (Raw Sugar)",     b_s.flow_lb_per_hr, b_s.brix, b_s.purity),
        (13, "B Molasses (diluted)",    bm.flow_lb_per_hr, bm.brix, bm.purity),
        (14, "B Molasses to Grain",     split(bm, tb.b_mol_to_grain_pct), bm.brix, bm.purity),
        (15, "B Molasses to C Pans",    split(bm, tb.b_mol_C_pans_pct),   bm.brix, bm.purity),
        (16, "Grain Massecuite",        *pan_masse(tb.grain_pans)),
        (17, "C Massecuite",            *pan_masse(tb.C_pans)),
        (18, "C Sugar",                 tb.C_centrifugals.sugar_stream.flow_lb_per_hr,
                                        tb.C_centrifugals.sugar_stream.brix,
                                        tb.C_centrifugals.sugar_stream.purity),
        (19, "C Magma",                 cmag.flow_lb_per_hr, cmag.brix, cmag.purity),
        (20, "C Magma to A Footing",    split(cmag, tb.c_magma_A_footing_pct), cmag.brix, cmag.purity),
        (21, "C Magma to B Footing",    split(cmag, tb.c_magma_B_footing_pct), cmag.brix, cmag.purity),
        (22, "C Magma to Remelt",       split(cmag, tb.c_magma_remelt_pct),    cmag.brix, cmag.purity),
        (23, "C Final Molasses",        tb.C_centrifugals.molasses_stream.flow_lb_per_hr,
                                        tb.C_centrifugals.molasses_stream.brix,
                                        tb.C_centrifugals.molasses_stream.purity),
    ]
    return rows


def _collect_water(tb):
    """Water streams not drawn: (left_rows, right_rows, totals)."""
    c_mingler = tb._c_magma.flow_lb_per_hr  - tb.C_centrifugals.sugar_stream.flow_lb_per_hr
    c_remelt  = tb._c_remelt.flow_lb_per_hr - tb._c_magma_to_rmlt.flow_lb_per_hr
    a_dil = tb._a_mol_diluted.flow_lb_per_hr - tb.A_centrifugals.molasses_stream.flow_lb_per_hr
    b_dil = tb._b_mol_diluted.flow_lb_per_hr - tb.B_centrifugals.molasses_stream.flow_lb_per_hr

    left = [
        ("A Centrifugal Wash Water", tb.A_centrifugals.wash_water_lb_hr),
        ("B Centrifugal Wash Water", tb.B_centrifugals.wash_water_lb_hr),
        ("C Centrifugal Wash Water", tb.C_centrifugals.wash_water_lb_hr),
        ("C Magma Mingler Water",    c_mingler),
        ("C Remelt Water",           c_remelt),
    ]
    right = [
        ("A Molasses Dilution Water",   a_dil),
        ("B Molasses Dilution Water",   b_dil),
        ("A Pans Water Evaporated",     tb.A_pans.water_evaporated_lb_hr),
        ("B Pans Water Evaporated",     tb.B_pans.water_evaporated_lb_hr),
        ("Grain Pans Water Evaporated", tb.grain_pans.water_evaporated_lb_hr),
        ("C Pans Water Evaporated",     tb.C_pans.water_evaporated_lb_hr),
    ]
    total_in   = tb.total_water.flow_lb_per_hr
    total_evap = (tb.A_pans.water_evaporated_lb_hr + tb.B_pans.water_evaporated_lb_hr
                  + tb.grain_pans.water_evaporated_lb_hr + tb.C_pans.water_evaporated_lb_hr)
    return left, right, (total_in, total_evap)


def plot_three_boiling(tb, show: bool = True, save_path: str = None,
                       include_table: bool = True) -> plt.Figure:
    """Draw the three-boiling (single-magma) PFD, with a stream table below
    unless include_table=False (diagram only, e.g. for embedding in Excel)."""
    DW, DH = 24.5, 16.6

    SYRC = '#1e8449'   # syrup / feed
    MASC = '#6c3483'   # massecuite
    SUGC = '#d35400'   # sugar / raw sugar
    MOLC = '#a04000'   # molasses
    MAGC = '#b7950b'   # magma / footings
    RMC  = '#2980b9'   # remelt
    FINC = '#7b241c'   # final molasses
    EQ_EC, EQ_FC = '#2471a3', '#d6eaf8'
    GRAY = '#5d6d7e'

    if include_table:
        fig = plt.figure(figsize=(18.0, 19.8))
        gs  = fig.add_gridspec(2, 1, height_ratios=[11.8, 7.4], hspace=0.03)
        ax  = fig.add_subplot(gs[0])
        axt = fig.add_subplot(gs[1])
        axt.axis('off')
    else:
        fig, ax = plt.subplots(figsize=(18.0, 12.2))
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

    def pan(cx, y0, name, w=2.4):
        h = w / 2
        pts = [(cx - h, y0), (cx - h, y0 + 1.7), (cx - 0.5, y0 + 2.05),
               (cx - 0.5, y0 + 2.55), (cx + 0.5, y0 + 2.55), (cx + 0.5, y0 + 2.05),
               (cx + h, y0 + 1.7), (cx + h, y0)]
        ax.add_patch(mpatches.Polygon(pts, closed=True, facecolor=EQ_FC,
                                      edgecolor=EQ_EC, lw=2.0, zorder=2))
        lbl(cx, y0 + 1.0, name, fs=12, bold=True, color='#1a3a5c')

    def cen(cx, y0, name):
        pts = [(cx - 0.85, y0 + 1.0), (cx + 0.85, y0 + 1.0),
               (cx + 0.45, y0), (cx - 0.45, y0)]
        ax.add_patch(mpatches.Polygon(pts, closed=True, facecolor=EQ_FC,
                                      edgecolor=EQ_EC, lw=1.8, zorder=2))
        lbl(cx + 1.05, y0 + 0.62, name, fs=7.5, color=GRAY, ha='left')

    def mingler(cx, cy, name):
        ax.add_patch(mpatches.Rectangle((cx - 0.8, cy - 0.25), 1.6, 0.5,
                                        facecolor='white', edgecolor=EQ_EC,
                                        lw=1.6, hatch='//', zorder=2))
        lbl(cx + 0.95, cy, name, fs=7.5, color=GRAY, ha='left')

    def tank(cx, cy, w, h, name):
        ax.plot([cx - w/2, cx - w/2, cx + w/2, cx + w/2],
                [cy + h/2, cy - h/2, cy - h/2, cy + h/2],
                color=EQ_EC, lw=1.8, zorder=2)
        lbl(cx, cy, name, fs=7.5, color=GRAY)

    def heatx_box(cx, cy, name):
        s = 0.42
        ax.add_patch(mpatches.Rectangle((cx - s, cy - s), 2*s, 2*s,
                                        facecolor='white', edgecolor=EQ_EC, lw=1.6, zorder=2))
        ax.plot([cx - s, cx + s], [cy - s, cy + s], color=EQ_EC, lw=1.0, zorder=3)
        ax.plot([cx - s, cx + s], [cy + s, cy - s], color=EQ_EC, lw=1.0, zorder=3)
        lbl(cx + 0.65, cy, name, fs=7.5, color=GRAY, ha='left')

    def reheater(cx, cy, name):
        ax.add_patch(mpatches.Circle((cx, cy), 0.45, facecolor='white',
                                     edgecolor=EQ_EC, lw=1.6, zorder=2))
        lbl(cx, cy, '~', fs=13, color=EQ_EC, bold=True)
        lbl(cx + 0.65, cy, name, fs=7.5, color=GRAY, ha='left')

    # ── Equipment placement ───────────────────────────────────────────────
    PX = {'A': 4.0, 'B': 10.0, 'GR': 15.0, 'C': 20.0}
    Y0   = 10.0
    NECK = Y0 + 2.55
    Y_SYR = 13.6
    Y_BFOOT, Y_AFOOT = 14.35, 15.5   # C magma loop heights: B footing (short), A footing (long)
    CEN0 = 7.0

    pan(PX['A'],  Y0, 'A')
    pan(PX['B'],  Y0, 'B')
    pan(PX['GR'], Y0, 'Grain')
    pan(PX['C'],  Y0, 'C')

    cen(PX['A'], CEN0, 'A Cen')
    cen(PX['B'], CEN0, 'B Cen')
    heatx_box(PX['C'], 8.0, 'Cooling\nCryst')
    reheater(PX['C'], 6.5, 'Reheater')
    cen(PX['C'], 4.4, 'C Cen')

    mingler(PX['C'], 3.30, 'C Mingler')
    tank(10.5, 1.65, 1.8, 0.9, 'Remelt')

    # ══ Streams ═══════════════════════════════════════════════════════════
    # 1 syrup from evaporators, 2 remelt return joining it
    seg([(0.5, Y_SYR), (PX['GR'] - 0.25, Y_SYR)], SYRC, lw=2.2)
    lbl(0.5, Y_SYR + 0.45, 'Syrup from Evaporators', fs=9.5, bold=True,
        color=SYRC, ha='left')
    tag(0.8, Y_SYR, 1, SYRC)
    dot(1.3, Y_SYR, SYRC)
    seg([(9.6, 1.65), (1.3, 1.65), (1.3, Y_SYR - 0.5)], RMC)
    arr(1.3, Y_SYR - 0.5, 1.3, Y_SYR, RMC)
    tag(1.3, 7.8, 2, RMC)

    # 3/4 syrup drops into A and Grain necks
    for x, t in [(PX['A'] - 0.25, 3), (PX['GR'] - 0.25, 4)]:
        dot(x, Y_SYR, SYRC)
        arr(x, Y_SYR, x, NECK, SYRC)
        tag(x, 13.05, t, SYRC)

    # 20 C magma footing to A neck — long loop around the right + top
    seg([(PX['C'], 2.6), (23.3, 2.6), (23.3, Y_AFOOT), (PX['A'] + 0.25, Y_AFOOT)], MAGC)
    arr(PX['A'] + 0.25, Y_AFOOT, PX['A'] + 0.25, NECK, MAGC)
    tag(13.5, Y_AFOOT, 20, MAGC)

    # 21 C magma footing to B neck — shorter loop around the right + top
    seg([(PX['C'], 2.6), (22.8, 2.6), (22.8, Y_BFOOT), (PX['B'] + 0.35, Y_BFOOT)], MAGC)
    arr(PX['B'] + 0.35, Y_BFOOT, PX['B'] + 0.35, NECK, MAGC)
    tag(16.5, Y_BFOOT, 21, MAGC)

    # 5/11/17 massecuites: pan -> centrifugal (or crystallizer for C)
    for key, t in [('A', 5), ('B', 11)]:
        arr(PX[key], Y0, PX[key], CEN0 + 1.0, MASC, lw=2.0)
        tag(PX[key], 9.0, t, MASC)
    arr(PX['C'], Y0, PX['C'], 8.42, MASC, lw=2.0)
    tag(PX['C'], 9.2, 17, MASC)

    # C chain: cryst -> reheater -> C cen
    arr(PX['C'], 7.58, PX['C'], 6.95, MASC)
    arr(PX['C'], 6.05, PX['C'], 5.4, MASC)

    # 6 A sugar -> raw sugar
    seg([(PX['A'], CEN0), (PX['A'], 1.1), (2.2, 1.1)], SUGC, lw=2.0)
    arr(2.2, 1.1, 2.2, 0.35, SUGC, lw=2.2)
    lbl(2.2, 0.12, 'A Raw Sugar', fs=9.5, bold=True, color=SUGC)
    tag(PX['A'], 3.0, 6, SUGC)

    # 12 B sugar -> raw sugar (terminal product — no B magma stage)
    # Vertical run crosses the A-molasses trunk at y=6.2 — keep the tag well
    # clear of that crossing so it doesn't read as part of the molasses network.
    seg([(PX['B'], CEN0), (PX['B'], 1.85), (6.6, 1.85)], SUGC, lw=2.0)
    arr(6.6, 1.85, 6.6, 0.35, SUGC, lw=2.2)
    lbl(6.6, 0.12, 'B Raw Sugar', fs=9.5, bold=True, color=SUGC)
    tag(PX['B'], 4.2, 12, SUGC)

    # 7..10 A molasses (diluted) splits: top-off to A, B, Grain
    y1 = 6.2
    seg([(PX['A'] + 0.8, CEN0 + 0.45), (PX['A'] + 1.5, CEN0 + 0.45),
         (PX['A'] + 1.5, y1), (13.4, y1)], MOLC)
    tag(8.5, y1, 7, MOLC)
    dot(PX['A'] + 1.5, y1, MOLC)                        # top-off back to A
    seg([(PX['A'] + 1.5, y1), (PX['A'] + 1.5, 11.5)], MOLC)
    arr(PX['A'] + 1.5, 11.5, PX['A'] + 1.2, 11.5, MOLC)
    tag(PX['A'] + 1.5, 9.4, 8, MOLC)
    dot(8.3, y1, MOLC)                                  # -> B
    seg([(8.3, y1), (8.3, 10.8)], MOLC)
    arr(8.3, 10.8, PX['B'] - 1.2, 10.8, MOLC)
    tag(8.3, 9.0, 9, MOLC)
    seg([(13.4, y1), (13.4, 11.4)], MOLC)               # -> Grain
    arr(13.4, 11.4, PX['GR'] - 1.2, 11.4, MOLC)
    tag(13.4, 8.8, 10, MOLC)

    # 13..15 B molasses splits: Grain, C
    y3 = 3.35
    seg([(PX['B'] + 0.8, CEN0 + 0.45), (PX['B'] + 1.7, CEN0 + 0.45),
         (PX['B'] + 1.7, y3), (18.4, y3)], MOLC)
    tag(12.4, y3, 13, MOLC)
    dot(13.0, y3, MOLC)                                 # -> Grain
    seg([(13.0, y3), (13.0, 10.8)], MOLC)
    arr(13.0, 10.8, PX['GR'] - 1.2, 10.8, MOLC)
    tag(13.0, 7.5, 14, MOLC)
    seg([(18.4, y3), (18.4, 10.7)], MOLC)               # -> C
    arr(18.4, 10.7, PX['C'] - 1.2, 10.7, MOLC)
    tag(18.4, 7.0, 15, MOLC)

    # 16 grain massecuite -> C pan
    seg([(PX['GR'], Y0), (PX['GR'], 9.0), (18.0, 9.0), (18.0, 11.3)], MASC)
    arr(18.0, 11.3, PX['C'] - 1.2, 11.3, MASC)
    tag(16.5, 9.0, 16, MASC)

    # 18/19/22 C sugar -> mingler -> magma -> remelt junction
    arr(PX['C'], 4.4, PX['C'], 3.55, SUGC)
    tag(PX['C'], 3.95, 18, SUGC)
    seg([(PX['C'], 3.05), (PX['C'], 2.6)], MAGC)
    tag(PX['C'] - 0.55, 2.82, 19, MAGC)
    dot(PX['C'], 2.6, MAGC)
    seg([(PX['C'], 2.6), (PX['C'], 0.6), (12.0, 0.6), (12.0, 1.65)], MAGC)
    arr(12.0, 1.65, 11.4, 1.65, MAGC)
    tag(15.5, 0.6, 22, MAGC)

    # 23 final molasses out
    arr(PX['C'] + 0.85, 4.85, 23.8, 4.85, FINC, lw=2.2)
    lbl(23.6, 5.55, 'Final\nMolasses', fs=9.5, bold=True, color=FINC)
    tag(22.2, 4.85, 23, FINC)

    lbl(DW / 2, DH - 0.15, 'Three Boiling (Single Magma) — Pan Floor PFD',
        fs=15, bold=True)

    # ══ Stream table ══════════════════════════════════════════════════════
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

    rows = _collect_streams(tb)
    half = (len(rows) + 1) // 2
    col_labels = ['#', 'Stream', 'Flow (lb/hr)', 'Brix', 'Purity']

    def fmt(r):
        return [str(r[0]), r[1], f'{r[2]:,.0f}', f'{r[3]:.1f}', f'{r[4]:.1f}']

    for block, bbox in [(rows[:half], [0.01, 0.42, 0.47, 0.56]),
                        (rows[half:], [0.52, 0.42, 0.47, 0.56])]:
        tab = axt.table(cellText=[fmt(r) for r in block], colLabels=col_labels,
                        cellLoc='right', bbox=bbox)
        style(tab, name_col=1)
        tab.auto_set_column_width([0, 1, 2, 3, 4])

    wleft, wright, (total_in, total_evap) = _collect_water(tb)
    axt.text(0.5, 0.385, 'STREAMS NOT SHOWN — WATER', transform=axt.transAxes,
             fontsize=10.5, fontweight='bold', color='#305496', ha='center')

    wcols = ['Stream', 'Flow (lb/hr)']
    for block, bbox in [(wleft,  [0.01, 0.06, 0.47, 0.30]),
                        (wright, [0.52, 0.06, 0.47, 0.30])]:
        tab = axt.table(cellText=[[n, f'{f:,.0f}'] for n, f in block],
                        colLabels=wcols, cellLoc='right', bbox=bbox)
        style(tab, name_col=0)
        tab.auto_set_column_width([0, 1])

    axt.text(0.01, 0.008,
             f'Total fresh water in (wash + mingler + remelt + dilution) = {total_in:,.0f} lb/hr'
             f'        Total water evaporated (all pans) = {total_evap:,.0f} lb/hr',
             transform=axt.transAxes, fontsize=9, color='#1c2833', fontweight='bold')

    if save_path:
        fig.savefig(save_path, dpi=170, bbox_inches='tight')
    if show:
        plt.show()
    return fig
