# Process flow diagram for FourBoilingDoubleMagma objects.
#
# The drawing carries NO data — every process stream gets a small numbered
# tag, and a table under the diagram lists each stream's flow, brix, and
# purity. Fresh water additions (wash, dilution, mingler, remelt water) are
# not drawn; the table footer shows the total.
#
# Topology (matches FourBoilingDoubleMagma._solve):
#   syrup+remelts -> A1 / A2 / Grain    A1 mol -> A2 / B / Grain
#   A2 mol -> B / Grain                 B mol  -> Grain / C
#   B magma -> A1 & A2 footings + remelt
#   Grain massecuite -> C pans          C: pan -> cryst -> reheater -> cen
#   C magma -> B footing + remelt       A1+A2 sugar -> Raw Sugar
#   C molasses -> Final Molasses        remelts -> back to syrup

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches


def _collect_streams(fb):
    """Return [(tag, name, flow_lb_hr, brix, purity)] for the stream table."""
    saf = fb.syrup_as_fed

    def split(stream, pct):
        return stream.flow_lb_per_hr * pct / 100

    a1m, a2m, bm = fb._a1_mol_diluted, fb._a2_mol_diluted, fb._b_mol_diluted
    bmag, cmag   = fb._b_magma, fb._c_magma
    a1s = fb.A1_centrifugals.sugar_stream
    a2s = fb.A2_centrifugals.sugar_stream

    # combined remelt back to syrup
    br, cr    = fb._b_remelt, fb._c_remelt
    rm_flow   = br.flow_lb_per_hr + cr.flow_lb_per_hr
    rm_solids = br.solids_flow + cr.solids_flow
    rm_brix   = rm_solids / rm_flow * 100 if rm_flow else 0
    rm_purity = (br.pol_flow + cr.pol_flow) / rm_solids * 100 if rm_solids else 0

    # combined raw sugar
    rs_flow   = a1s.flow_lb_per_hr + a2s.flow_lb_per_hr
    rs_solids = a1s.solids_flow + a2s.solids_flow
    rs_brix   = rs_solids / rs_flow * 100 if rs_flow else 0
    rs_purity = (a1s.pol_flow + a2s.pol_flow) / rs_solids * 100 if rs_solids else 0

    def pan_masse(pan):
        return pan.massecuite_flow_lb_hr, pan.masse_brix, pan.masse_purity

    rows = [
        (1,  "Syrup from Evaporators",   fb.syrup.flow_lb_per_hr, fb.syrup.brix, fb.syrup.purity),
        (2,  "Remelt Return to Syrup",   rm_flow, rm_brix, rm_purity),
        (3,  "Syrup to A1 Pans",         split(saf, fb.syrup_to_A1_pans_pct), saf.brix, saf.purity),
        (4,  "Syrup to A2 Pans",         split(saf, fb.syrup_to_A2_pans_pct), saf.brix, saf.purity),
        (5,  "Syrup to Grain Pans",      split(saf, fb.syrup_to_grain_pct),   saf.brix, saf.purity),
        (6,  "A1 Massecuite",            *pan_masse(fb.A1_pans)),
        (7,  "A1 Sugar",                 a1s.flow_lb_per_hr, a1s.brix, a1s.purity),
        (8,  "A1 Molasses (diluted)",    a1m.flow_lb_per_hr, a1m.brix, a1m.purity),
        (9,  "A1 Molasses to A2 Pans",   split(a1m, fb.a1_mol_to_A2_pct),    a1m.brix, a1m.purity),
        (10, "A1 Molasses to Grain",     split(a1m, fb.a1_mol_to_grain_pct), a1m.brix, a1m.purity),
        (11, "A1 Molasses to B Pans",    split(a1m, fb.a1_mol_to_B_pct),     a1m.brix, a1m.purity),
        (12, "A2 Massecuite",            *pan_masse(fb.A2_pans)),
        (13, "A2 Sugar",                 a2s.flow_lb_per_hr, a2s.brix, a2s.purity),
        (14, "A2 Molasses (diluted)",    a2m.flow_lb_per_hr, a2m.brix, a2m.purity),
        (15, "A2 Molasses to B Pans",    split(a2m, fb.a2_mol_to_B_pct),     a2m.brix, a2m.purity),
        (16, "A2 Molasses to Grain",     split(a2m, fb.a2_mol_to_grain_pct), a2m.brix, a2m.purity),
        (17, "B Massecuite",             *pan_masse(fb.B_pans)),
        (18, "B Sugar",                  fb.B_centrifugals.sugar_stream.flow_lb_per_hr,
                                         fb.B_centrifugals.sugar_stream.brix,
                                         fb.B_centrifugals.sugar_stream.purity),
        (19, "B Magma",                  bmag.flow_lb_per_hr, bmag.brix, bmag.purity),
        (20, "B Magma to A1 Footing",    split(bmag, fb.b_magma_A1_footing_pct), bmag.brix, bmag.purity),
        (21, "B Magma to A2 Footing",    split(bmag, fb.b_magma_A2_footing_pct), bmag.brix, bmag.purity),
        (22, "B Magma to Remelt",        split(bmag, fb.b_magma_remelt_pct),     bmag.brix, bmag.purity),
        (23, "B Molasses (diluted)",     bm.flow_lb_per_hr, bm.brix, bm.purity),
        (24, "B Molasses to Grain",      split(bm, fb.b_mol_to_grain_pct), bm.brix, bm.purity),
        (25, "B Molasses to C Pans",     split(bm, fb.b_mol_to_C_pct),     bm.brix, bm.purity),
        (26, "Grain Massecuite",         *pan_masse(fb.grain_pans)),
        (27, "C Massecuite",             *pan_masse(fb.C_pans)),
        (28, "C Sugar",                  fb.C_centrifugals.sugar_stream.flow_lb_per_hr,
                                         fb.C_centrifugals.sugar_stream.brix,
                                         fb.C_centrifugals.sugar_stream.purity),
        (29, "C Magma",                  cmag.flow_lb_per_hr, cmag.brix, cmag.purity),
        (30, "C Magma to B Footing",     split(cmag, fb.c_magma_B_footing_pct), cmag.brix, cmag.purity),
        (31, "C Magma to Remelt",        split(cmag, fb.c_magma_remelt_pct),    cmag.brix, cmag.purity),
        (32, "C Final Molasses",         fb.C_centrifugals.molasses_stream.flow_lb_per_hr,
                                         fb.C_centrifugals.molasses_stream.brix,
                                         fb.C_centrifugals.molasses_stream.purity),
        (33, "Total Raw Sugar (A1+A2)",  rs_flow, rs_brix, rs_purity),
    ]
    return rows


def _collect_water(fb):
    """Water streams not drawn on the diagram: (left_rows, right_rows, totals).

    Left block: centrifugal wash + mingler + remelt water.
    Right block: molasses dilution water + evaporation per pan.
    """
    b_mingler = fb._b_magma.flow_lb_per_hr - fb.B_centrifugals.sugar_stream.flow_lb_per_hr
    c_mingler = fb._c_magma.flow_lb_per_hr - fb.C_centrifugals.sugar_stream.flow_lb_per_hr
    b_remelt  = fb._b_remelt.flow_lb_per_hr - fb._b_magma_to_rmlt.flow_lb_per_hr
    c_remelt  = fb._c_remelt.flow_lb_per_hr - fb._c_magma_to_rmlt.flow_lb_per_hr
    a1_dil = fb._a1_mol_diluted.flow_lb_per_hr - fb.A1_centrifugals.molasses_stream.flow_lb_per_hr
    a2_dil = fb._a2_mol_diluted.flow_lb_per_hr - fb.A2_centrifugals.molasses_stream.flow_lb_per_hr
    b_dil  = fb._b_mol_diluted.flow_lb_per_hr  - fb.B_centrifugals.molasses_stream.flow_lb_per_hr

    left = [
        ("A1 Centrifugal Wash Water", fb.A1_centrifugals.wash_water_lb_hr),
        ("A2 Centrifugal Wash Water", fb.A2_centrifugals.wash_water_lb_hr),
        ("B Centrifugal Wash Water",  fb.B_centrifugals.wash_water_lb_hr),
        ("C Centrifugal Wash Water",  fb.C_centrifugals.wash_water_lb_hr),
        ("B Magma Mingler Water",     b_mingler),
        ("C Magma Mingler Water",     c_mingler),
        ("B Remelt Water",            b_remelt),
        ("C Remelt Water",            c_remelt),
    ]
    right = [
        ("A1 Molasses Dilution Water", a1_dil),
        ("A2 Molasses Dilution Water", a2_dil),
        ("B Molasses Dilution Water",  b_dil),
        ("A1 Pans Water Evaporated",    fb.A1_pans.water_evaporated_lb_hr),
        ("A2 Pans Water Evaporated",    fb.A2_pans.water_evaporated_lb_hr),
        ("B Pans Water Evaporated",     fb.B_pans.water_evaporated_lb_hr),
        ("Grain Pans Water Evaporated", fb.grain_pans.water_evaporated_lb_hr),
        ("C Pans Water Evaporated",     fb.C_pans.water_evaporated_lb_hr),
    ]
    total_in   = fb.total_water.flow_lb_per_hr
    total_evap = (fb.A1_pans.water_evaporated_lb_hr + fb.A2_pans.water_evaporated_lb_hr
                  + fb.B_pans.water_evaporated_lb_hr + fb.grain_pans.water_evaporated_lb_hr
                  + fb.C_pans.water_evaporated_lb_hr)
    return left, right, (total_in, total_evap)


def plot_four_boiling(fb, show: bool = True, save_path: str = None,
                      include_table: bool = True) -> plt.Figure:
    """Draw the four-boiling double-magma PFD, with a stream table below
    unless include_table=False (diagram only, e.g. for embedding in Excel
    where the table lives in cells instead)."""
    DW, DH = 27.0, 15.8

    # ── Colors by stream type ─────────────────────────────────────────────
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
        fig = plt.figure(figsize=(19.5, 20.2))
        gs  = fig.add_gridspec(2, 1, height_ratios=[11.4, 8.8], hspace=0.03)
        ax  = fig.add_subplot(gs[0])
        axt = fig.add_subplot(gs[1])
        axt.axis('off')
    else:
        fig, ax = plt.subplots(figsize=(19.5, 11.6))
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
        # open-top tank
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
    PX = {'A1': 4.0, 'A2': 9.0, 'B': 14.0, 'GR': 18.5, 'C': 23.0}
    Y0   = 10.0             # pan body base
    NECK = Y0 + 2.55        # pan neck top
    Y_SYR, Y_CTOP, Y_BTOP = 13.6, 14.35, 15.1
    CEN0 = 7.0              # A1/A2/B centrifugal base

    pan(PX['A1'], Y0, 'A1')
    pan(PX['A2'], Y0, 'A2')
    pan(PX['B'],  Y0, 'B')
    pan(PX['GR'], Y0, 'Grain')
    pan(PX['C'],  Y0, 'C')

    cen(PX['A1'], CEN0, 'A1 Cen')
    cen(PX['A2'], CEN0, 'A2 Cen')
    cen(PX['B'],  CEN0, 'B Cen')
    heatx_box(PX['C'], 8.0, 'Cooling\nCryst')
    reheater(PX['C'], 6.5, 'Reheater')
    cen(PX['C'], 4.4, 'C Cen')

    mingler(PX['B'], 5.95, 'B Mingler')
    mingler(PX['C'], 3.30, 'C Mingler')
    tank(13.5, 1.65, 1.8, 0.9, 'Remelt')

    # ══ Streams ═══════════════════════════════════════════════════════════
    # 1 syrup from evaporators, 2 remelt return joining it, 34 combined feed
    seg([(0.5, Y_SYR), (18.25, Y_SYR)], SYRC, lw=2.2)
    lbl(0.5, Y_SYR + 0.45, 'Syrup from Evaporators', fs=9.5, bold=True,
        color=SYRC, ha='left')
    tag(0.8, Y_SYR, 1, SYRC)
    dot(1.3, Y_SYR, SYRC)
    seg([(12.6, 1.65), (1.3, 1.65), (1.3, Y_SYR - 0.5)], RMC)
    arr(1.3, Y_SYR - 0.5, 1.3, Y_SYR, RMC)    # head onto the syrup line
    tag(1.3, 7.8, 2, RMC)

    # 3/4/5 syrup drops into A1, A2, Grain necks
    for x, t in [(PX['A1'] - 0.25, 3), (PX['A2'] - 0.25, 4), (PX['GR'] - 0.25, 5)]:
        dot(x, Y_SYR, SYRC)
        arr(x, Y_SYR, x, NECK, SYRC)
        tag(x, 13.05, t, SYRC)

    # 20/21 B magma footings along the very top
    seg([(PX['B'], 4.6), (2.0, 4.6), (2.0, Y_BTOP), (PX['A2'] + 0.25, Y_BTOP)], MAGC)
    dot(PX['A1'] + 0.25, Y_BTOP, MAGC)
    arr(PX['A1'] + 0.25, Y_BTOP, PX['A1'] + 0.25, NECK, MAGC)
    arr(PX['A2'] + 0.25, Y_BTOP, PX['A2'] + 0.25, NECK, MAGC)
    tag(PX['A1'] + 0.25, 14.0, 20, MAGC)
    tag(PX['A2'] + 0.25, 14.0, 21, MAGC)

    # 30 C magma footing to B neck
    seg([(PX['C'], 2.6), (25.6, 2.6), (25.6, Y_CTOP), (PX['B'] + 0.35, Y_CTOP)], MAGC)
    arr(PX['B'] + 0.35, Y_CTOP, PX['B'] + 0.35, NECK, MAGC)
    tag(19.0, Y_CTOP, 30, MAGC)

    # 6/12/17/27 massecuites: pan -> centrifugal (or crystallizer for C)
    for key, t in [('A1', 6), ('A2', 12), ('B', 17)]:
        arr(PX[key], Y0, PX[key], CEN0 + 1.0, MASC, lw=2.0)
        tag(PX[key], 9.0, t, MASC)
    arr(PX['C'], Y0, PX['C'], 8.42, MASC, lw=2.0)
    tag(PX['C'], 9.2, 27, MASC)

    # C chain: cryst -> reheater -> C cen
    arr(PX['C'], 7.58, PX['C'], 6.95, MASC)
    arr(PX['C'], 6.05, PX['C'], 5.4, MASC)

    # 7/13/33 A sugars -> raw sugar
    seg([(PX['A2'], CEN0), (PX['A2'], 1.1), (2.2, 1.1)], SUGC, lw=2.0)
    seg([(PX['A1'], CEN0), (PX['A1'], 1.1)], SUGC, lw=2.0)
    dot(PX['A1'], 1.1, SUGC)
    arr(2.2, 1.1, 2.2, 0.35, SUGC, lw=2.2)
    lbl(2.2, 0.12, 'Raw Sugar', fs=10, bold=True, color=SUGC)
    tag(PX['A1'], 3.0, 7, SUGC)
    tag(PX['A2'], 3.0, 13, SUGC)
    tag(3.3, 1.1, 33, SUGC)

    # 8..11 A1 molasses (diluted) splits: A2 pan, Grain, B
    y1 = 6.2
    seg([(PX['A1'] + 0.8, CEN0 + 0.45), (PX['A1'] + 1.5, CEN0 + 0.45),
         (PX['A1'] + 1.5, y1), (16.2, y1)], MOLC)
    tag(6.6, y1, 8, MOLC)
    dot(7.6, y1, MOLC)                                   # -> A2
    seg([(7.6, y1), (7.6, 12.3)], MOLC)
    arr(7.6, 12.3, PX['A2'] - 0.5, 12.3, MOLC)
    tag(7.6, 9.6, 9, MOLC)
    dot(11.9, y1, MOLC)                                  # -> B
    seg([(11.9, y1), (11.9, 10.8)], MOLC)
    arr(11.9, 10.8, PX['B'] - 1.2, 10.8, MOLC)
    tag(11.9, 9.2, 11, MOLC)
    seg([(16.2, y1), (16.2, 11.5)], MOLC)                # -> Grain
    arr(16.2, 11.5, PX['GR'] - 1.2, 11.5, MOLC)
    tag(16.2, 8.8, 10, MOLC)

    # 14..16 A2 molasses splits: B, Grain
    y2 = 5.6
    seg([(PX['A2'] + 0.8, CEN0 + 0.45), (PX['A2'] + 1.5, CEN0 + 0.45),
         (PX['A2'] + 1.5, y2), (16.6, y2)], MOLC)
    tag(11.2, y2, 14, MOLC)
    dot(12.3, y2, MOLC)                                  # -> B
    seg([(12.3, y2), (12.3, 11.2)], MOLC)
    arr(12.3, 11.2, PX['B'] - 1.2, 11.2, MOLC)
    tag(12.3, 8.7, 15, MOLC)
    seg([(16.6, y2), (16.6, 11.15)], MOLC)               # -> Grain
    arr(16.6, 11.15, PX['GR'] - 1.2, 11.15, MOLC)
    tag(16.6, 8.3, 16, MOLC)

    # 23..25 B molasses splits: Grain, C
    y3 = 5.0
    seg([(PX['B'] + 0.8, CEN0 + 0.45), (PX['B'] + 1.7, CEN0 + 0.45),
         (PX['B'] + 1.7, y3), (21.0, y3)], MOLC)
    tag(16.35, y3, 23, MOLC)
    dot(17.0, y3, MOLC)                                  # -> Grain
    seg([(17.0, y3), (17.0, 10.8)], MOLC)
    arr(17.0, 10.8, PX['GR'] - 1.2, 10.8, MOLC)
    tag(17.0, 7.8, 24, MOLC)
    seg([(21.0, y3), (21.0, 10.7)], MOLC)                # -> C
    arr(21.0, 10.7, PX['C'] - 1.2, 10.7, MOLC)
    tag(21.0, 8.5, 25, MOLC)

    # 26 grain massecuite -> C pan
    seg([(PX['GR'], Y0), (PX['GR'], 9.0), (21.4, 9.0), (21.4, 11.3)], MASC)
    arr(21.4, 11.3, PX['C'] - 1.2, 11.3, MASC)
    tag(19.8, 9.0, 26, MASC)

    # 18/19/22 B sugar -> mingler -> magma -> junction (footings + remelt)
    arr(PX['B'], CEN0, PX['B'], 6.2, SUGC)
    tag(PX['B'], 6.6, 18, SUGC)
    seg([(PX['B'], 5.7), (PX['B'], 4.6)], MAGC)
    tag(PX['B'], 5.15, 19, MAGC)
    dot(PX['B'], 4.6, MAGC)
    arr(PX['B'], 4.6, PX['B'], 2.1, MAGC)                # -> remelt tank top
    tag(PX['B'], 3.2, 22, MAGC)

    # 28/29/31 C sugar -> mingler -> magma -> junction (B footing + remelt)
    arr(PX['C'], 4.4, PX['C'], 3.55, SUGC)
    tag(PX['C'], 3.95, 28, SUGC)
    seg([(PX['C'], 3.05), (PX['C'], 2.6)], MAGC)
    tag(PX['C'] - 0.55, 2.82, 29, MAGC)
    dot(PX['C'], 2.6, MAGC)
    seg([(PX['C'], 2.6), (PX['C'], 0.6), (15.0, 0.6), (15.0, 1.65)], MAGC)
    arr(15.0, 1.65, 14.4, 1.65, MAGC)
    tag(18.0, 0.6, 31, MAGC)

    # 32 final molasses out
    arr(PX['C'] + 0.85, 4.85, 26.6, 4.85, FINC, lw=2.2)
    lbl(26.3, 5.55, 'Final\nMolasses', fs=9.5, bold=True, color=FINC)
    tag(25.2, 4.85, 32, FINC)

    lbl(DW / 2, DH - 0.15, 'Four Boiling Double Magma — Pan Floor PFD',
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

    rows = _collect_streams(fb)
    half = (len(rows) + 1) // 2
    col_labels = ['#', 'Stream', 'Flow (lb/hr)', 'Brix', 'Purity']

    def fmt(r):
        return [str(r[0]), r[1], f'{r[2]:,.0f}', f'{r[3]:.1f}', f'{r[4]:.1f}']

    for block, bbox in [(rows[:half], [0.01, 0.44, 0.47, 0.54]),
                        (rows[half:], [0.52, 0.44, 0.47, 0.54])]:
        tab = axt.table(cellText=[fmt(r) for r in block], colLabels=col_labels,
                        cellLoc='right', bbox=bbox)
        style(tab, name_col=1)
        tab.auto_set_column_width([0, 1, 2, 3, 4])

    # ── Streams not shown: water additions & evaporation ─────────────────
    wleft, wright, (total_in, total_evap) = _collect_water(fb)
    axt.text(0.5, 0.405, 'STREAMS NOT SHOWN — WATER', transform=axt.transAxes,
             fontsize=10.5, fontweight='bold', color='#305496', ha='center')

    wcols = ['Stream', 'Flow (lb/hr)']
    for block, bbox in [(wleft,  [0.01, 0.055, 0.47, 0.33]),
                        (wright, [0.52, 0.055, 0.47, 0.33])]:
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
