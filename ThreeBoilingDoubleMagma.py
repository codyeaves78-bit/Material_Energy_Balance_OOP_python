from Pan import Pan
from Centrifugal import Centrifugal
from Crystallizer_and_Reheater import Crystallizer, Reheater
from SugarStream import SugarStream

from time import time

def make_magma(sugar_stream: SugarStream, mingler_brix: float) -> SugarStream:
    magma = SugarStream.copy(sugar_stream)
    solids = magma.solids_flow
    magma.brix = mingler_brix
    magma.flow_lb_per_hr = solids / magma.brix * 100
    return magma # helper function

def make_remelt(magma=SugarStream(), remelt_brix=65):
    remelt = SugarStream.copy(magma)
    brix_flow = magma.solids_flow
    new_flow = brix_flow * 100 / remelt_brix
    new_brix = brix_flow / new_flow * 100
    remelt.flow_lb_per_hr = new_flow
    remelt.brix = new_brix
    return remelt


def dilute_molasses(mol: SugarStream, diluted_brix: float) -> SugarStream:
    """Dilute molasses to target brix by adding water. Solids are conserved."""
    diluted = SugarStream.copy(mol)
    diluted.brix = diluted_brix
    diluted.flow_lb_per_hr = mol.solids_flow / (diluted_brix / 100)
    return diluted

class ThreeBoilingDoubleMagma:
    """An object to do the Three Boiling Double Magma Balance
    When inputting the Pan and Centrifugal Object, user does not need to define inlet streams"""
    def __init__(
            self,
            syrup: SugarStream,
            A_pans: Pan,
            B_pans: Pan,
            C_pans: Pan,
            grain_pans: Pan,
            A_centrifugals: Centrifugal,
            B_centrifugals: Centrifugal,
            C_centrifugals: Centrifugal,
            C_crystallizers: Crystallizer = None,
            C_reheaters: Reheater = None,
            c_magma_remelt_pct: float = 20,
            b_magma_remelt_pct: float = 20,
            syrup_to_grain_pct: float = 5,
            a_mol_to_grain_pct: float = 5,
            b_mol_to_grain_pct: float = 10,
            a_mol_top_off_pct: float = 30,
            a_mol_dilution_brix: float = 70,
            b_mol_dilution_brix: float = 70,
            ):

        self.syrup = syrup
        
        # Store Pan/Centrifugal configs as templates; solved instances assigned in _solve()
        self._A_pans_cfg = A_pans
        self._B_pans_cfg = B_pans
        self._C_pans_cfg = C_pans
        self._grain_pans_cfg = grain_pans
        self._A_cen_cfg = A_centrifugals
        self._B_cen_cfg = B_centrifugals
        self._C_cen_cfg = C_centrifugals
        # Default: cool to 120°F / reheat to 130°F with no exhaustion (ml purity carried)
        self._C_crys_cfg = (C_crystallizers if C_crystallizers is not None
                            else Crystallizer(massecuite_in=None, massecuite_flow_lb_hr=0,
                                              name='C Crystallizers'))
        self._C_reheat_cfg = (C_reheaters if C_reheaters is not None
                              else Reheater(massecuite_in=None, massecuite_flow_lb_hr=0,
                                            name='C Reheaters'))

        self.c_magma_remelt_pct = c_magma_remelt_pct
        self.b_magma_remelt_pct = b_magma_remelt_pct
        self.syrup_to_grain_pct = syrup_to_grain_pct
        self.a_mol_to_grain_pct = a_mol_to_grain_pct
        self.b_mol_to_grain_pct = b_mol_to_grain_pct
        self.a_mol_top_off_pct = a_mol_top_off_pct
        self.a_mol_B_pans_pct = 100.0 - a_mol_top_off_pct - a_mol_to_grain_pct
        self.b_mol_C_pans_pct = 100.0 - b_mol_to_grain_pct
        self.a_mol_dilution_brix = a_mol_dilution_brix
        self.b_mol_dilution_brix = b_mol_dilution_brix
        self.syrup_to_A_pans_pct = 100.0 - syrup_to_grain_pct

        self._solve()

    def _rebuild_pan(self, config: Pan, feed_streams: list) -> Pan:
        return Pan(
            feed_streams=feed_streams,
            heating_surface_ft2=config.heating_surface_ft2,
            inches_vacuum=config.inches_vacuum,
            supersaturation=config.supersaturation,
            head_ft=config.head_ft,
            masse_brix=config.masse_brix,
            ml_purity=config.ml_purity,
            calandria_pressure_psia=config.calandria_pressure_psia,
            heat_loss_factor=config.heat_loss_factor,
            name=config.name,
        )

    def _rebuild_centrifugal(self, config: Centrifugal, massecuite, massecuite_flow_lb_hr: float) -> Centrifugal:
        return Centrifugal(
            massecuite=massecuite,
            massecuite_flow_lb_hr=massecuite_flow_lb_hr,
            target_molasses_brix=config.target_molasses_brix,
            purity_rise=config.purity_rise,
            sugar_purity=config.sugar_purity,
            sugar_moisture=config.sugar_moisture,
            name=config.name,
            sugar_temp=config.sugar_temp,
            molasses_temp=config.molasses_temp,
        )

    def _rebuild_crystallizer(self, config: Crystallizer, massecuite_in, massecuite_flow_lb_hr: float) -> Crystallizer:
        return Crystallizer(
            massecuite_in=massecuite_in,
            massecuite_flow_lb_hr=massecuite_flow_lb_hr,
            masse_temp_out_deg_F=config.masse_temp_out_deg_F,
            ml_purity_out=config.ml_purity_out,
            water_temp_in_deg_F=config.water_temp_in_deg_F,
            water_temp_out_deg_F=config.water_temp_out_deg_F,
            name=config.name,
        )

    def _rebuild_reheater(self, config: Reheater, massecuite_in, massecuite_flow_lb_hr: float) -> Reheater:
        return Reheater(
            massecuite_in=massecuite_in,
            massecuite_flow_lb_hr=massecuite_flow_lb_hr,
            masse_temp_out_deg_F=config.masse_temp_out_deg_F,
            ml_purity_out=config.ml_purity_out,
            water_temp_in_deg_F=config.water_temp_in_deg_F,
            water_temp_out_deg_F=config.water_temp_out_deg_F,
            name=config.name,
        )

    def _solve(self, iterations: int = 20):
        # Dummy initial magma footings — zero flow so they don't distort the first A/B pan solve.
        # Both are overwritten each iteration: c_magma_B_pans from C centrifugals sugar stream,
        # b_magma_A_pans from B centrifugals sugar stream (via make_magma). Brix/purity/temp
        # are placeholders only; the loop replaces them before they matter.
        c_magma_B_pans = SugarStream(brix=92, purity=85, flow_lb_per_hr=0, temp_deg_F=130)
        b_magma_A_pans = SugarStream(brix=92, purity=92, flow_lb_per_hr=0, temp_deg_F=130)

        syrup_as_fed = SugarStream.copy(self.syrup)

        syrup_to_A_pans = SugarStream.copy(self.syrup)
        syrup_to_A_pans.flow_lb_per_hr = self.syrup_to_A_pans_pct / 100 * self.syrup.flow_lb_per_hr

        # Dummy top-off A molasses — zero flow for the first A pan solve.
        # Overwritten each iteration from A centrifugals molasses_stream.
        # NOTE: molasses_stream.temp_deg_F is fixed to _A_cen_cfg.molasses_temp (not computed
        # from the centrifugal thermodynamics), so temperature is constant across iterations.
        top_off_a_mol = SugarStream(brix=70, purity=70, flow_lb_per_hr=0, temp_deg_F=140)

        for _ in range(iterations):
            self.A_pans = self._rebuild_pan(
                self._A_pans_cfg, [syrup_to_A_pans, b_magma_A_pans, top_off_a_mol]
            )
            self.A_centrifugals = self._rebuild_centrifugal(
                self._A_cen_cfg, self.A_pans.massecuite, self.A_pans.massecuite_flow_lb_hr
            )

            a_mol_diluted = dilute_molasses(self.A_centrifugals.molasses_stream, self.a_mol_dilution_brix)

            top_off_a_mol = SugarStream.copy(a_mol_diluted)
            top_off_a_mol.flow_lb_per_hr = self.a_mol_top_off_pct / 100 * top_off_a_mol.flow_lb_per_hr

            a_mol_B_pans = SugarStream.copy(a_mol_diluted)
            a_mol_B_pans.flow_lb_per_hr = self.a_mol_B_pans_pct / 100 * a_mol_B_pans.flow_lb_per_hr

            self.B_pans = self._rebuild_pan(
                self._B_pans_cfg, [c_magma_B_pans, a_mol_B_pans]
            )
            self.B_centrifugals = self._rebuild_centrifugal(
                self._B_cen_cfg, self.B_pans.massecuite, self.B_pans.massecuite_flow_lb_hr
            )

            b_mol_diluted = dilute_molasses(self.B_centrifugals.molasses_stream, self.b_mol_dilution_brix)

            b_mol_grain = SugarStream.copy(b_mol_diluted)
            b_mol_grain.flow_lb_per_hr = self.b_mol_to_grain_pct / 100 * b_mol_grain.flow_lb_per_hr

            a_mol_grain = SugarStream.copy(a_mol_diluted)
            a_mol_grain.flow_lb_per_hr = self.a_mol_to_grain_pct / 100 * a_mol_grain.flow_lb_per_hr

            syrup_to_grain = SugarStream.copy(syrup_as_fed)
            syrup_to_grain.flow_lb_per_hr = self.syrup_to_grain_pct / 100 * syrup_as_fed.flow_lb_per_hr

            self.grain_pans = self._rebuild_pan(
                self._grain_pans_cfg, [syrup_to_grain, a_mol_grain, b_mol_grain]
            )

            grain_massecuite = SugarStream(
                brix=self.grain_pans.masse_brix,
                purity=self.grain_pans.masse_purity,
                flow_lb_per_hr=self.grain_pans.massecuite_flow_lb_hr,
                temp_deg_F=self.grain_pans.massecuite.massecuite_temp,
                pressure_psia=14.7,
                level_ft=0,
            )

            b_mol_C_pans = SugarStream.copy(b_mol_diluted)
            b_mol_C_pans.flow_lb_per_hr = self.b_mol_C_pans_pct / 100 * b_mol_C_pans.flow_lb_per_hr

            self.C_pans = self._rebuild_pan(
                self._C_pans_cfg, [grain_massecuite, b_mol_C_pans]
            )

            # C massecuite: cooling crystallizer → reheater → centrifugals.
            # Mass flow is conserved (non-contact water); the crystallizer's ml purity
            # drop carries into the centrifugal and lowers final molasses purity.
            self.C_crystallizers = self._rebuild_crystallizer(
                self._C_crys_cfg, self.C_pans.massecuite, self.C_pans.massecuite_flow_lb_hr
            )
            self.C_reheaters = self._rebuild_reheater(
                self._C_reheat_cfg, self.C_crystallizers.massecuite_out,
                self.C_pans.massecuite_flow_lb_hr
            )
            self.C_centrifugals = self._rebuild_centrifugal(
                self._C_cen_cfg, self.C_reheaters.massecuite_out, self.C_pans.massecuite_flow_lb_hr
            )

            b_magma = make_magma(self.B_centrifugals.sugar_stream, mingler_brix=92)
            c_magma = make_magma(self.C_centrifugals.sugar_stream, mingler_brix=92)

            b_magma_A_pans = SugarStream.copy(b_magma)
            b_magma_A_pans.flow_lb_per_hr = (100 - self.b_magma_remelt_pct) / 100 * b_magma_A_pans.flow_lb_per_hr

            c_magma_B_pans = SugarStream.copy(c_magma)
            c_magma_B_pans.flow_lb_per_hr = (100 - self.c_magma_remelt_pct) / 100 * c_magma_B_pans.flow_lb_per_hr

            b_magma_to_rmlt = SugarStream.copy(b_magma)
            b_magma_to_rmlt.flow_lb_per_hr = self.b_magma_remelt_pct / 100 * b_magma_to_rmlt.flow_lb_per_hr
            b_remelt = make_remelt(b_magma_to_rmlt, remelt_brix=65)

            c_magma_to_rmlt = SugarStream.copy(c_magma)
            c_magma_to_rmlt.flow_lb_per_hr = self.c_magma_remelt_pct / 100 * c_magma_to_rmlt.flow_lb_per_hr
            c_remelt = make_remelt(c_magma_to_rmlt, remelt_brix=65)

            total_flows = self.syrup.flow_lb_per_hr + c_remelt.flow_lb_per_hr + b_remelt.flow_lb_per_hr
            total_solids = self.syrup.solids_flow + c_remelt.solids_flow + b_remelt.solids_flow
            total_pols = self.syrup.pol_flow + b_remelt.pol_flow + c_remelt.pol_flow

            syrup_as_fed = SugarStream.copy(self.syrup)
            syrup_as_fed.flow_lb_per_hr = total_flows
            syrup_as_fed.brix = total_solids / total_flows * 100
            syrup_as_fed.purity = total_pols / total_solids * 100

            syrup_to_A_pans = SugarStream.copy(syrup_as_fed)
            syrup_to_A_pans.flow_lb_per_hr = self.syrup_to_A_pans_pct / 100 * syrup_to_A_pans.flow_lb_per_hr

        self.syrup_as_fed = syrup_as_fed

        # Save final-iteration magma/remelt/dilution streams for water accounting
        self._b_magma          = b_magma
        self._c_magma          = c_magma
        self._b_magma_to_rmlt  = b_magma_to_rmlt
        self._c_magma_to_rmlt  = c_magma_to_rmlt
        self._b_remelt         = b_remelt
        self._c_remelt         = c_remelt
        self._a_mol_diluted    = a_mol_diluted
        self._b_mol_diluted    = b_mol_diluted

    @property
    def total_water(self) -> SugarStream:
        """All fresh water added to the pan floor (lb/hr): centrifugal wash + magma minglers + remelts."""
        cen_wash     = (self.A_centrifugals.wash_water_lb_hr
                      + self.B_centrifugals.wash_water_lb_hr
                      + self.C_centrifugals.wash_water_lb_hr)
        b_mingler    = self._b_magma.flow_lb_per_hr    - self.B_centrifugals.sugar_stream.flow_lb_per_hr
        c_mingler    = self._c_magma.flow_lb_per_hr    - self.C_centrifugals.sugar_stream.flow_lb_per_hr
        b_rmlt_water = self._b_remelt.flow_lb_per_hr   - self._b_magma_to_rmlt.flow_lb_per_hr
        c_rmlt_water = self._c_remelt.flow_lb_per_hr   - self._c_magma_to_rmlt.flow_lb_per_hr
        a_dil_water  = self._a_mol_diluted.flow_lb_per_hr - self.A_centrifugals.molasses_stream.flow_lb_per_hr
        b_dil_water  = self._b_mol_diluted.flow_lb_per_hr - self.B_centrifugals.molasses_stream.flow_lb_per_hr
        total_lb_hr  = (cen_wash + b_mingler + c_mingler + b_rmlt_water + c_rmlt_water
                        + a_dil_water + b_dil_water)
        return SugarStream(brix=0, purity=0, flow_lb_per_hr=total_lb_hr)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def generate_pfd(self, show=True, save_path=None):
        """Generate a process flow diagram. Returns the matplotlib Figure."""
        from pan_floor_diagram import plot_three_boiling
        return plot_three_boiling(self, show=show, save_path=save_path)

    def neat_display(self):
        W = 115
        HEAVY = "=" * W
        LIGHT = "-" * W

        LBL = 32   # label column width
        NUM = 13   # numeric column width
        VOL = 10   # ft³/hr column width

        def _row(label, flow, solids, pol, water, brix=None, purity=None, vol_ft3_hr=None):
            b = f"{brix:6.1f}" if brix is not None else "     -"
            p = f"{purity:6.1f}" if purity is not None else "     -"
            v = f"{vol_ft3_hr:{VOL},.0f}" if vol_ft3_hr is not None else " " * (VOL - 1) + "-"
            return (f"  {label:<{LBL}} {flow:{NUM},.0f} {solids:{NUM},.0f}"
                    f" {pol:{NUM},.0f} {water:{NUM},.0f} {b} {p} {v}")

        def _hdr():
            return (f"  {'Stream':<{LBL}} {'Flow (lb/hr)':{NUM}} {'Solids (lb/hr)':{NUM}}"
                    f" {'Pol (lb/hr)':{NUM}} {'Water (lb/hr)':{NUM}} {'Brix%':>6} {'Pur%':>6} {'ft3/hr':>{VOL}}")

        def _stream(label, s):
            sol = s.solids_flow
            return _row(label, s.flow_lb_per_hr, sol, s.pol_flow,
                        s.flow_lb_per_hr - sol, s.brix, s.purity, vol_ft3_hr=s.cu_ft_hr)

        def _section(title):
            return f"\n{LIGHT}\n  {title}\n{LIGHT}"

        def _pan_station(pan):
            lines = []
            lines.append("  ENTERING")
            for i, f in enumerate(pan.feed_streams, 1):
                sol = f.solids_flow
                lines.append(_row(f"    Feed {i}  (Bx={f.brix:.1f} Pu={f.purity:.1f})",
                                  f.flow_lb_per_hr, sol, f.pol_flow,
                                  f.flow_lb_per_hr - sol, f.brix, f.purity, vol_ft3_hr=f.cu_ft_hr))
            ff = pan.feed_flow_lb_hr
            fs = pan.feed_solids_lb_hr
            fp = sum(f.pol_flow for f in pan.feed_streams)
            lines.append(LIGHT)
            lines.append(_row("  Total Feed In", ff, fs, fp, ff - fs))
            lines.append("")
            lines.append("  LEAVING")
            masse_sol = fs          # solids conserved through evaporation
            masse_pol = fp          # pol conserved through evaporation
            masse_water = pan.massecuite_flow_lb_hr - masse_sol
            masse_vol = pan.massecuite_flow_lb_hr / pan.massecuite.density
            lines.append(_row("  Massecuite Out", pan.massecuite_flow_lb_hr,
                               masse_sol, masse_pol, masse_water,
                               pan.masse_brix, pan.masse_purity, vol_ft3_hr=masse_vol))
            lines.append(_row("  Evaporated Water", pan.water_evaporated_lb_hr,
                               0, 0, pan.water_evaporated_lb_hr))
            lines.append(LIGHT)
            net = ff - pan.massecuite_flow_lb_hr - pan.water_evaporated_lb_hr
            lines.append(f"  {'Net (In - Out):':<{LBL}} {net:{NUM},.0f} lb/hr")
            return lines

        def _cen_station(cen):
            lines = []
            ms  = cen.massecuite_solids_lb_hr
            mw  = cen.massecuite_flow_lb_hr - ms
            mp  = cen.pol_in_lb_hr
            ww  = cen.wash_water_lb_hr
            s_sol  = cen.crystals_to_sugar_lb_hr
            s_wat  = cen.sugar_wet_lb_hr - s_sol
            m_sol  = cen.molasses_solids_lb_hr
            m_wat  = cen.molasses_flow_lb_hr - m_sol
            masse_vol = cen.massecuite_flow_lb_hr / cen.massecuite.density
            lines.append("  ENTERING")
            lines.append(_row("    Massecuite", cen.massecuite_flow_lb_hr, ms, mp, mw,
                               cen.massecuite.masse_brix, cen.massecuite.masse_purity,
                               vol_ft3_hr=masse_vol))
            lines.append(_row("    Wash Water", ww, 0, 0, ww))
            lines.append(LIGHT)
            lines.append(f"  {'Total In':<{LBL}} {cen.massecuite_flow_lb_hr + ww:{NUM},.0f}"
                         f" {ms:{NUM},.0f} {mp:{NUM},.0f} {mw + ww:{NUM},.0f}")
            lines.append("")
            lines.append("  LEAVING")
            lines.append(_row("    Sugar Out", cen.sugar_wet_lb_hr,
                               s_sol, cen.sugar_pol_lb_hr, s_wat,
                               cen.sugar_brix, cen.sugar_purity,
                               vol_ft3_hr=cen.sugar_stream.cu_ft_hr))
            lines.append(_row("    Molasses Out", cen.molasses_flow_lb_hr,
                               m_sol, cen.pol_to_molasses_lb_hr, m_wat,
                               cen.target_molasses_brix, cen.molasses_purity,
                               vol_ft3_hr=cen.molasses_stream.cu_ft_hr))
            lines.append(LIGHT)
            total_out = cen.sugar_wet_lb_hr + cen.molasses_flow_lb_hr
            net = (cen.massecuite_flow_lb_hr + ww) - total_out
            lines.append(f"  {'Net (In - Out):':<{LBL}} {net:{NUM},.0f} lb/hr")
            return lines

        def _dil_station(undiluted, diluted, label):
            lines = []
            water_added = diluted.flow_lb_per_hr - undiluted.flow_lb_per_hr
            lines.append("  ENTERING")
            lines.append(_stream(f"    {label} (undiluted)", undiluted))
            lines.append(_row("    Dilution Water", water_added, 0, 0, water_added))
            lines.append(LIGHT)
            lines.append(_row("  Total In", diluted.flow_lb_per_hr, undiluted.solids_flow,
                               undiluted.pol_flow, diluted.flow_lb_per_hr - undiluted.solids_flow))
            lines.append("")
            lines.append("  LEAVING")
            lines.append(_stream(f"    {label} (diluted)", diluted))
            lines.append(LIGHT)
            net = diluted.flow_lb_per_hr - (undiluted.flow_lb_per_hr + water_added)
            lines.append(f"  {'Net (In - Out):':<{LBL}} {net:{NUM},.2f} lb/hr")
            return lines

        def _heatx_station(unit, water_label):
            """Crystallizer/reheater station — non-contact water, mass conserved."""
            lines = []
            m_in, m_out = unit.massecuite_in, unit.massecuite_out
            flow = unit.massecuite_flow_lb_hr
            sol  = flow * m_in.masse_brix / 100
            pol  = flow * m_in.masse_purity * m_in.masse_brix / 10000
            lines.append("  ENTERING")
            lines.append(_row(f"    Massecuite In   (T={unit.masse_temp_in_deg_F:5.1f}F)",
                               flow, sol, pol, flow - sol,
                               m_in.masse_brix, m_in.masse_purity, vol_ft3_hr=flow / m_in.density))
            lines.append("")
            lines.append("  LEAVING")
            lines.append(_row(f"    Massecuite Out  (T={unit.masse_temp_out_deg_F:5.1f}F)",
                               flow, sol, pol, flow - sol,
                               m_out.masse_brix, m_out.masse_purity, vol_ft3_hr=flow / m_out.density))
            lines.append(LIGHT)
            lines.append(f"  {'ML purity in -> out:':<{LBL}} {m_in.ml_purity:6.1f} -> {m_out.ml_purity:6.1f} %"
                         f"     crystal content: {m_in.crystal_content:5.1f} -> {m_out.crystal_content:5.1f} %")
            lines.append(f"  {'Duty:':<{LBL}} {unit.duty_btu_hr:{NUM},.0f} BTU/hr")
            lines.append(f"  {water_label + ':':<{LBL}} {unit.water_lb_hr:{NUM},.0f} lb/hr"
                         f" ({unit.water_gpm:,.0f} gpm), {unit.water_temp_in_deg_F:.0f} -> "
                         f"{unit.water_temp_out_deg_F:.0f} F")
            return lines

        # ── Totals needed for Overall section ────────────────────────────
        total_evap = (self.A_pans.water_evaporated_lb_hr + self.B_pans.water_evaporated_lb_hr
                      + self.C_pans.water_evaporated_lb_hr + self.grain_pans.water_evaporated_lb_hr)
        a_sugar  = self.A_centrifugals.sugar_stream
        c_mol    = self.C_centrifugals.molasses_stream
        pol_extr = a_sugar.pol_flow / self.syrup.pol_flow * 100

        out = []
        out.append(HEAVY)
        out.append(f"{'THREE BOILING DOUBLE MAGMA - COMPLETE FLOOR BALANCE':^{W}}")
        out.append(HEAVY)

        # ── Overall ──────────────────────────────────────────────────────
        out.append(_section("OVERALL FLOOR BALANCE"))
        out.append(f"  (Feed = Evaporator syrup + Wash Water; Products = A sugar + C final molasses)")
        out.append("")
        out.append(_hdr())
        out.append("")
        out.append("  ENTERING")
        out.append(_stream("  Syrup From Evaporators", self.syrup))
        out.append(_stream("  Wash and Dilution Water", self.total_water))
        out.append("")
        out.append("  LEAVING")
        out.append(_stream("  A Product Sugar", a_sugar))
        out.append(_stream("  C Final Molasses", c_mol))
        out.append(_row("  Evaporated (all pans)", total_evap, 0, 0, total_evap))
        out.append("")
        tw = self.total_water
        in_flow    = self.syrup.flow_lb_per_hr + tw.flow_lb_per_hr
        in_solids  = self.syrup.solids_flow
        in_pol     = self.syrup.pol_flow
        in_water   = (self.syrup.flow_lb_per_hr - self.syrup.solids_flow) + tw.flow_lb_per_hr
        out_flow   = a_sugar.flow_lb_per_hr + c_mol.flow_lb_per_hr + total_evap
        out_solids = a_sugar.solids_flow    + c_mol.solids_flow
        out_pol    = a_sugar.pol_flow       + c_mol.pol_flow
        out_water  = ((a_sugar.flow_lb_per_hr - a_sugar.solids_flow)
                    + (c_mol.flow_lb_per_hr   - c_mol.solids_flow)
                    + total_evap)
        out.append(LIGHT)
        out.append(_row("  Total Entering", in_flow,  in_solids,  in_pol,  in_water))
        out.append(_row("  Total Leaving",  out_flow, out_solids, out_pol, out_water))
        out.append(LIGHT)
        out.append(_row("  Net (In - Out)", in_flow - out_flow, in_solids - out_solids,
                                            in_pol  - out_pol,  in_water  - out_water))
        out.append(f"  {'Pol% Recovered in Raw Sugar (A sugar / feed):':<{LBL+NUM}} {pol_extr:6.2f} %")
        out.append("")

        # ── A Pans ────────────────────────────────────────────────────────
        out.append(_section(f"A PANS  [{self.A_pans.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_pan_station(self.A_pans))

        # ── A Centrifugals ─────────────────────────────────────────────────
        out.append(_section(f"A CENTRIFUGALS  [{self.A_centrifugals.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_cen_station(self.A_centrifugals))

        # ── A Molasses Dilution ──────────────────────────────────────────
        out.append(_section(f"A MOLASSES DILUTION  (target {self.a_mol_dilution_brix:.1f} Bx)"))
        out.append(_hdr())
        out.append("")
        out.extend(_dil_station(self.A_centrifugals.molasses_stream, self._a_mol_diluted, "A Molasses"))

        # ── B Pans ────────────────────────────────────────────────────────
        out.append(_section(f"B PANS  [{self.B_pans.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_pan_station(self.B_pans))

        # ── B Centrifugals ─────────────────────────────────────────────────
        out.append(_section(f"B CENTRIFUGALS  [{self.B_centrifugals.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_cen_station(self.B_centrifugals))

        # ── B Molasses Dilution ──────────────────────────────────────────
        out.append(_section(f"B MOLASSES DILUTION  (target {self.b_mol_dilution_brix:.1f} Bx)"))
        out.append(_hdr())
        out.append("")
        out.extend(_dil_station(self.B_centrifugals.molasses_stream, self._b_mol_diluted, "B Molasses"))

        # ── Grain Pans ────────────────────────────────────────────────────
        out.append(_section(f"GRAIN PANS  [{self.grain_pans.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_pan_station(self.grain_pans))

        # ── C Pans ────────────────────────────────────────────────────────
        out.append(_section(f"C PANS  [{self.C_pans.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_pan_station(self.C_pans))

        # ── C Crystallizers ──────────────────────────────────────────────
        out.append(_section(f"C CRYSTALLIZERS  [{self.C_crystallizers.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_heatx_station(self.C_crystallizers, "Cooling Water"))

        # ── C Reheaters ──────────────────────────────────────────────────
        out.append(_section(f"C REHEATERS  [{self.C_reheaters.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_heatx_station(self.C_reheaters, "Hot Water"))

        # ── C Centrifugals ─────────────────────────────────────────────────
        out.append(_section(f"C CENTRIFUGALS  [{self.C_centrifugals.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_cen_station(self.C_centrifugals))
        out.append("")
        out.append(HEAVY)

        print("\n".join(out))


if __name__ == "__main__":
    pan_floor = ThreeBoilingDoubleMagma(
        syrup=SugarStream(brix=60, purity=80, flow_lb_per_hr=162_744, temp_deg_F=140),
        A_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=22500,
            inches_vacuum=23.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=92,
            ml_purity=65,
            calandria_pressure_psia=21.696,   # V1 (7 psig)
            heat_loss_factor=0.02, name='A Pans'),
        B_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=7500,
            inches_vacuum=25,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=94,
            ml_purity=48,
            calandria_pressure_psia=29.696,   # Exhaust (15 psig)
            heat_loss_factor=0.05, name='B Pans'),
        grain_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=3000,
            inches_vacuum=25.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=88,
            ml_purity=39,
            calandria_pressure_psia=29.696,   # Exhaust (15 psig)
            heat_loss_factor=0.05, name='grain Pans'),
        C_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=12000,
            inches_vacuum=26.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=95.5,
            ml_purity=33,
            calandria_pressure_psia=21.696,   # V1 (7 psig)
            heat_loss_factor=0.05, name='C Pans'),
        A_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82, purity_rise=2, 
                                   sugar_moisture=0.2, sugar_purity=99.7, sugar_temp=150, molasses_temp=145, name="A Centrifugals"),
        B_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82, purity_rise=2, 
                                   sugar_moisture=5, sugar_purity=92, sugar_temp=150, molasses_temp=145, name="B Centrifugals"),
        C_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82, purity_rise=4,
                                   sugar_moisture=5, sugar_purity=82, sugar_temp=150, molasses_temp=145, name="C Centrifugals"),
        C_crystallizers=Crystallizer(massecuite_in=None, massecuite_flow_lb_hr=0,
                                     masse_temp_out_deg_F=120, ml_purity_out=30,
                                     water_temp_in_deg_F=85, water_temp_out_deg_F=105,
                                     name="C Crystallizers"),
        C_reheaters=Reheater(massecuite_in=None, massecuite_flow_lb_hr=0,
                             masse_temp_out_deg_F=130,
                             water_temp_in_deg_F=150, water_temp_out_deg_F=135,
                             name="C Reheaters"),
        b_magma_remelt_pct=20,
        c_magma_remelt_pct=20,
        a_mol_to_grain_pct=3,
        b_mol_to_grain_pct=10,
        syrup_to_grain_pct=1,
        a_mol_top_off_pct=0
    )

    pan_floor.neat_display()
    pan_floor.A_pans.neat_display()


