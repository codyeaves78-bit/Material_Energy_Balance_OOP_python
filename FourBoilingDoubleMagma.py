from Pan import Pan
from Centrifugal import Centrifugal
from SugarStream import SugarStream
from pan_floor_diagram import plot_four_boiling


def make_magma(sugar_stream: SugarStream, mingler_brix: float) -> SugarStream:
    magma = SugarStream.copy(sugar_stream)
    solids = magma.solids_flow
    magma.brix = mingler_brix
    magma.flow_lb_per_hr = solids / magma.brix * 100
    return magma


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


class FourBoilingDoubleMagma:
    """Four Boiling Double Magma balance: A1, A2, B, C pans with grain pans.
    When inputting Pan and Centrifugal objects, user does not need to define inlet streams."""

    def __init__(
        self,
        syrup: SugarStream,
        A1_pans: Pan,
        A2_pans: Pan,
        B_pans: Pan,
        C_pans: Pan,
        grain_pans: Pan,
        A1_centrifugals: Centrifugal,
        A2_centrifugals: Centrifugal,
        B_centrifugals: Centrifugal,
        C_centrifugals: Centrifugal,
        syrup_to_A1_pans_pct: float = 75,
        syrup_to_A2_pans_pct: float = 20,
        a1_mol_to_A2_pct: float = 80,
        a1_mol_to_grain_pct: float = 3,
        a2_mol_to_grain_pct: float = 3,
        b_mol_to_grain_pct: float = 10,
        b_magma_A1_footing_pct: float = 40,
        b_magma_A2_footing_pct: float = 40,
        c_magma_B_footing_pct: float = 80,
        a1_mol_dilution_brix: float = 70,
        a2_mol_dilution_brix: float = 70,
        b_mol_dilution_brix: float = 70,
        iterations: int = 15,
    ):
        self.syrup = syrup

        self._A1_pans_cfg = A1_pans
        self._A2_pans_cfg = A2_pans
        self._B_pans_cfg = B_pans
        self._C_pans_cfg = C_pans
        self._grain_pans_cfg = grain_pans
        self._A1_cen_cfg = A1_centrifugals
        self._A2_cen_cfg = A2_centrifugals
        self._B_cen_cfg = B_centrifugals
        self._C_cen_cfg = C_centrifugals

        self.syrup_to_A1_pans_pct = syrup_to_A1_pans_pct
        self.syrup_to_A2_pans_pct = syrup_to_A2_pans_pct
        self.syrup_to_grain_pct = 100.0 - syrup_to_A1_pans_pct - syrup_to_A2_pans_pct

        self.a1_mol_to_A2_pct = a1_mol_to_A2_pct
        self.a1_mol_to_grain_pct = a1_mol_to_grain_pct
        self.a1_mol_to_B_pct = 100.0 - a1_mol_to_A2_pct - a1_mol_to_grain_pct

        self.a2_mol_to_grain_pct = a2_mol_to_grain_pct
        self.a2_mol_to_B_pct = 100.0 - a2_mol_to_grain_pct

        self.b_mol_to_grain_pct = b_mol_to_grain_pct
        self.b_mol_to_C_pct = 100.0 - b_mol_to_grain_pct

        self.b_magma_A1_footing_pct = b_magma_A1_footing_pct
        self.b_magma_A2_footing_pct = b_magma_A2_footing_pct
        self.b_magma_remelt_pct = 100.0 - b_magma_A1_footing_pct - b_magma_A2_footing_pct

        self.c_magma_B_footing_pct = c_magma_B_footing_pct
        self.c_magma_remelt_pct = 100.0 - c_magma_B_footing_pct

        self.a1_mol_dilution_brix = a1_mol_dilution_brix
        self.a2_mol_dilution_brix = a2_mol_dilution_brix
        self.b_mol_dilution_brix = b_mol_dilution_brix

        self._solve(iterations)

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

    def _solve(self, iterations: int = 15):
        # Dummy footings — zero flow so first iteration solves cleanly; overwritten each loop
        b_magma_A1_footing = SugarStream(brix=92, purity=92, flow_lb_per_hr=0, temp_deg_F=130)
        b_magma_A2_footing = SugarStream(brix=92, purity=92, flow_lb_per_hr=0, temp_deg_F=130)
        c_magma_B_footing  = SugarStream(brix=92, purity=85, flow_lb_per_hr=0, temp_deg_F=130)

        syrup_as_fed = SugarStream.copy(self.syrup)

        for _ in range(iterations):
            # ── Split syrup ───────────────────────────────────────────────
            syrup_to_A1 = SugarStream.copy(syrup_as_fed)
            syrup_to_A1.flow_lb_per_hr = self.syrup_to_A1_pans_pct / 100 * syrup_as_fed.flow_lb_per_hr

            syrup_to_A2 = SugarStream.copy(syrup_as_fed)
            syrup_to_A2.flow_lb_per_hr = self.syrup_to_A2_pans_pct / 100 * syrup_as_fed.flow_lb_per_hr

            syrup_to_grain = SugarStream.copy(syrup_as_fed)
            syrup_to_grain.flow_lb_per_hr = self.syrup_to_grain_pct / 100 * syrup_as_fed.flow_lb_per_hr

            # ── A1 pans ───────────────────────────────────────────────────
            self.A1_pans = self._rebuild_pan(self._A1_pans_cfg, [syrup_to_A1, b_magma_A1_footing])
            self.A1_centrifugals = self._rebuild_centrifugal(
                self._A1_cen_cfg, self.A1_pans.massecuite, self.A1_pans.massecuite_flow_lb_hr
            )

            # Dilute A1 molasses, then split
            a1_mol_diluted = dilute_molasses(self.A1_centrifugals.molasses_stream, self.a1_mol_dilution_brix)

            a1_mol_to_A2 = SugarStream.copy(a1_mol_diluted)
            a1_mol_to_A2.flow_lb_per_hr = self.a1_mol_to_A2_pct / 100 * a1_mol_diluted.flow_lb_per_hr

            a1_mol_to_grain = SugarStream.copy(a1_mol_diluted)
            a1_mol_to_grain.flow_lb_per_hr = self.a1_mol_to_grain_pct / 100 * a1_mol_diluted.flow_lb_per_hr

            a1_mol_to_B = SugarStream.copy(a1_mol_diluted)
            a1_mol_to_B.flow_lb_per_hr = self.a1_mol_to_B_pct / 100 * a1_mol_diluted.flow_lb_per_hr

            # ── A2 pans ───────────────────────────────────────────────────
            self.A2_pans = self._rebuild_pan(
                self._A2_pans_cfg, [syrup_to_A2, a1_mol_to_A2, b_magma_A2_footing]
            )
            self.A2_centrifugals = self._rebuild_centrifugal(
                self._A2_cen_cfg, self.A2_pans.massecuite, self.A2_pans.massecuite_flow_lb_hr
            )

            # Dilute A2 molasses, then split
            a2_mol_diluted = dilute_molasses(self.A2_centrifugals.molasses_stream, self.a2_mol_dilution_brix)

            a2_mol_to_grain = SugarStream.copy(a2_mol_diluted)
            a2_mol_to_grain.flow_lb_per_hr = self.a2_mol_to_grain_pct / 100 * a2_mol_diluted.flow_lb_per_hr

            a2_mol_to_B = SugarStream.copy(a2_mol_diluted)
            a2_mol_to_B.flow_lb_per_hr = self.a2_mol_to_B_pct / 100 * a2_mol_diluted.flow_lb_per_hr

            # ── B pans ────────────────────────────────────────────────────
            self.B_pans = self._rebuild_pan(
                self._B_pans_cfg, [a2_mol_to_B, c_magma_B_footing, a1_mol_to_B]
            )
            self.B_centrifugals = self._rebuild_centrifugal(
                self._B_cen_cfg, self.B_pans.massecuite, self.B_pans.massecuite_flow_lb_hr
            )

            # B magma — update footings and remelt split
            b_magma = make_magma(self.B_centrifugals.sugar_stream, mingler_brix=92)
            b_magma_A1_footing = SugarStream.copy(b_magma)
            b_magma_A1_footing.flow_lb_per_hr = self.b_magma_A1_footing_pct / 100 * b_magma.flow_lb_per_hr
            b_magma_A2_footing = SugarStream.copy(b_magma)
            b_magma_A2_footing.flow_lb_per_hr = self.b_magma_A2_footing_pct / 100 * b_magma.flow_lb_per_hr
            b_magma_to_rmlt = SugarStream.copy(b_magma)
            b_magma_to_rmlt.flow_lb_per_hr = self.b_magma_remelt_pct / 100 * b_magma.flow_lb_per_hr

            # Dilute B molasses, then split
            b_mol_diluted = dilute_molasses(self.B_centrifugals.molasses_stream, self.b_mol_dilution_brix)

            b_mol_to_grain = SugarStream.copy(b_mol_diluted)
            b_mol_to_grain.flow_lb_per_hr = self.b_mol_to_grain_pct / 100 * b_mol_diluted.flow_lb_per_hr

            b_mol_to_C = SugarStream.copy(b_mol_diluted)
            b_mol_to_C.flow_lb_per_hr = self.b_mol_to_C_pct / 100 * b_mol_diluted.flow_lb_per_hr

            # ── Grain pans ────────────────────────────────────────────────
            self.grain_pans = self._rebuild_pan(
                self._grain_pans_cfg, [syrup_to_grain, a1_mol_to_grain, a2_mol_to_grain, b_mol_to_grain]
            )

            grain_massecuite = SugarStream(
                brix=self.grain_pans.masse_brix,
                purity=self.grain_pans.masse_purity,
                flow_lb_per_hr=self.grain_pans.massecuite_flow_lb_hr,
                temp_deg_F=self.grain_pans.massecuite.massecuite_temp,
                pressure_psia=14.7,
                level_ft=0,
            )

            # ── C pans ────────────────────────────────────────────────────
            self.C_pans = self._rebuild_pan(self._C_pans_cfg, [grain_massecuite, b_mol_to_C])
            self.C_centrifugals = self._rebuild_centrifugal(
                self._C_cen_cfg, self.C_pans.massecuite, self.C_pans.massecuite_flow_lb_hr
            )

            # C magma — update B footing and remelt split
            c_magma = make_magma(self.C_centrifugals.sugar_stream, mingler_brix=92)
            c_magma_B_footing = SugarStream.copy(c_magma)
            c_magma_B_footing.flow_lb_per_hr = self.c_magma_B_footing_pct / 100 * c_magma.flow_lb_per_hr
            c_magma_to_rmlt = SugarStream.copy(c_magma)
            c_magma_to_rmlt.flow_lb_per_hr = self.c_magma_remelt_pct / 100 * c_magma.flow_lb_per_hr

            # Remelts diluted to remelt_brix
            b_remelt = make_remelt(b_magma_to_rmlt, remelt_brix=65)
            c_remelt = make_remelt(c_magma_to_rmlt, remelt_brix=65)

            # Update syrup_as_fed = evaporator syrup + b remelt + c remelt
            total_flows  = self.syrup.flow_lb_per_hr + b_remelt.flow_lb_per_hr + c_remelt.flow_lb_per_hr
            total_solids = self.syrup.solids_flow     + b_remelt.solids_flow    + c_remelt.solids_flow
            total_pols   = self.syrup.pol_flow        + b_remelt.pol_flow       + c_remelt.pol_flow

            syrup_as_fed = SugarStream.copy(self.syrup)
            syrup_as_fed.flow_lb_per_hr = total_flows
            syrup_as_fed.brix   = total_solids / total_flows  * 100
            syrup_as_fed.purity = total_pols   / total_solids * 100

        self.syrup_as_fed = syrup_as_fed

        self._a1_mol_diluted  = a1_mol_diluted
        self._a2_mol_diluted  = a2_mol_diluted
        self._b_mol_diluted   = b_mol_diluted

        self._b_magma         = b_magma
        self._c_magma         = c_magma
        self._b_magma_to_rmlt = b_magma_to_rmlt
        self._c_magma_to_rmlt = c_magma_to_rmlt
        self._b_remelt        = b_remelt
        self._c_remelt        = c_remelt

    def generate_pfd(self, show=True, save_path=None):
        """Generate a process flow diagram. Returns the matplotlib Figure."""
        from pan_floor_diagram import plot_four_boiling
        return plot_four_boiling(self, show=show, save_path=save_path)

    @property
    def total_water(self) -> SugarStream:
        """All fresh water added to the pan floor (lb/hr): centrifugal wash + magma minglers + remelts."""
        cen_wash = (
            self.A1_centrifugals.wash_water_lb_hr
            + self.A2_centrifugals.wash_water_lb_hr
            + self.B_centrifugals.wash_water_lb_hr
            + self.C_centrifugals.wash_water_lb_hr
        )
        b_mingler    = self._b_magma.flow_lb_per_hr  - self.B_centrifugals.sugar_stream.flow_lb_per_hr
        c_mingler    = self._c_magma.flow_lb_per_hr  - self.C_centrifugals.sugar_stream.flow_lb_per_hr
        b_rmlt_water  = self._b_remelt.flow_lb_per_hr - self._b_magma_to_rmlt.flow_lb_per_hr
        c_rmlt_water  = self._c_remelt.flow_lb_per_hr - self._c_magma_to_rmlt.flow_lb_per_hr
        a1_dil_water  = self._a1_mol_diluted.flow_lb_per_hr - self.A1_centrifugals.molasses_stream.flow_lb_per_hr
        a2_dil_water  = self._a2_mol_diluted.flow_lb_per_hr - self.A2_centrifugals.molasses_stream.flow_lb_per_hr
        b_dil_water   = self._b_mol_diluted.flow_lb_per_hr  - self.B_centrifugals.molasses_stream.flow_lb_per_hr
        total_lb_hr   = (cen_wash + b_mingler + c_mingler + b_rmlt_water + c_rmlt_water
                         + a1_dil_water + a2_dil_water + b_dil_water)
        return SugarStream(brix=0, purity=0, flow_lb_per_hr=total_lb_hr)

    # ──────────────────────────────────────────────────────────────────────
    # Display
    # ──────────────────────────────────────────────────────────────────────

    def display_balance(self):
        W = 115
        HEAVY = "=" * W
        LIGHT = "-" * W

        LBL = 32
        NUM = 13
        VOL = 10

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

        def _pan_station(pan, feed_names=None):
            lines = []
            lines.append("  ENTERING")
            for i, f in enumerate(pan.feed_streams, 1):
                name = feed_names[i - 1] if feed_names and i - 1 < len(feed_names) else f"Feed {i}"
                sol = f.solids_flow
                lines.append(_row(f"    {name}  (Bx={f.brix:.1f} Pu={f.purity:.1f})",
                                  f.flow_lb_per_hr, sol, f.pol_flow,
                                  f.flow_lb_per_hr - sol, f.brix, f.purity, vol_ft3_hr=f.cu_ft_hr))
            ff = pan.feed_flow_lb_hr
            fs = pan.feed_solids_lb_hr
            fp = sum(f.pol_flow for f in pan.feed_streams)
            lines.append(LIGHT)
            lines.append(_row("  Total Feed In", ff, fs, fp, ff - fs))
            lines.append("")
            lines.append("  LEAVING")
            masse_sol   = fs
            masse_pol   = fp
            masse_water = pan.massecuite_flow_lb_hr - masse_sol
            masse_vol   = pan.massecuite_flow_lb_hr / pan.massecuite.density
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

        # ── Totals ────────────────────────────────────────────────────────
        total_evap = (
            self.A1_pans.water_evaporated_lb_hr
            + self.A2_pans.water_evaporated_lb_hr
            + self.B_pans.water_evaporated_lb_hr
            + self.grain_pans.water_evaporated_lb_hr
            + self.C_pans.water_evaporated_lb_hr
        )
        a1_sugar = self.A1_centrifugals.sugar_stream
        a2_sugar = self.A2_centrifugals.sugar_stream
        c_mol    = self.C_centrifugals.molasses_stream

        total_raw_sugar_flow   = a1_sugar.flow_lb_per_hr + a2_sugar.flow_lb_per_hr
        total_raw_sugar_solids = a1_sugar.solids_flow    + a2_sugar.solids_flow
        total_raw_sugar_pol    = a1_sugar.pol_flow       + a2_sugar.pol_flow
        total_raw_sugar_water  = (a1_sugar.flow_lb_per_hr - a1_sugar.solids_flow) + (a2_sugar.flow_lb_per_hr - a2_sugar.solids_flow)

        pol_extr = total_raw_sugar_pol / self.syrup.pol_flow * 100

        out = []
        out.append(HEAVY)
        out.append(f"{'FOUR BOILING DOUBLE MAGMA - COMPLETE FLOOR BALANCE':^{W}}")
        out.append(HEAVY)

        # ── Overall ───────────────────────────────────────────────────────
        out.append(_section("OVERALL FLOOR BALANCE"))
        out.append(f"  (Feed = Evaporator syrup + Wash Water; Products = A1+A2 sugar + C final molasses)")
        out.append("")
        out.append(_hdr())
        out.append("")
        out.append("  ENTERING")
        out.append(_stream("  Syrup From Evaporators", self.syrup))
        out.append(_stream("  Wash and Dilution Water", self.total_water))
        out.append("")
        out.append("  LEAVING")
        out.append(_row("  A1 Product Sugar", a1_sugar.flow_lb_per_hr, a1_sugar.solids_flow,
                        a1_sugar.pol_flow, a1_sugar.flow_lb_per_hr - a1_sugar.solids_flow,
                        a1_sugar.brix, a1_sugar.purity, vol_ft3_hr=a1_sugar.cu_ft_hr))
        out.append(_row("  A2 Product Sugar", a2_sugar.flow_lb_per_hr, a2_sugar.solids_flow,
                        a2_sugar.pol_flow, a2_sugar.flow_lb_per_hr - a2_sugar.solids_flow,
                        a2_sugar.brix, a2_sugar.purity, vol_ft3_hr=a2_sugar.cu_ft_hr))
        out.append(_row("  Total Raw Sugar", total_raw_sugar_flow, total_raw_sugar_solids,
                        total_raw_sugar_pol, total_raw_sugar_water))
        out.append(_stream("  C Final Molasses", c_mol))
        out.append(_row("  Evaporated (all pans)", total_evap, 0, 0, total_evap))
        out.append("")

        tw = self.total_water
        in_flow    = self.syrup.flow_lb_per_hr + tw.flow_lb_per_hr
        in_solids  = self.syrup.solids_flow
        in_pol     = self.syrup.pol_flow
        in_water   = (self.syrup.flow_lb_per_hr - self.syrup.solids_flow) + tw.flow_lb_per_hr
        out_flow   = total_raw_sugar_flow + c_mol.flow_lb_per_hr + total_evap
        out_solids = total_raw_sugar_solids + c_mol.solids_flow
        out_pol    = total_raw_sugar_pol    + c_mol.pol_flow
        out_water  = (total_raw_sugar_water
                      + (c_mol.flow_lb_per_hr - c_mol.solids_flow)
                      + total_evap)

        out.append(LIGHT)
        out.append(_row("  Total Entering", in_flow,  in_solids,  in_pol,  in_water))
        out.append(_row("  Total Leaving",  out_flow, out_solids, out_pol, out_water))
        out.append(LIGHT)
        out.append(_row("  Net (In - Out)", in_flow - out_flow, in_solids - out_solids,
                                            in_pol  - out_pol,  in_water  - out_water))
        out.append(f"  {'Pol% Recovered in Raw Sugar (A1+A2 / feed):':<{LBL+NUM}} {pol_extr:6.2f} %")
        out.append("")

        # ── A1 Pans ───────────────────────────────────────────────────────
        out.append(_section(f"A1 PANS  [{self.A1_pans.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_pan_station(self.A1_pans, ["Syrup", "B Magma"]))

        # ── A1 Centrifugals ───────────────────────────────────────────────
        out.append(_section(f"A1 CENTRIFUGALS  [{self.A1_centrifugals.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_cen_station(self.A1_centrifugals))

        # ── A1 Molasses Dilution ──────────────────────────────────────────
        out.append(_section(f"A1 MOLASSES DILUTION  (target {self.a1_mol_dilution_brix:.1f} Bx)"))
        out.append(_hdr())
        out.append("")
        out.extend(_dil_station(self.A1_centrifugals.molasses_stream, self._a1_mol_diluted, "A1 Molasses"))

        # ── A2 Pans ───────────────────────────────────────────────────────
        out.append(_section(f"A2 PANS  [{self.A2_pans.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_pan_station(self.A2_pans, ["Syrup", "A1 Molasses", "B Magma"]))

        # ── A2 Centrifugals ───────────────────────────────────────────────
        out.append(_section(f"A2 CENTRIFUGALS  [{self.A2_centrifugals.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_cen_station(self.A2_centrifugals))

        # ── A2 Molasses Dilution ──────────────────────────────────────────
        out.append(_section(f"A2 MOLASSES DILUTION  (target {self.a2_mol_dilution_brix:.1f} Bx)"))
        out.append(_hdr())
        out.append("")
        out.extend(_dil_station(self.A2_centrifugals.molasses_stream, self._a2_mol_diluted, "A2 Molasses"))

        # ── B Pans ────────────────────────────────────────────────────────
        out.append(_section(f"B PANS  [{self.B_pans.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_pan_station(self.B_pans, ["A2 Molasses", "C Magma", "A1 Molasses"]))

        # ── B Centrifugals ────────────────────────────────────────────────
        out.append(_section(f"B CENTRIFUGALS  [{self.B_centrifugals.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_cen_station(self.B_centrifugals))

        # ── B Molasses Dilution ───────────────────────────────────────────
        out.append(_section(f"B MOLASSES DILUTION  (target {self.b_mol_dilution_brix:.1f} Bx)"))
        out.append(_hdr())
        out.append("")
        out.extend(_dil_station(self.B_centrifugals.molasses_stream, self._b_mol_diluted, "B Molasses"))

        # ── Grain Pans ────────────────────────────────────────────────────
        out.append(_section(f"GRAIN PANS  [{self.grain_pans.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_pan_station(self.grain_pans, ["Syrup", "A1 Molasses", "A2 Molasses", "B Molasses"]))

        # ── C Pans ────────────────────────────────────────────────────────
        out.append(_section(f"C PANS  [{self.C_pans.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_pan_station(self.C_pans, ["Grain Massecuite", "B Molasses"]))

        # ── C Centrifugals ────────────────────────────────────────────────
        out.append(_section(f"C CENTRIFUGALS  [{self.C_centrifugals.name}]"))
        out.append(_hdr())
        out.append("")
        out.extend(_cen_station(self.C_centrifugals))
        out.append("")
        out.append(HEAVY)

        print("\n".join(out))


if __name__ == "__main__":
    pan_floor = FourBoilingDoubleMagma(
        syrup=SugarStream(brix=65, purity=89, flow_lb_per_hr=100_000, temp_deg_F=140),
        A1_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=16000,
            inches_vacuum=23.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=92,
            ml_purity=75,
            calandria_pressure_psia=21.696,
            heat_loss_factor=0.02, name='A1 Pans'),
        A2_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=6000,
            inches_vacuum=23.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=92,
            ml_purity=70,
            calandria_pressure_psia=21.696,
            heat_loss_factor=0.02, name='A2 Pans'),
        B_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=7500,
            inches_vacuum=25,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=94,
            ml_purity=52,
            calandria_pressure_psia=29.696,
            heat_loss_factor=0.05, name='B Pans'),
        grain_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=3000,
            inches_vacuum=25.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=88,
            ml_purity=45,
            calandria_pressure_psia=29.696,
            heat_loss_factor=0.05, name='Grain Pans'),
        C_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=12000,
            inches_vacuum=26.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=95.5,
            ml_purity=33,
            calandria_pressure_psia=21.696,
            heat_loss_factor=0.05, name='C Pans'),
        A1_centrifugals=Centrifugal(
            massecuite=None, massecuite_flow_lb_hr=0,
            target_molasses_brix=82, purity_rise=0,
            sugar_moisture=0.2, sugar_purity=99.7,
            sugar_temp=150, molasses_temp=145, name="A1 Centrifugals"),
        A2_centrifugals=Centrifugal(
            massecuite=None, massecuite_flow_lb_hr=0,
            target_molasses_brix=82, purity_rise=0,
            sugar_moisture=0.2, sugar_purity=99.3,
            sugar_temp=150, molasses_temp=145, name="A2 Centrifugals"),
        B_centrifugals=Centrifugal(
            massecuite=None, massecuite_flow_lb_hr=0,
            target_molasses_brix=82, purity_rise=0,
            sugar_moisture=5, sugar_purity=92,
            sugar_temp=150, molasses_temp=145, name="B Centrifugals"),
        C_centrifugals=Centrifugal(
            massecuite=None, massecuite_flow_lb_hr=0,
            target_molasses_brix=82, purity_rise=0,
            sugar_moisture=5, sugar_purity=82,
            sugar_temp=150, molasses_temp=145, name="C Centrifugals"),
        syrup_to_A1_pans_pct=75,
        syrup_to_A2_pans_pct=20, # remainder goes to grain pans
        a1_mol_to_A2_pct=80,
        a1_mol_to_grain_pct=3,
        a2_mol_to_grain_pct=0,
        b_mol_to_grain_pct=10,
        b_magma_A1_footing_pct=40,
        b_magma_A2_footing_pct=40, # remaining goes to remelt
        c_magma_B_footing_pct=80, # remaining goes to remelt
        iterations=15,
    )

    pan_floor.display_balance()
   # pan_floor.generate_pfd(show=True, save_path=None)
