import matplotlib
matplotlib.use('Agg')
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
WA  = '#2e86c1'   # water (wash / dilution / mingler)
BOX_E = '#2c3e50'
PAN_F = '#fef9e7'
CEN_F = '#eaf4fb'
TANK_F = '#eafaf1'
MAG_F = '#fdebd0'
GRN_F = '#f0f4c3'


def _helpers(ax):
    def arr(x1, y1, x2, y2, c, lw=1.6, ls='solid'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
            arrowprops=dict(arrowstyle='->', color=c, lw=lw,
                linestyle=ls, shrinkA=0, shrinkB=0), clip_on=False, zorder=4)

    def lbl(x, y, txt, ha='center', va='center', fs=7.5, c='#1c2833', bold=False):
        ax.text(x, y, txt, ha=ha, va=va, fontsize=fs,
            color=c, fontweight='bold' if bold else 'normal',
            clip_on=False, zorder=7)

    def box(cx, cy, w, h, fc, ec=BOX_E, lw=1.8, z=3):
        ax.add_patch(mpatches.FancyBboxPatch(
            (cx - w/2, cy - h/2), w, h,
            boxstyle='round,pad=0.07', lw=lw,
            edgecolor=ec, facecolor=fc, zorder=z))

    def stub_h(x1, y, x2, name, stream, c, name_above=True, fs=6.3, name_fs=6.8,
               ha='center', gap=0.30, show_purity=True):
        """Short horizontal stub arrow (not connected to another box) with a 2-line label."""
        arr(x1, y, x2, y, c, lw=1.7)
        mx = (x1 + x2) / 2
        txt = f'{stream.flow_lb_per_hr:,.0f} lb/hr'
        if show_purity:
            txt += f'   Pu {stream.purity:.1f}'
        if name_above:
            lbl(mx, y + gap, name, ha=ha, bold=True, fs=name_fs, c=c)
            lbl(mx, y - gap, txt, ha=ha, fs=fs, c=c)
        else:
            lbl(mx, y - gap, name, ha=ha, bold=True, fs=name_fs, c=c)
            lbl(mx, y + gap, txt, ha=ha, fs=fs, c=c)

    def stub_v(x, y1, y2, name, stream, c, side='right', fs=6.3, name_fs=6.8,
               show_purity=True):
        """Short vertical stub arrow with a 2-line label placed beside it."""
        arr(x, y1, x, y2, c, lw=1.7)
        my = (y1 + y2) / 2
        ha = 'left' if side == 'right' else 'right'
        ox = 0.15 if side == 'right' else -0.15
        txt = f'{stream.flow_lb_per_hr:,.0f} lb/hr'
        if show_purity:
            txt += f'   Pu {stream.purity:.1f}'
        lbl(x + ox, my + 0.16, name, ha=ha, bold=True, fs=name_fs, c=c)
        lbl(x + ox, my - 0.16, txt, ha=ha, fs=fs, c=c)

    return arr, lbl, box, stub_h, stub_v


def _pan_box(lbl, box, cx, cy, pan, W=2.6, H=2.4):
    box(cx, cy, W, H, PAN_F)
    lbl(cx, cy + H/2 - 0.30, pan.name, bold=True, fs=8.5)
    lbl(cx, cy + 0.10, f'{pan.massecuite_flow_lb_hr:,.0f} lb/hr', fs=7)
    lbl(cx, cy - 0.30, f'Bx {pan.masse_brix:.1f}  Pu {pan.masse_purity:.1f}', fs=7)
    lbl(cx, cy - 0.72, f'{pan.heating_surface_ft2:,.0f} ft²', fs=6, c='#666')


def _cen_box(lbl, box, cx, cy, cen, W=2.0, H=1.8):
    box(cx, cy, W, H, CEN_F)
    lbl(cx, cy + H/2 - 0.28, cen.name, bold=True, fs=7.8)
    lbl(cx, cy + 0.08, f'{cen.sugar_wet_lb_hr:,.0f} lb/hr sugar', fs=6.3)
    lbl(cx, cy - 0.28, f'{cen.molasses_flow_lb_hr:,.0f} lb/hr mol', fs=6.3)


def _tank_box(lbl, box, cx, cy, title, W=2.6, H=1.3):
    box(cx, cy, W, H, TANK_F)
    lbl(cx, cy, title, bold=True, fs=8.5)


def _mag_box(lbl, box, cx, cy, title, magma, W=2.0, H=1.3):
    box(cx, cy, W, H, MAG_F)
    lbl(cx, cy + H/2 - 0.28, title, bold=True, fs=7.5)
    lbl(cx, cy - 0.10, f'{magma.flow_lb_per_hr:,.0f} lb/hr  Pu {magma.purity:.1f}', fs=6.3)


def plot_three_boiling(obj, show=True, save_path=None):
    DW, DH = 27, 21
    fig, ax = plt.subplots(figsize=(20, 14))
    ax.set_xlim(0, DW); ax.set_ylim(0, DH)
    ax.axis('off')
    fig.patch.set_facecolor('#f5f6fa')
    ax.set_facecolor('#f5f6fa')

    arr, lbl, box, stub_h, stub_v = _helpers(ax)

    # ── Columns (bottom process row) ────────────────────────────────────
    X_A, X_B, X_GRAIN, X_C = 4.5, 10.5, 16.5, 22.5
    PW, PH = 2.6, 2.4
    CW, CH = 2.0, 1.8
    MW, MH = 2.0, 1.3

    Y_TANK = 17.4;  TW, TH = 2.6, 1.3
    Y_PAN  = 13.6
    Y_CEN  =  9.7
    Y_MAG  =  6.0

    P_bot = Y_PAN - PH/2; P_top = Y_PAN + PH/2; P_L = X_A  # placeholder
    C_bot = Y_CEN - CH/2; C_top = Y_CEN + CH/2

    # ── Top row tank x-coords ───────────────────────────────────────────
    X_SYR, X_AMOL, X_BMOL = 4.5, 11.5, 18.5

    # ── Precompute streams ────────────────────────────────────────────
    a_mol      = obj.A_centrifugals.molasses_stream
    b_mol      = obj.B_centrifugals.molasses_stream
    a_mol_dil  = obj._a_mol_diluted
    b_mol_dil  = obj._b_mol_diluted
    saf        = obj.syrup_as_fed

    a_mol_B_flow  = obj.a_mol_B_pans_pct   / 100 * a_mol_dil.flow_lb_per_hr
    a_mol_gr_flow = obj.a_mol_to_grain_pct / 100 * a_mol_dil.flow_lb_per_hr
    a_mol_topoff  = obj.a_mol_top_off_pct  / 100 * a_mol_dil.flow_lb_per_hr
    b_mol_C_flow  = obj.b_mol_C_pans_pct   / 100 * b_mol_dil.flow_lb_per_hr
    b_mol_gr_flow = obj.b_mol_to_grain_pct / 100 * b_mol_dil.flow_lb_per_hr
    b_ftg_flow    = (100 - obj.b_magma_remelt_pct) / 100 * obj._b_magma.flow_lb_per_hr
    c_ftg_flow    = (100 - obj.c_magma_remelt_pct) / 100 * obj._c_magma.flow_lb_per_hr
    syr_gr_flow   = obj.syrup_to_grain_pct / 100 * saf.flow_lb_per_hr
    syr_A_flow    = obj.syrup_to_A_pans_pct / 100 * saf.flow_lb_per_hr

    def mkstream(flow, purity):
        from SugarStream import SugarStream
        return SugarStream(brix=0, purity=purity, flow_lb_per_hr=flow)

    a_mol_B_s  = mkstream(a_mol_B_flow, a_mol_dil.purity)
    a_mol_gr_s = mkstream(a_mol_gr_flow, a_mol_dil.purity)
    a_mol_to_s = mkstream(a_mol_topoff, a_mol_dil.purity)
    b_mol_C_s  = mkstream(b_mol_C_flow, b_mol_dil.purity)
    b_mol_gr_s = mkstream(b_mol_gr_flow, b_mol_dil.purity)
    syr_gr_s   = mkstream(syr_gr_flow, saf.purity)
    syr_A_s    = mkstream(syr_A_flow, saf.purity)

    from SugarStream import SugarStream
    a_dil_water = SugarStream(brix=0, purity=0,
        flow_lb_per_hr=a_mol_dil.flow_lb_per_hr - a_mol.flow_lb_per_hr)
    b_dil_water = SugarStream(brix=0, purity=0,
        flow_lb_per_hr=b_mol_dil.flow_lb_per_hr - b_mol.flow_lb_per_hr)
    b_mag_water = SugarStream(brix=0, purity=0,
        flow_lb_per_hr=obj._b_magma.flow_lb_per_hr - obj.B_centrifugals.sugar_stream.flow_lb_per_hr)
    c_mag_water = SugarStream(brix=0, purity=0,
        flow_lb_per_hr=obj._c_magma.flow_lb_per_hr - obj.C_centrifugals.sugar_stream.flow_lb_per_hr)

    b_ftg_s = mkstream(b_ftg_flow, obj._b_magma.purity)
    c_ftg_s = mkstream(c_ftg_flow, obj._c_magma.purity)

    # ── Title + legend ────────────────────────────────────────────────
    lbl(DW/2, DH - 0.4, 'THREE BOILING DOUBLE MAGMA — Process Flow Diagram', fs=13, bold=True)
    items = [('Syrup', SC), ('A Molasses', MA), ('B Molasses', MB), ('Final Mol', MC),
             ('Magma Footing', MG), ('Remelt', RC), ('Grain Masse', GC),
             ('Sugar Out', SU), ('Water', WA)]
    lx = 0.2
    for txt, col in items:
        ax.plot([lx, lx+0.4], [DH-1.15, DH-1.15], color=col, lw=2.2, clip_on=False)
        lbl(lx+0.52, DH-1.15, txt, ha='left', fs=7, c=col)
        lx += 2.75

    # ══════════════════════════════════════════════════════════════════
    # TOP ROW — staging / splitting tanks
    # ══════════════════════════════════════════════════════════════════

    # Syrup Tank
    _tank_box(lbl, box, X_SYR, Y_TANK, 'Syrup Tank', W=TW, H=TH)
    stub_h(X_SYR - TW/2 - 1.6, Y_TANK, X_SYR - TW/2, 'Syrup from Evaporators', obj.syrup, SC, ha='left')
    stub_v(X_SYR - 0.5, Y_TANK + TH/2 + 1.1, Y_TANK + TH/2, 'B Magma Remelt', obj._b_remelt, RC, side='left')
    stub_v(X_SYR + 0.5, Y_TANK + TH/2 + 1.1, Y_TANK + TH/2, 'C Magma Remelt', obj._c_remelt, RC, side='right')
    stub_h(X_SYR + TW/2, Y_TANK + 0.30, X_SYR + TW/2 + 1.5, '→ A Pans', syr_A_s, SC, ha='left')
    stub_h(X_SYR + TW/2, Y_TANK - 0.30, X_SYR + TW/2 + 1.5, '→ Grain Pans', syr_gr_s, SC, ha='left', name_above=False)

    # A Molasses Tank
    _tank_box(lbl, box, X_AMOL, Y_TANK, 'A Molasses Tank', W=TW, H=TH)
    stub_h(X_AMOL - TW/2 - 1.6, Y_TANK, X_AMOL - TW/2, 'A Molasses', a_mol, MA, ha='left')
    stub_v(X_AMOL, Y_TANK + TH/2 + 1.1, Y_TANK + TH/2, 'Water', a_dil_water, WA, side='right', show_purity=False)
    stub_h(X_AMOL + TW/2, Y_TANK + 0.42, X_AMOL + TW/2 + 1.5, '→ B Pans', a_mol_B_s, MA, ha='left')
    stub_h(X_AMOL + TW/2, Y_TANK - 0.05, X_AMOL + TW/2 + 1.5, '→ Grain Pans', a_mol_gr_s, MA, ha='left', name_above=False)
    stub_h(X_AMOL + TW/2, Y_TANK - 0.55, X_AMOL + TW/2 + 1.7, '→ A Pans (top-off)', a_mol_to_s, MA, ha='left', name_above=False)

    # B Molasses Tank
    _tank_box(lbl, box, X_BMOL, Y_TANK, 'B Molasses Tank', W=TW, H=TH)
    stub_h(X_BMOL - TW/2 - 1.6, Y_TANK, X_BMOL - TW/2, 'B Molasses', b_mol, MB, ha='left')
    stub_v(X_BMOL, Y_TANK + TH/2 + 1.1, Y_TANK + TH/2, 'Water', b_dil_water, WA, side='right', show_purity=False)
    stub_h(X_BMOL + TW/2, Y_TANK + 0.30, X_BMOL + TW/2 + 1.5, '→ C Pans', b_mol_C_s, MB, ha='left')
    stub_h(X_BMOL + TW/2, Y_TANK - 0.30, X_BMOL + TW/2 + 1.5, '→ Grain Pans', b_mol_gr_s, MB, ha='left', name_above=False)

    # ══════════════════════════════════════════════════════════════════
    # MAIN ROW — Pans / Centrifugals / Magma minglers
    # ══════════════════════════════════════════════════════════════════

    _pan_box(lbl, box, X_A, Y_PAN, obj.A_pans, W=PW, H=PH)
    _pan_box(lbl, box, X_B, Y_PAN, obj.B_pans, W=PW, H=PH)
    _pan_box(lbl, box, X_GRAIN, Y_PAN, obj.grain_pans, W=PW, H=PH)
    _pan_box(lbl, box, X_C, Y_PAN, obj.C_pans, W=PW, H=PH)

    P_bot = Y_PAN - PH/2; P_top = Y_PAN + PH/2
    C_bot = Y_CEN - CH/2; C_top = Y_CEN + CH/2

    # A Pans stub-ins
    stub_h(X_A - PW/2 - 1.6, Y_PAN + 0.75, X_A - PW/2, 'Syrup', syr_A_s, SC, ha='left')
    stub_h(X_A - PW/2 - 1.9, Y_PAN, X_A - PW/2, 'B Magma (A Footing)', b_ftg_s, MG, ha='left')
    stub_h(X_A - PW/2 - 1.9, Y_PAN - 0.75, X_A - PW/2, 'A Molasses (top-off)', a_mol_to_s, MA, ha='left', name_above=False)

    # B Pans stub-ins
    stub_h(X_B - PW/2 - 1.6, Y_PAN + 0.4, X_B - PW/2, 'A Molasses', a_mol_B_s, MA, ha='left')
    stub_h(X_B - PW/2 - 1.9, Y_PAN - 0.4, X_B - PW/2, 'C Magma (B Footing)', c_ftg_s, MG, ha='left', name_above=False)

    # Grain Pans stub-ins
    stub_h(X_GRAIN - PW/2 - 1.6, Y_PAN + 0.75, X_GRAIN - PW/2, 'Syrup', syr_gr_s, SC, ha='left')
    stub_h(X_GRAIN - PW/2 - 1.6, Y_PAN, X_GRAIN - PW/2, 'A Molasses', a_mol_gr_s, MA, ha='left')
    stub_h(X_GRAIN - PW/2 - 1.6, Y_PAN - 0.75, X_GRAIN - PW/2, 'B Molasses', b_mol_gr_s, MB, ha='left', name_above=False)

    # Grain -> C pan (real connected forward arrow)
    arr(X_GRAIN + PW/2, Y_PAN + 0.35, X_C - PW/2, Y_PAN + 0.35, GC, lw=1.8)
    lbl((X_GRAIN + PW/2 + X_C - PW/2)/2, Y_PAN + 0.35 + 0.30, 'Grain Masse', bold=True, fs=6.8, c=GC)
    lbl((X_GRAIN + PW/2 + X_C - PW/2)/2, Y_PAN + 0.35 - 0.30,
        f'{obj.grain_pans.massecuite_flow_lb_hr:,.0f} lb/hr   Pu {obj.grain_pans.masse_purity:.1f}', fs=6.3, c=GC)

    # C Pans stub-in: B Molasses
    stub_h(X_C - PW/2 - 1.6, Y_PAN - 0.35, X_C - PW/2, 'B Molasses', b_mol_C_s, MB, ha='left', name_above=False)

    # Pan -> Centrifugal (connected, same column)
    for X in (X_A, X_B, X_C):
        arr(X, P_bot, X, C_top, '#555', lw=1.8)
    # grain pans has no centrifugal

    _cen_box(lbl, box, X_A, Y_CEN, obj.A_centrifugals, W=CW, H=CH)
    _cen_box(lbl, box, X_B, Y_CEN, obj.B_centrifugals, W=CW, H=CH)
    _cen_box(lbl, box, X_C, Y_CEN, obj.C_centrifugals, W=CW, H=CH)

    # Wash water stub-ins (centrifugals)
    from SugarStream import SugarStream as _SS
    a_ww = _SS(brix=0, purity=0, flow_lb_per_hr=obj.A_centrifugals.wash_water_lb_hr)
    b_ww = _SS(brix=0, purity=0, flow_lb_per_hr=obj.B_centrifugals.wash_water_lb_hr)
    c_ww = _SS(brix=0, purity=0, flow_lb_per_hr=obj.C_centrifugals.wash_water_lb_hr)
    stub_h(X_A + CW/2 + 1.5, Y_CEN, X_A + CW/2, 'Wash Water', a_ww, WA, ha='right', show_purity=False)
    stub_h(X_B + CW/2 + 1.5, Y_CEN, X_B + CW/2, 'Wash Water', b_ww, WA, ha='right', show_purity=False)
    stub_h(X_C + CW/2 + 1.5, Y_CEN, X_C + CW/2, 'Wash Water', c_ww, WA, ha='right', show_purity=False)

    # A sugar out (final product)
    arr(X_A, C_bot, X_A, C_bot - 0.9, SU, lw=2.0)
    lbl(X_A + 0.7, C_bot - 0.45, 'A SUGAR', ha='left', bold=True, fs=8, c=SU)
    lbl(X_A + 0.7, C_bot - 0.80,
        f'{obj.A_centrifugals.sugar_wet_lb_hr:,.0f} lb/hr  Pu {obj.A_centrifugals.sugar_purity:.1f}',
        ha='left', fs=6.3, c=SU)

    # A molasses out (stub, matches A Molasses Tank stub-in)
    stub_h(X_A + CW/2, Y_CEN + 0.3, X_A + CW/2 + 1.7, 'A Molasses', a_mol, MA, ha='left')

    # B/C: centrifugal -> magma mingler (connected)
    arr(X_B, C_bot, X_B, Y_MAG + MH/2, '#555', lw=1.8)
    arr(X_C, C_bot, X_C, Y_MAG + MH/2, '#555', lw=1.8)

    _mag_box(lbl, box, X_B, Y_MAG, 'B Magma', obj._b_magma, W=MW, H=MH)
    _mag_box(lbl, box, X_C, Y_MAG, 'C Magma', obj._c_magma, W=MW, H=MH)

    stub_h(X_B - MW/2 - 1.5, Y_MAG, X_B - MW/2, 'Water', b_mag_water, WA, ha='right', show_purity=False)
    stub_h(X_C - MW/2 - 1.5, Y_MAG, X_C - MW/2, 'Water', c_mag_water, WA, ha='right', show_purity=False)

    stub_h(X_B + MW/2, Y_MAG + 0.30, X_B + MW/2 + 1.7, '→ A Pans (footing)', b_ftg_s, MG, ha='left')
    stub_h(X_B + MW/2, Y_MAG - 0.30, X_B + MW/2 + 1.5, '→ Remelt', obj._b_magma_to_rmlt, RC, ha='left', name_above=False)
    stub_h(X_C + MW/2, Y_MAG + 0.30, X_C + MW/2 + 1.7, '→ B Pans (footing)', c_ftg_s, MG, ha='left')
    stub_h(X_C + MW/2, Y_MAG - 0.30, X_C + MW/2 + 1.5, '→ Remelt', obj._c_magma_to_rmlt, RC, ha='left', name_above=False)

    # B molasses out (stub, matches B Molasses Tank stub-in)
    stub_h(X_B + CW/2, Y_CEN + 0.3, X_B + CW/2 + 1.7, 'B Molasses', b_mol, MB, ha='left')

    # Final molasses out
    arr(X_C + CW/2, Y_CEN, DW - 0.2, Y_CEN, MC, lw=2.2)
    lbl(DW - 0.25, Y_CEN + 0.55, 'FINAL MOLASSES', ha='right', bold=True, fs=9, c=MC)
    fm = obj.C_centrifugals.molasses_stream
    lbl(DW - 0.25, Y_CEN + 0.15, f'{fm.flow_lb_per_hr:,.0f} lb/hr   Pu {fm.purity:.1f}', ha='right', fs=7, c=MC)

    # ── Footer ──────────────────────────────────────────────────────────
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


if __name__ == '__main__':
    import sys
    sys.path.insert(0, r'c:\Users\ceaves\material_energy_balance_OOP\Material_Energy_Balance_OOP_python')
    from ThreeBoilingDoubleMagma import ThreeBoilingDoubleMagma
    from Pan import Pan
    from Centrifugal import Centrifugal
    from SugarStream import SugarStream

    pf = ThreeBoilingDoubleMagma(
        syrup=SugarStream(brix=60, purity=80, flow_lb_per_hr=162_744, temp_deg_F=140),
        A_pans=Pan(feed_streams=None, heating_surface_ft2=22500, inches_vacuum=23.5, supersaturation=1.2, head_ft=2, masse_brix=92, ml_purity=65, calandria_pressure_psia=21.696, heat_loss_factor=0.02, name='A Pans'),
        B_pans=Pan(feed_streams=None, heating_surface_ft2=7500, inches_vacuum=25, supersaturation=1.2, head_ft=2, masse_brix=94, ml_purity=48, calandria_pressure_psia=29.696, heat_loss_factor=0.05, name='B Pans'),
        grain_pans=Pan(feed_streams=None, heating_surface_ft2=3000, inches_vacuum=25.5, supersaturation=1.2, head_ft=2, masse_brix=88, ml_purity=39, calandria_pressure_psia=29.696, heat_loss_factor=0.05, name='grain Pans'),
        C_pans=Pan(feed_streams=None, heating_surface_ft2=12000, inches_vacuum=26.5, supersaturation=1.2, head_ft=2, masse_brix=95.5, ml_purity=33, calandria_pressure_psia=21.696, heat_loss_factor=0.05, name='C Pans'),
        A_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82, purity_rise=2, sugar_moisture=0.2, sugar_purity=99.7, sugar_temp=150, molasses_temp=145, name='A Centrifugals'),
        B_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82, purity_rise=2, sugar_moisture=5, sugar_purity=92, sugar_temp=150, molasses_temp=145, name='B Centrifugals'),
        C_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82, purity_rise=4, sugar_moisture=5, sugar_purity=82, sugar_temp=150, molasses_temp=145, name='C Centrifugals'),
        b_magma_remelt_pct=20, c_magma_remelt_pct=20, a_mol_to_grain_pct=3, b_mol_to_grain_pct=10,
        syrup_to_grain_pct=1, a_mol_top_off_pct=15,
    )
    plot_three_boiling(pf, show=False, save_path=r'C:\Users\ceaves\AppData\Local\Temp\claude\c--Users-ceaves-material-energy-balance-OOP-Material-Energy-Balance-OOP-python\29a8f6af-c66b-4790-ad54-0abdd960b2ec\scratchpad\pfd_test.png')
    print('saved')
