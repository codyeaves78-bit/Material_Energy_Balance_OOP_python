import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ── Palette ───────────────────────────────────────────────────────────────────
SC  = '#1a78c2'   # syrup / syrup-as-fed
MA  = '#1e8449'   # A / A1 molasses
MA2 = '#52be80'   # A2 molasses (four-boiling)
MB  = '#117a65'   # B molasses
MC  = '#922b21'   # final molasses
MG  = '#d35400'   # magma footings
RC  = '#6c3483'   # remelt streams
GC  = '#6d4c41'   # grain massecuite
SU  = '#b7950b'   # sugar outputs
BOX_E = '#2c3e50'
PAN_F = '#fef9e7'
CEN_F = '#eaf4fb'
MIN_F = '#fdebd0'
REM_F = '#f4ecf7'
GRN_F = '#f0f4c3'


def _helpers(ax):
    def arr(x1, y1, x2, y2, c, lw=1.6, ls='solid'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle='->', color=c, lw=lw,
                linestyle=ls, shrinkA=0, shrinkB=0), clip_on=False)

    def seg(x1, y1, x2, y2, c, lw=1.6, ls='solid'):
        ax.plot([x1, x2], [y1, y2], color=c, lw=lw, ls=ls, zorder=4, clip_on=False)

    def lbl(x, y, txt, ha='center', va='center', fs=7.5, c='#1c2833', bold=False):
        ax.text(x, y, txt, ha=ha, va=va, fontsize=fs,
            color=c, fontweight='bold' if bold else 'normal',
            clip_on=False, zorder=7)

    def box(cx, cy, w, h, fc, ec=BOX_E, lw=1.8, z=3):
        ax.add_patch(mpatches.FancyBboxPatch(
            (cx - w/2, cy - h/2), w, h,
            boxstyle='round,pad=0.07', lw=lw,
            edgecolor=ec, facecolor=fc, zorder=z))

    def flbl(x, y, stream, ha='center', clr='#1c2833', fs=6.5):
        ax.text(x, y + 0.22, f'{stream.flow_lb_per_hr:,.0f} lb/hr',
            ha=ha, va='center', fontsize=fs, color=clr, clip_on=False, zorder=7)
        ax.text(x, y - 0.13, f'Bx {stream.brix:.1f}  Pu {stream.purity:.1f}',
            ha=ha, va='center', fontsize=max(fs - 0.5, 5.5), color=clr,
            clip_on=False, zorder=7)

    def dot(x, y, c, r=0.12):
        ax.add_patch(mpatches.Circle((x, y), r, color=c, zorder=5))

    return arr, seg, lbl, box, flbl, dot


def _pan_box(lbl, box, cx, cy, pan, W=2.8, H=2.6):
    box(cx, cy, W, H, PAN_F)
    lbl(cx, cy + H/2 - 0.32, pan.name, bold=True, fs=8.5)
    lbl(cx, cy + 0.12, f'{pan.massecuite_flow_lb_hr:,.0f} lb/hr', fs=7)
    lbl(cx, cy - 0.32, f'Bx {pan.masse_brix:.1f}  Pu {pan.masse_purity:.1f}', fs=7)
    lbl(cx, cy - 0.76, f'{pan.heating_surface_ft2:,.0f} ft²', fs=6, c='#666')


def _cen_box(lbl, box, cx, cy, cen, W=2.2, H=2.2):
    box(cx, cy, W, H, CEN_F)
    lbl(cx, cy + H/2 - 0.30, cen.name, bold=True, fs=8)
    lbl(cx, cy + 0.12, f'{cen.sugar_wet_lb_hr:,.0f} lb/hr sugar', fs=6.5)
    lbl(cx, cy - 0.30, f'{cen.molasses_flow_lb_hr:,.0f} lb/hr mol', fs=6.5)


def _min_box(lbl, box, cx, cy, title, magma, W=1.8, H=1.5):
    box(cx, cy, W, H, MIN_F)
    lbl(cx, cy + H/2 - 0.28, title, bold=True, fs=7.5)
    lbl(cx, cy - 0.06, f'{magma.flow_lb_per_hr:,.0f} lb/hr', fs=6.5)
    lbl(cx, cy - 0.44, f'Bx {magma.brix:.1f}  Pu {magma.purity:.1f}', fs=6.5)


# ─────────────────────────────────────────────────────────────────────────────
# THREE BOILING DOUBLE MAGMA
# ─────────────────────────────────────────────────────────────────────────────

def plot_three_boiling(obj, show=True, save_path=None):
    """PFD for a ThreeBoilingDoubleMagma instance."""

    DW, DH = 25, 21
    fig, ax = plt.subplots(figsize=(19, 13))
    ax.set_xlim(0, DW); ax.set_ylim(0, DH)
    ax.axis('off')
    fig.patch.set_facecolor('#f5f6fa')
    ax.set_facecolor('#f5f6fa')

    arr, seg, lbl, box, flbl, dot = _helpers(ax)

    # ── Column x-coords ───────────────────────────────────────────────────
    X_REM, X_A, X_B, X_GRAIN, X_C = 1.5, 5.5, 10.5, 15.5, 20.5

    # ── Row y-coords (generous spacing to prevent crowding) ───────────────
    Y_PAN  = 16.0;  PW, PH = 2.8, 2.6
    Y_CEN  = 11.5;  CW, CH = 2.2, 2.2
    Y_GRN  =  8.0;  GW, GH = 2.2, 2.2   # grain pans
    Y_MIN  =  5.5;  MW, MH = 1.8, 1.5   # B/C minglers
    Y_REM  =  8.0;  RW, RH = 1.8, 1.1   # remelt node (same Y as grain, diff X)
    Y_HWY  =  3.0                         # remelt return highway
    Y_SOUT =  4.0                         # A sugar output level (above highway)

    P_bot = Y_PAN - PH/2;  P_top = Y_PAN + PH/2
    C_bot = Y_CEN - CH/2;  C_top = Y_CEN + CH/2
    G_bot = Y_GRN - GH/2;  G_top = Y_GRN + GH/2
    M_bot = Y_MIN - MH/2;  M_top = Y_MIN + MH/2

    # ── Pre-compute split flows ────────────────────────────────────────────
    a_mol = obj.A_centrifugals.molasses_stream
    b_mol = obj.B_centrifugals.molasses_stream
    saf   = obj.syrup_as_fed

    a_mol_B_flow  = obj.a_mol_B_pans_pct   / 100 * a_mol.flow_lb_per_hr
    a_mol_gr_flow = obj.a_mol_to_grain_pct / 100 * a_mol.flow_lb_per_hr
    b_mol_C_flow  = obj.b_mol_C_pans_pct   / 100 * b_mol.flow_lb_per_hr
    b_mol_gr_flow = obj.b_mol_to_grain_pct / 100 * b_mol.flow_lb_per_hr
    b_ftg_flow    = (100 - obj.b_magma_remelt_pct) / 100 * obj._b_magma.flow_lb_per_hr
    c_ftg_flow    = (100 - obj.c_magma_remelt_pct) / 100 * obj._c_magma.flow_lb_per_hr
    syr_gr_flow   = obj.syrup_to_grain_pct / 100 * saf.flow_lb_per_hr
    syr_A_flow    = obj.syrup_to_A_pans_pct / 100 * saf.flow_lb_per_hr

    # ── Title + legend ────────────────────────────────────────────────────
    lbl(DW/2, DH - 0.4,
        'THREE BOILING DOUBLE MAGMA  —  Process Flow Diagram',
        fs=13, bold=True)
    items = [('Syrup/Feed', SC), ('A Molasses', MA), ('B Molasses', MB),
             ('Final Mol', MC), ('Magma Footing', MG), ('Remelt', RC),
             ('Grain Masse', GC), ('Sugar Out', SU)]
    lx = 0.2
    for txt, col in items:
        seg(lx, DH - 1.1, lx + 0.45, DH - 1.1, col, lw=2.2)
        lbl(lx + 0.58, DH - 1.1, txt, ha='left', fs=7, c=col)
        lx += 3.0

    # ══════════════════════════════════════════════════════════════════════
    # Equipment
    # ══════════════════════════════════════════════════════════════════════
    _pan_box(lbl, box, X_A, Y_PAN, obj.A_pans)
    _pan_box(lbl, box, X_B, Y_PAN, obj.B_pans)
    _pan_box(lbl, box, X_C, Y_PAN, obj.C_pans)

    _cen_box(lbl, box, X_A, Y_CEN, obj.A_centrifugals)
    _cen_box(lbl, box, X_B, Y_CEN, obj.B_centrifugals)
    _cen_box(lbl, box, X_C, Y_CEN, obj.C_centrifugals)

    _min_box(lbl, box, X_B, Y_MIN, 'B Magma', obj._b_magma)
    _min_box(lbl, box, X_C, Y_MIN, 'C Magma', obj._c_magma)

    box(X_GRAIN, Y_GRN, GW, GH, GRN_F)
    lbl(X_GRAIN, Y_GRN + GH/2 - 0.30, obj._grain_pans_cfg.name, bold=True, fs=8.5)
    lbl(X_GRAIN, Y_GRN + 0.10, f'{obj.grain_pans.massecuite_flow_lb_hr:,.0f} lb/hr', fs=7)
    lbl(X_GRAIN, Y_GRN - 0.35, f'Bx {obj.grain_pans.masse_brix:.1f}  Pu {obj.grain_pans.masse_purity:.1f}', fs=7)

    ax.add_patch(mpatches.Ellipse((X_REM, Y_REM), RW, RH,
        edgecolor=RC, facecolor=REM_F, lw=2.0, zorder=3))
    lbl(X_REM, Y_REM, 'REMELT', bold=True, fs=8, c=RC)

    # ══════════════════════════════════════════════════════════════════════
    # Forward streams
    # ══════════════════════════════════════════════════════════════════════

    # 1. Syrup in — enters remelt ellipse from the TOP (vertical arrow)
    #    Start arrow below the legend row (which sits at DH-1.1) to avoid overlap.
    arr(X_REM, DH - 2.0, X_REM, Y_REM + RH/2, SC, lw=2.2)
    lbl(X_REM + 0.55, DH - 2.0,  'SYRUP IN', ha='left', bold=True, fs=9, c=SC)
    lbl(X_REM + 0.55, DH - 2.50, f'{obj.syrup.flow_lb_per_hr:,.0f} lb/hr', ha='left', fs=7, c=SC)
    lbl(X_REM + 0.55, DH - 2.88, f'Bx {obj.syrup.brix:.1f}  Pu {obj.syrup.purity:.1f}', ha='left', fs=7, c=SC)

    # 2. Remelt → A pan: go right then up
    rx = X_A - PW/2 - 0.30
    seg(X_REM + RW/2, Y_REM, rx, Y_REM, SC, lw=2.0)
    seg(rx, Y_REM, rx, Y_PAN - 0.35, SC, lw=2.0)
    arr(rx, Y_PAN - 0.35, X_A - PW/2, Y_PAN - 0.35, SC, lw=2.0)
    # label on horizontal segment, below line to avoid overlap with syrup label
    lbl((X_REM + RW/2 + rx)/2, Y_REM - 0.50,
        f'→A: {syr_A_flow:,.0f} lb/hr  Bx {saf.brix:.1f}  Pu {saf.purity:.1f}', fs=6.5, c=SC)

    # 3. Syrup → grain (dashed branch off the same Y_REM horizontal)
    dot(rx, Y_REM, SC)
    seg(rx, Y_REM, X_GRAIN - GW/2, Y_REM, SC, lw=1.3, ls='dashed')
    arr(X_GRAIN - GW/2, Y_REM, X_GRAIN - GW/2, G_bot + 0.12, SC, lw=1.3)
    # label above the dashed line to separate from the remelt→A label below
    lbl((rx + X_GRAIN - GW/2)/2, Y_REM + 0.45,
        f'Syrup→Grain  {syr_gr_flow:,.0f} lb/hr', fs=6.5, c=SC)

    # 4. A pan → A centrifugal
    arr(X_A, P_bot, X_A, C_top, '#555', lw=1.8)
    lbl(X_A + 0.80, (P_bot + C_top)/2,
        f'A Massecuite\n{obj.A_pans.massecuite_flow_lb_hr:,.0f} lb/hr\nBx {obj.A_pans.masse_brix:.1f}  Pu {obj.A_pans.masse_purity:.1f}',
        fs=6.5, c='#333')

    # 5. A cen → A sugar (short drop, clearly labeled on the right)
    seg(X_A, C_bot, X_A, Y_SOUT, SU, lw=1.8)
    arr(X_A, Y_SOUT, X_A, Y_SOUT - 0.4, SU, lw=1.8)
    lbl(X_A + 0.65, (C_bot + Y_SOUT)/2,
        f'A SUGAR\n{obj.A_centrifugals.sugar_wet_lb_hr:,.0f} lb/hr\nBx {obj.A_centrifugals.sugar_brix:.1f}  Pu {obj.A_centrifugals.sugar_purity:.1f}',
        ha='left', fs=6.5, c=SU)

    # 6. A mol → B pan (right exit of A cen, horizontal then up)
    a_riser_x = X_B - PW/2 - 0.22
    seg(X_A + CW/2, Y_CEN, a_riser_x, Y_CEN, MA, lw=1.8)
    seg(a_riser_x, Y_CEN, a_riser_x, Y_PAN - 0.35, MA, lw=1.8)
    arr(a_riser_x, Y_PAN - 0.35, X_B - PW/2, Y_PAN - 0.35, MA, lw=1.8)
    lbl((X_A + CW/2 + a_riser_x)/2, Y_CEN + 0.45,
        f'A Mol→B  {a_mol_B_flow:,.0f} lb/hr\nBx {a_mol.brix:.1f}  Pu {a_mol.purity:.1f}',
        fs=6.5, c=MA)

    # 7. A mol → grain (branch at X_A+CW/2, goes right then down into grain top)
    agr_bx = X_A + CW/2 + 0.5
    dot(agr_bx, Y_CEN, MA)
    seg(agr_bx, Y_CEN, agr_bx, G_top + 0.20, MA, lw=1.3, ls='dashed')
    seg(agr_bx, G_top + 0.20, X_GRAIN - GW/2 + 0.35, G_top + 0.20, MA, lw=1.3, ls='dashed')
    arr(X_GRAIN - GW/2 + 0.35, G_top + 0.20, X_GRAIN - GW/2 + 0.35, G_top, MA, lw=1.3)
    lbl(agr_bx - 0.48, (Y_CEN + Y_GRN)/2 + 0.30,
        f'A Mol→Grain\n{a_mol_gr_flow:,.0f} lb/hr', ha='right', fs=6.5, c=MA)

    # 8. B pan → B centrifugal
    arr(X_B, P_bot, X_B, C_top, '#555', lw=1.8)
    lbl(X_B + 0.80, (P_bot + C_top)/2,
        f'B Massecuite\n{obj.B_pans.massecuite_flow_lb_hr:,.0f} lb/hr\nBx {obj.B_pans.masse_brix:.1f}  Pu {obj.B_pans.masse_purity:.1f}',
        fs=6.5, c='#333')

    # 9. B cen → B mingler
    arr(X_B, C_bot, X_B, M_top, '#555', lw=1.8)
    lbl(X_B + 0.65, (C_bot + M_top)/2, 'B Sugar', ha='left', fs=6.5, c='#555')

    # 10. B mol → C pan
    b_riser_x = X_C - PW/2 - 0.22
    seg(X_B + CW/2, Y_CEN, b_riser_x, Y_CEN, MB, lw=1.8)
    seg(b_riser_x, Y_CEN, b_riser_x, Y_PAN - 0.35, MB, lw=1.8)
    arr(b_riser_x, Y_PAN - 0.35, X_C - PW/2, Y_PAN - 0.35, MB, lw=1.8)
    lbl((X_B + CW/2 + b_riser_x)/2, Y_CEN + 0.45,
        f'B Mol→C  {b_mol_C_flow:,.0f} lb/hr\nBx {b_mol.brix:.1f}  Pu {b_mol.purity:.1f}',
        fs=6.5, c=MB)

    # 11. B mol → grain
    bgr_bx = X_B + CW/2 + 0.5
    dot(bgr_bx, Y_CEN, MB)
    seg(bgr_bx, Y_CEN, bgr_bx, G_top + 0.40, MB, lw=1.3, ls='dashed')
    seg(bgr_bx, G_top + 0.40, X_GRAIN + GW/2 - 0.35, G_top + 0.40, MB, lw=1.3, ls='dashed')
    arr(X_GRAIN + GW/2 - 0.35, G_top + 0.40, X_GRAIN + GW/2 - 0.35, G_top, MB, lw=1.3)
    lbl(bgr_bx - 0.48, (Y_CEN + Y_GRN)/2,
        f'B Mol→Grain\n{b_mol_gr_flow:,.0f} lb/hr', ha='right', fs=6.5, c=MB)

    # 12. Grain → C pan (exit right, riser up, enter C pan left-high)
    gr_rx = X_C - PW/2 - 0.06
    seg(X_GRAIN + GW/2, Y_GRN, gr_rx, Y_GRN, GC, lw=1.8)
    seg(gr_rx, Y_GRN, gr_rx, Y_PAN + 0.35, GC, lw=1.8)
    arr(gr_rx, Y_PAN + 0.35, X_C - PW/2, Y_PAN + 0.35, GC, lw=1.8)
    lbl(gr_rx - 0.50, (Y_GRN + Y_PAN)/2,
        f'Grain Masse\n{obj.grain_pans.massecuite_flow_lb_hr:,.0f} lb/hr\nBx {obj.grain_pans.masse_brix:.1f}  Pu {obj.grain_pans.masse_purity:.1f}',
        ha='right', fs=6.5, c=GC)

    # 13. C pan → C centrifugal
    arr(X_C, P_bot, X_C, C_top, '#555', lw=1.8)
    lbl(X_C + 0.80, (P_bot + C_top)/2,
        f'C Massecuite\n{obj.C_pans.massecuite_flow_lb_hr:,.0f} lb/hr\nBx {obj.C_pans.masse_brix:.1f}  Pu {obj.C_pans.masse_purity:.1f}',
        fs=6.5, c='#333')

    # 14. C cen → C mingler
    arr(X_C, C_bot, X_C, M_top, '#555', lw=1.8)
    lbl(X_C + 0.65, (C_bot + M_top)/2, 'C Sugar', ha='left', fs=6.5, c='#555')

    # 15. Final molasses → right exit
    arr(X_C + CW/2, Y_CEN, DW - 0.2, Y_CEN, MC, lw=2.0)
    lbl(DW - 0.25, Y_CEN + 0.60, 'FINAL MOLASSES', ha='right', bold=True, fs=9, c=MC)
    flbl(DW - 0.25, Y_CEN - 0.15, obj.C_centrifugals.molasses_stream, ha='right', clr=MC, fs=7)

    # ══════════════════════════════════════════════════════════════════════
    # Backward: magma footings (orange) — routed left of the receiving pan
    # ══════════════════════════════════════════════════════════════════════

    # 16. B magma footing → A pan
    #   horizontal left at Y_MIN from B min to a riser x just left of A pan
    b_ftg_rx = X_A - PW/2 - 0.55
    seg(X_B - MW/2, Y_MIN, b_ftg_rx, Y_MIN, MG, lw=1.6)
    seg(b_ftg_rx, Y_MIN, b_ftg_rx, Y_PAN + 0.35, MG, lw=1.6)
    arr(b_ftg_rx, Y_PAN + 0.35, X_A - PW/2, Y_PAN + 0.35, MG, lw=1.6)
    # label ABOVE the horizontal run to keep it clear of things below
    lbl((b_ftg_rx + X_B - MW/2)/2, Y_MIN + 0.40,
        f'B Magma Footing → A   {b_ftg_flow:,.0f} lb/hr  Bx {obj._b_magma.brix:.1f}  Pu {obj._b_magma.purity:.1f}',
        fs=6.5, c=MG)

    # 17. C magma footing → B pan
    #   horizontal left at Y_MIN - 0.55 (below B footing run) from C min to riser left of B pan
    c_ftg_rx = X_B - PW/2 - 0.55
    Y_C_FTG  = Y_MIN - 0.55
    seg(X_C - MW/2, Y_MIN, X_C - MW/2, Y_C_FTG, MG, lw=1.6)
    seg(X_C - MW/2, Y_C_FTG, c_ftg_rx, Y_C_FTG, MG, lw=1.6)
    seg(c_ftg_rx, Y_C_FTG, c_ftg_rx, Y_PAN + 0.35, MG, lw=1.6)
    arr(c_ftg_rx, Y_PAN + 0.35, X_B - PW/2, Y_PAN + 0.35, MG, lw=1.6)
    lbl((c_ftg_rx + X_C - MW/2)/2, Y_C_FTG - 0.38,
        f'C Magma Footing → B   {c_ftg_flow:,.0f} lb/hr  Bx {obj._c_magma.brix:.1f}  Pu {obj._c_magma.purity:.1f}',
        fs=6.5, c=MG)

    # ══════════════════════════════════════════════════════════════════════
    # Remelt returns (purple dashed) — below Y_MIN
    # ══════════════════════════════════════════════════════════════════════

    # 18. B remelt: drop from B mingler bottom → highway → up to remelt node
    seg(X_B, M_bot, X_B, Y_HWY, RC, lw=1.4, ls='dashed')
    seg(X_B, Y_HWY, X_REM, Y_HWY, RC, lw=1.4, ls='dashed')
    arr(X_REM, Y_HWY, X_REM, Y_REM - RH/2, RC, lw=1.4)
    lbl((X_B + X_REM)/2, Y_HWY + 0.38,
        f'B Remelt  {obj._b_remelt.flow_lb_per_hr:,.0f} lb/hr  Bx {obj._b_remelt.brix:.1f}',
        fs=6.5, c=RC)

    # 19. C remelt: drop from C mingler bottom → highway (offset +0.25) → left → up to remelt node
    seg(X_C, M_bot, X_C, Y_HWY + 0.28, RC, lw=1.4, ls='dashed')
    seg(X_C, Y_HWY + 0.28, X_REM + 0.20, Y_HWY + 0.28, RC, lw=1.4, ls='dashed')
    arr(X_REM + 0.20, Y_HWY + 0.28, X_REM + 0.20, Y_REM - RH/2, RC, lw=1.4)
    lbl((X_C + X_REM)/2, Y_HWY - 0.38,
        f'C Remelt  {obj._c_remelt.flow_lb_per_hr:,.0f} lb/hr  Bx {obj._c_remelt.brix:.1f}',
        fs=6.5, c=RC)

    # ── Footer ────────────────────────────────────────────────────────────
    a_sug = obj.A_centrifugals.sugar_stream
    pol_rec = a_sug.pol_flow / obj.syrup.pol_flow * 100
    lbl(DW/2, 0.55,
        f'Feed: {obj.syrup.flow_lb_per_hr:,.0f} lb/hr  |  '
        f'A Sugar: {obj.A_centrifugals.sugar_wet_lb_hr:,.0f} lb/hr  |  '
        f'Final Mol: {obj.C_centrifugals.molasses_flow_lb_hr:,.0f} lb/hr  |  '
        f'Pol Recovery: {pol_rec:.1f} %',
        fs=8.5, c='#444')

    fig.tight_layout(pad=0.4)
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# FOUR BOILING DOUBLE MAGMA
# ─────────────────────────────────────────────────────────────────────────────

def plot_four_boiling(obj, show=True, save_path=None):
    """PFD for a FourBoilingDoubleMagma instance."""

    DW, DH = 31, 21
    fig, ax = plt.subplots(figsize=(23, 13))
    ax.set_xlim(0, DW); ax.set_ylim(0, DH)
    ax.axis('off')
    fig.patch.set_facecolor('#f5f6fa')
    ax.set_facecolor('#f5f6fa')

    arr, seg, lbl, box, flbl, dot = _helpers(ax)

    # ── Column x-coords ───────────────────────────────────────────────────
    X_REM = 1.5
    X_A1  = 5.5
    X_A2  = 10.0
    X_B   = 15.0
    X_GRN = 20.0
    X_C   = 26.0

    # ── Row y-coords ──────────────────────────────────────────────────────
    Y_PAN  = 16.0;  PW, PH = 2.6, 2.6
    Y_CEN  = 11.5;  CW, CH = 2.2, 2.2
    Y_GRN  =  8.0;  GW, GH = 2.2, 2.2
    Y_MIN  =  5.5;  MW, MH = 1.8, 1.5
    Y_REM  =  8.0;  RW, RH = 1.8, 1.1
    Y_HWY  =  3.0
    Y_SOUT =  4.2                         # A1/A2 sugar stop level

    P_bot = Y_PAN - PH/2;  P_top = Y_PAN + PH/2
    C_bot = Y_CEN - CH/2;  C_top = Y_CEN + CH/2
    G_bot = Y_GRN - GH/2;  G_top = Y_GRN + GH/2
    M_bot = Y_MIN - MH/2;  M_top = Y_MIN + MH/2

    # ── Pre-compute split flows ────────────────────────────────────────────
    a1_mol  = obj.A1_centrifugals.molasses_stream
    a2_mol  = obj.A2_centrifugals.molasses_stream
    b_mol   = obj.B_centrifugals.molasses_stream
    saf     = obj.syrup_as_fed

    a1_A2_flow  = obj.a1_mol_to_A2_pct    / 100 * a1_mol.flow_lb_per_hr
    a1_gr_flow  = obj.a1_mol_to_grain_pct / 100 * a1_mol.flow_lb_per_hr
    a1_B_flow   = obj.a1_mol_to_B_pct     / 100 * a1_mol.flow_lb_per_hr
    a2_gr_flow  = obj.a2_mol_to_grain_pct / 100 * a2_mol.flow_lb_per_hr
    a2_B_flow   = obj.a2_mol_to_B_pct     / 100 * a2_mol.flow_lb_per_hr
    b_C_flow    = obj.b_mol_to_C_pct      / 100 * b_mol.flow_lb_per_hr
    b_gr_flow   = obj.b_mol_to_grain_pct  / 100 * b_mol.flow_lb_per_hr
    b_A1_ftg    = obj.b_magma_A1_footing_pct / 100 * obj._b_magma.flow_lb_per_hr
    b_A2_ftg    = obj.b_magma_A2_footing_pct / 100 * obj._b_magma.flow_lb_per_hr
    c_B_ftg     = obj.c_magma_B_footing_pct  / 100 * obj._c_magma.flow_lb_per_hr
    syr_A1_flow = obj.syrup_to_A1_pans_pct / 100 * saf.flow_lb_per_hr
    syr_A2_flow = obj.syrup_to_A2_pans_pct / 100 * saf.flow_lb_per_hr
    syr_gr_flow = obj.syrup_to_grain_pct   / 100 * saf.flow_lb_per_hr

    # ── Title + legend ────────────────────────────────────────────────────
    lbl(DW/2, DH - 0.4,
        'FOUR BOILING DOUBLE MAGMA  —  Process Flow Diagram',
        fs=13, bold=True)
    items = [('Syrup/Feed', SC), ('A1 Mol', MA), ('A2 Mol', MA2), ('B Mol', MB),
             ('Final Mol', MC), ('Magma Ftg', MG), ('Remelt', RC),
             ('Grain Masse', GC), ('Sugar Out', SU)]
    lx = 0.2
    for txt, col in items:
        seg(lx, DH - 1.1, lx + 0.40, DH - 1.1, col, lw=2.2)
        lbl(lx + 0.52, DH - 1.1, txt, ha='left', fs=7, c=col)
        lx += 3.4

    # ══════════════════════════════════════════════════════════════════════
    # Equipment
    # ══════════════════════════════════════════════════════════════════════
    _pan_box(lbl, box, X_A1, Y_PAN, obj.A1_pans, W=PW)
    _pan_box(lbl, box, X_A2, Y_PAN, obj.A2_pans, W=PW)
    _pan_box(lbl, box, X_B,  Y_PAN, obj.B_pans,  W=PW)
    _pan_box(lbl, box, X_C,  Y_PAN, obj.C_pans,  W=PW)

    _cen_box(lbl, box, X_A1, Y_CEN, obj.A1_centrifugals)
    _cen_box(lbl, box, X_A2, Y_CEN, obj.A2_centrifugals)
    _cen_box(lbl, box, X_B,  Y_CEN, obj.B_centrifugals)
    _cen_box(lbl, box, X_C,  Y_CEN, obj.C_centrifugals)

    _min_box(lbl, box, X_B, Y_MIN, 'B Magma', obj._b_magma)
    _min_box(lbl, box, X_C, Y_MIN, 'C Magma', obj._c_magma)

    box(X_GRN, Y_GRN, GW, GH, GRN_F)
    lbl(X_GRN, Y_GRN + GH/2 - 0.30, obj._grain_pans_cfg.name, bold=True, fs=8.5)
    lbl(X_GRN, Y_GRN + 0.10, f'{obj.grain_pans.massecuite_flow_lb_hr:,.0f} lb/hr', fs=7)
    lbl(X_GRN, Y_GRN - 0.35, f'Bx {obj.grain_pans.masse_brix:.1f}  Pu {obj.grain_pans.masse_purity:.1f}', fs=7)

    ax.add_patch(mpatches.Ellipse((X_REM, Y_REM), RW, RH,
        edgecolor=RC, facecolor=REM_F, lw=2.0, zorder=3))
    lbl(X_REM, Y_REM, 'REMELT', bold=True, fs=8, c=RC)

    # ══════════════════════════════════════════════════════════════════════
    # Forward streams
    # ══════════════════════════════════════════════════════════════════════

    # 1. Syrup — enters remelt ellipse from the TOP (vertical arrow)
    #    Start arrow below the legend row (DH-1.1) to avoid overlap.
    arr(X_REM, DH - 2.0, X_REM, Y_REM + RH/2, SC, lw=2.2)
    lbl(X_REM + 0.55, DH - 2.0,  'SYRUP IN', ha='left', bold=True, fs=9, c=SC)
    lbl(X_REM + 0.55, DH - 2.50, f'{obj.syrup.flow_lb_per_hr:,.0f} lb/hr', ha='left', fs=7, c=SC)
    lbl(X_REM + 0.55, DH - 2.88, f'Bx {obj.syrup.brix:.1f}  Pu {obj.syrup.purity:.1f}', ha='left', fs=7, c=SC)

    # 2. Remelt → A1 pan (riser on left side of A1)
    rx1 = X_A1 - PW/2 - 0.30
    seg(X_REM + RW/2, Y_REM, rx1, Y_REM, SC, lw=2.0)
    seg(rx1, Y_REM, rx1, Y_PAN - 0.35, SC, lw=2.0)
    arr(rx1, Y_PAN - 0.35, X_A1 - PW/2, Y_PAN - 0.35, SC, lw=2.0)
    # Label below the horizontal (between remelt exit and riser)
    lbl((X_REM + RW/2 + rx1)/2, Y_REM - 0.50,
        f'→A1: {syr_A1_flow:,.0f} lb/hr', fs=6.5, c=SC)

    # 3. Syrup → A2 (dashed branch, horizontal then riser)
    dot(rx1, Y_REM, SC)
    rx2 = X_A2 - PW/2 - 0.30
    seg(rx1, Y_REM, rx2, Y_REM, SC, lw=1.4, ls='dashed')
    seg(rx2, Y_REM, rx2, Y_PAN - 0.35, SC, lw=1.4, ls='dashed')
    arr(rx2, Y_PAN - 0.35, X_A2 - PW/2, Y_PAN - 0.35, SC, lw=1.4)
    # Label above the horizontal for separation from →A1 label below
    lbl((rx1 + rx2)/2, Y_REM + 0.50,
        f'→A2: {syr_A2_flow:,.0f} lb/hr', fs=6.5, c=SC)

    # 4. Syrup → grain (dashed, extends further right)
    dot(rx2, Y_REM, SC)
    seg(rx2, Y_REM, X_GRN - GW/2, Y_REM, SC, lw=1.2, ls='dashed')
    arr(X_GRN - GW/2, Y_REM, X_GRN - GW/2, G_bot + 0.12, SC, lw=1.2)
    # Label below — well separated from →A2 label above which is further left
    lbl((rx2 + X_GRN - GW/2)/2, Y_REM - 0.50,
        f'Syrup→Grain  {syr_gr_flow:,.0f} lb/hr', fs=6.5, c=SC)

    # 5. A1 pan → A1 cen
    arr(X_A1, P_bot, X_A1, C_top, '#555', lw=1.8)
    lbl(X_A1 + 0.78, (P_bot + C_top)/2,
        f'A1 Masse\n{obj.A1_pans.massecuite_flow_lb_hr:,.0f} lb/hr', fs=6.5, c='#333')

    # 6. A1 sugar out (short drop, label right)
    seg(X_A1, C_bot, X_A1, Y_SOUT, SU, lw=1.8)
    arr(X_A1, Y_SOUT, X_A1, Y_SOUT - 0.4, SU, lw=1.8)
    lbl(X_A1 + 0.65, (C_bot + Y_SOUT)/2,
        f'A1 SUGAR\n{obj.A1_centrifugals.sugar_wet_lb_hr:,.0f} lb/hr',
        ha='left', fs=6.5, c=SU)

    # 7. A1 mol → A2 pan (horizontal at Y_CEN then up)
    a1_riser_x = X_A2 - PW/2 - 0.22
    seg(X_A1 + CW/2, Y_CEN, a1_riser_x, Y_CEN, MA, lw=1.8)
    seg(a1_riser_x, Y_CEN, a1_riser_x, Y_PAN - 0.35, MA, lw=1.8)
    arr(a1_riser_x, Y_PAN - 0.35, X_A2 - PW/2, Y_PAN - 0.35, MA, lw=1.8)
    lbl((X_A1 + CW/2 + a1_riser_x)/2, Y_CEN + 0.45,
        f'A1 Mol→A2  {a1_A2_flow:,.0f} lb/hr\nBx {a1_mol.brix:.1f}  Pu {a1_mol.purity:.1f}',
        fs=6.5, c=MA)

    # 8. A1 mol → grain (branch — dot spaced 0.8 right of main mol exit)
    a1gr_bx = X_A1 + CW/2 + 0.8
    dot(a1gr_bx, Y_CEN, MA)
    seg(a1gr_bx, Y_CEN, a1gr_bx, G_top + 0.20, MA, lw=1.2, ls='dashed')
    seg(a1gr_bx, G_top + 0.20, X_GRN - GW/2 + 0.35, G_top + 0.20, MA, lw=1.2, ls='dashed')
    arr(X_GRN - GW/2 + 0.35, G_top + 0.20, X_GRN - GW/2 + 0.35, G_top, MA, lw=1.2)
    lbl(a1gr_bx - 0.45, (Y_CEN + Y_GRN)/2 + 0.3,
        f'A1 Mol→Grain\n{a1_gr_flow:,.0f} lb/hr', ha='right', fs=6.5, c=MA)

    # 9. A1 mol → B pan (branch — dot spaced 1.6 right of main mol exit)
    a1B_bx = X_A1 + CW/2 + 1.6
    a1B_hy = Y_GRN - 1.0          # horizontal routing level for this stream
    a1B_rx = X_B - PW/2 - 0.55
    dot(a1B_bx, Y_CEN, MA)
    seg(a1B_bx, Y_CEN, a1B_bx, a1B_hy, MA, lw=1.2, ls='dashed')
    seg(a1B_bx, a1B_hy, a1B_rx, a1B_hy, MA, lw=1.2, ls='dashed')
    seg(a1B_rx, a1B_hy, a1B_rx, Y_PAN + 0.35, MA, lw=1.2, ls='dashed')
    arr(a1B_rx, Y_PAN + 0.35, X_B - PW/2, Y_PAN + 0.35, MA, lw=1.2)
    # Label on the horizontal segment — clear of the A2 Mol→B label above (which is at Y_CEN+0.45)
    lbl((a1B_bx + a1B_rx)/2, a1B_hy + 0.42,
        f'A1 Mol→B   {a1_B_flow:,.0f} lb/hr', ha='center', fs=6.5, c=MA)

    # 10. A2 pan → A2 cen
    arr(X_A2, P_bot, X_A2, C_top, '#555', lw=1.8)
    lbl(X_A2 + 0.78, (P_bot + C_top)/2,
        f'A2 Masse\n{obj.A2_pans.massecuite_flow_lb_hr:,.0f} lb/hr', fs=6.5, c='#333')

    # 11. A2 sugar out
    seg(X_A2, C_bot, X_A2, Y_SOUT, SU, lw=1.8)
    arr(X_A2, Y_SOUT, X_A2, Y_SOUT - 0.4, SU, lw=1.8)
    lbl(X_A2 + 0.65, (C_bot + Y_SOUT)/2,
        f'A2 SUGAR\n{obj.A2_centrifugals.sugar_wet_lb_hr:,.0f} lb/hr',
        ha='left', fs=6.5, c=SU)

    # 12. A2 mol → B pan
    a2_riser_x = X_B - PW/2 - 0.22
    seg(X_A2 + CW/2, Y_CEN, a2_riser_x, Y_CEN, MA2, lw=1.8)
    seg(a2_riser_x, Y_CEN, a2_riser_x, Y_PAN - 0.35, MA2, lw=1.8)
    arr(a2_riser_x, Y_PAN - 0.35, X_B - PW/2, Y_PAN - 0.35, MA2, lw=1.8)
    lbl((X_A2 + CW/2 + a2_riser_x)/2, Y_CEN + 0.45,
        f'A2 Mol→B  {a2_B_flow:,.0f} lb/hr\nBx {a2_mol.brix:.1f}  Pu {a2_mol.purity:.1f}',
        fs=6.5, c=MA2)

    # 13. A2 mol → grain
    a2gr_bx = X_A2 + CW/2 + 0.5
    dot(a2gr_bx, Y_CEN, MA2)
    seg(a2gr_bx, Y_CEN, a2gr_bx, G_top + 0.40, MA2, lw=1.2, ls='dashed')
    seg(a2gr_bx, G_top + 0.40, X_GRN - GW/2 + 0.65, G_top + 0.40, MA2, lw=1.2, ls='dashed')
    arr(X_GRN - GW/2 + 0.65, G_top + 0.40, X_GRN - GW/2 + 0.65, G_top, MA2, lw=1.2)
    lbl(a2gr_bx - 0.45, (Y_CEN + Y_GRN)/2,
        f'A2 Mol→Grain\n{a2_gr_flow:,.0f} lb/hr', ha='right', fs=6.5, c=MA2)

    # 14. B pan → B cen
    arr(X_B, P_bot, X_B, C_top, '#555', lw=1.8)
    lbl(X_B + 0.78, (P_bot + C_top)/2,
        f'B Masse\n{obj.B_pans.massecuite_flow_lb_hr:,.0f} lb/hr', fs=6.5, c='#333')

    # 15. B cen → B mingler
    arr(X_B, C_bot, X_B, M_top, '#555', lw=1.8)
    lbl(X_B + 0.62, (C_bot + M_top)/2, 'B Sugar', ha='left', fs=6.5, c='#555')

    # 16. B mol → C pan
    b_riser_x = X_C - PW/2 - 0.22
    seg(X_B + CW/2, Y_CEN, b_riser_x, Y_CEN, MB, lw=1.8)
    seg(b_riser_x, Y_CEN, b_riser_x, Y_PAN - 0.35, MB, lw=1.8)
    arr(b_riser_x, Y_PAN - 0.35, X_C - PW/2, Y_PAN - 0.35, MB, lw=1.8)
    lbl((X_B + CW/2 + b_riser_x)/2, Y_CEN + 0.45,
        f'B Mol→C  {b_C_flow:,.0f} lb/hr\nBx {b_mol.brix:.1f}  Pu {b_mol.purity:.1f}',
        fs=6.5, c=MB)

    # 17. B mol → grain
    bgr_bx = X_B + CW/2 + 0.5
    dot(bgr_bx, Y_CEN, MB)
    seg(bgr_bx, Y_CEN, bgr_bx, G_top + 0.60, MB, lw=1.2, ls='dashed')
    seg(bgr_bx, G_top + 0.60, X_GRN + GW/2 - 0.35, G_top + 0.60, MB, lw=1.2, ls='dashed')
    arr(X_GRN + GW/2 - 0.35, G_top + 0.60, X_GRN + GW/2 - 0.35, G_top, MB, lw=1.2)
    lbl(bgr_bx - 0.45, (Y_CEN + Y_GRN)/2 - 0.2,
        f'B Mol→Grain\n{b_gr_flow:,.0f} lb/hr', ha='right', fs=6.5, c=MB)

    # 18. Grain → C pan
    gr_rx = X_C - PW/2 - 0.06
    seg(X_GRN + GW/2, Y_GRN, gr_rx, Y_GRN, GC, lw=1.8)
    seg(gr_rx, Y_GRN, gr_rx, Y_PAN + 0.35, GC, lw=1.8)
    arr(gr_rx, Y_PAN + 0.35, X_C - PW/2, Y_PAN + 0.35, GC, lw=1.8)
    lbl(gr_rx - 0.50, (Y_GRN + Y_PAN)/2,
        f'Grain Masse\n{obj.grain_pans.massecuite_flow_lb_hr:,.0f} lb/hr\nBx {obj.grain_pans.masse_brix:.1f}  Pu {obj.grain_pans.masse_purity:.1f}',
        ha='right', fs=6.5, c=GC)

    # 19. C pan → C cen
    arr(X_C, P_bot, X_C, C_top, '#555', lw=1.8)
    lbl(X_C + 0.78, (P_bot + C_top)/2,
        f'C Masse\n{obj.C_pans.massecuite_flow_lb_hr:,.0f} lb/hr', fs=6.5, c='#333')

    # 20. C cen → C mingler
    arr(X_C, C_bot, X_C, M_top, '#555', lw=1.8)
    lbl(X_C + 0.62, (C_bot + M_top)/2, 'C Sugar', ha='left', fs=6.5, c='#555')

    # 21. Final molasses
    arr(X_C + CW/2, Y_CEN, DW - 0.2, Y_CEN, MC, lw=2.0)
    lbl(DW - 0.25, Y_CEN + 0.60, 'FINAL MOLASSES', ha='right', bold=True, fs=9, c=MC)
    flbl(DW - 0.25, Y_CEN - 0.15, obj.C_centrifugals.molasses_stream, ha='right', clr=MC, fs=7)

    # ══════════════════════════════════════════════════════════════════════
    # Magma footings (orange) — all routes at/above Y_MIN
    # ══════════════════════════════════════════════════════════════════════

    # 22. B magma → A1 pan
    b_A1_rx = X_A1 - PW/2 - 0.55
    seg(X_B - MW/2, Y_MIN, b_A1_rx, Y_MIN, MG, lw=1.6)
    seg(b_A1_rx, Y_MIN, b_A1_rx, Y_PAN + 0.35, MG, lw=1.6)
    arr(b_A1_rx, Y_PAN + 0.35, X_A1 - PW/2, Y_PAN + 0.35, MG, lw=1.6)
    lbl((b_A1_rx + X_B - MW/2)/2, Y_MIN + 0.42,
        f'B Magma → A1   {b_A1_ftg:,.0f} lb/hr  Bx {obj._b_magma.brix:.1f}',
        fs=6.5, c=MG)

    # 23. B magma → A2 pan (offset to Y_MIN - 0.55 to separate from A1 route)
    b_A2_rx = X_A2 - PW/2 - 0.55
    Y_B_A2  = Y_MIN - 0.55
    seg(X_B - MW/2, Y_MIN, X_B - MW/2, Y_B_A2, MG, lw=1.6)
    seg(X_B - MW/2, Y_B_A2, b_A2_rx, Y_B_A2, MG, lw=1.6)
    seg(b_A2_rx, Y_B_A2, b_A2_rx, Y_PAN + 0.35, MG, lw=1.6)
    arr(b_A2_rx, Y_PAN + 0.35, X_A2 - PW/2, Y_PAN + 0.35, MG, lw=1.6)
    lbl((b_A2_rx + X_B - MW/2)/2, Y_B_A2 - 0.38,
        f'B Magma → A2   {b_A2_ftg:,.0f} lb/hr', fs=6.5, c=MG)

    # 24. C magma → B pan (offset to Y_MIN + 0.55 to go above the B→A routes)
    c_B_rx  = X_B - PW/2 - 0.22
    Y_C_B   = Y_MIN + 0.55
    seg(X_C - MW/2, Y_MIN, X_C - MW/2, Y_C_B, MG, lw=1.6)
    seg(X_C - MW/2, Y_C_B, c_B_rx, Y_C_B, MG, lw=1.6)
    seg(c_B_rx, Y_C_B, c_B_rx, Y_PAN + 0.35, MG, lw=1.6)
    arr(c_B_rx, Y_PAN + 0.35, X_B - PW/2, Y_PAN + 0.35, MG, lw=1.6)
    lbl((c_B_rx + X_C - MW/2)/2, Y_C_B + 0.38,
        f'C Magma → B   {c_B_ftg:,.0f} lb/hr  Bx {obj._c_magma.brix:.1f}',
        fs=6.5, c=MG)

    # ══════════════════════════════════════════════════════════════════════
    # Remelt returns (purple dashed) — below Y_MIN, clearly separated
    # ══════════════════════════════════════════════════════════════════════

    # 25. B remelt
    seg(X_B, M_bot, X_B, Y_HWY, RC, lw=1.4, ls='dashed')
    seg(X_B, Y_HWY, X_REM, Y_HWY, RC, lw=1.4, ls='dashed')
    arr(X_REM, Y_HWY, X_REM, Y_REM - RH/2, RC, lw=1.4)
    lbl((X_B + X_REM)/2, Y_HWY + 0.40,
        f'B Remelt  {obj._b_remelt.flow_lb_per_hr:,.0f} lb/hr  Bx {obj._b_remelt.brix:.1f}',
        fs=6.5, c=RC)

    # 26. C remelt (offset highway to Y_HWY + 0.30)
    seg(X_C, M_bot, X_C, Y_HWY + 0.30, RC, lw=1.4, ls='dashed')
    seg(X_C, Y_HWY + 0.30, X_REM + 0.22, Y_HWY + 0.30, RC, lw=1.4, ls='dashed')
    arr(X_REM + 0.22, Y_HWY + 0.30, X_REM + 0.22, Y_REM - RH/2, RC, lw=1.4)
    lbl((X_C + X_REM)/2, Y_HWY - 0.38,
        f'C Remelt  {obj._c_remelt.flow_lb_per_hr:,.0f} lb/hr  Bx {obj._c_remelt.brix:.1f}',
        fs=6.5, c=RC)

    # ── Footer ────────────────────────────────────────────────────────────
    a1_sug = obj.A1_centrifugals.sugar_stream
    a2_sug = obj.A2_centrifugals.sugar_stream
    pol_rec = (a1_sug.pol_flow + a2_sug.pol_flow) / obj.syrup.pol_flow * 100
    lbl(DW/2, 0.55,
        f'Feed: {obj.syrup.flow_lb_per_hr:,.0f} lb/hr  |  '
        f'A1+A2 Sugar: {obj.A1_centrifugals.sugar_wet_lb_hr + obj.A2_centrifugals.sugar_wet_lb_hr:,.0f} lb/hr  |  '
        f'Final Mol: {obj.C_centrifugals.molasses_flow_lb_hr:,.0f} lb/hr  |  '
        f'Pol Recovery: {pol_rec:.1f} %',
        fs=8.5, c='#444')

    fig.tight_layout(pad=0.4)
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
    if show:
        plt.show()
    return fig
