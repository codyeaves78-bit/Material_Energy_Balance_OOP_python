from Pan import Pan
from Centrifugal import Centrifugal
from Crystallizer_and_Reheater import Crystallizer, Reheater
from SugarStream import SugarStream
from condensate_utils import flash_condensate


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

class TwoBoiling:
    def __init__(
                self,
                syrup: SugarStream,
                A_pans: Pan,
                C_pans: Pan,
                grain_pans: Pan,
                A_centrifugals: Centrifugal,
                C_centrifugals: Centrifugal,
                C_crystallizers: Crystallizer = None,
                C_reheaters: Reheater = None,
                c_magma_remelt_pct: float = 20,
                syrup_to_grain_pct: float = 5,
                syrup_to_C_pct: float = 5,
                a_mol_to_grain_pct: float = 5,
                a_mol_top_off_pct: float = 30,
                a_mol_dilution_brix: float = 70,
                c_magma_brix: float = 92,
                c_remelt_brix: float = 65,
                injection_water_temp_F: float = 90,
                condenser_leg_temp_drop_F: float = 5,
                iterations: int = 20,
                ):
        """The flow of a Two Boiling shceme
        Syrup, C magma footing, C magma remelt, and top off A molasses --> A pans
        A massecuite out of A pans --> A centr
        Sugar out A centr --> Warehouse
        A molasses from A centr --> A pans (top off), Grain, and C Pans (No B pans for TwoBoiling)
        Syrup and A molasses --> Grain Pans
        grain from Grain pans --> C Pans
        so Grain, Syrup, and remaining A molasses --> C Pans
        C massecuite from C Pans --> Cooling Crystallizer --> Reheater --> C Centr
        Sugar from C centr --> mingler to make C magma then C magma --> A pan footing and remainder remelted to --> Syrup
        C molasses --> Storage Tanks"""
        
        self.syrup = syrup
        self.injection_water_temp_F = injection_water_temp_F
        self.condensor_leg_temp_drop_F = condenser_leg_temp_drop_F # degrees below the vapor temp
        # Store Pan/Centrifugal configs as templates; solved instances assigned in _solve()
        self._A_pans_cfg = A_pans
        self._C_pans_cfg = C_pans
        self._grain_pans_cfg = grain_pans
        self._A_cen_cfg = A_centrifugals
        self._C_cen_cfg = C_centrifugals
        # Default: cool to 120°F / reheat to 130°F with no exhaustion (ml purity carried)
        self._C_crys_cfg = (C_crystallizers if C_crystallizers is not None
                            else Crystallizer(massecuite_in=None, massecuite_flow_lb_hr=0,
                                              name='C Crystallizers'))
        self._C_reheat_cfg = (C_reheaters if C_reheaters is not None
                              else Reheater(massecuite_in=None, massecuite_flow_lb_hr=0,
                                            name='C Reheaters'))

        self.c_magma_remelt_pct = c_magma_remelt_pct
        self.syrup_to_grain_pct = syrup_to_grain_pct
        self.syrup_to_C_pct = syrup_to_C_pct
        self.a_mol_to_grain_pct = a_mol_to_grain_pct
        self.a_mol_top_off_pct = a_mol_top_off_pct
        self.a_mol_to_C_pans_pct = 100.0 - a_mol_top_off_pct - a_mol_to_grain_pct
        self.a_mol_dilution_brix = a_mol_dilution_brix
        self.c_magma_brix = c_magma_brix
        self.c_remelt_brix = c_remelt_brix
        self.syrup_to_A_pans_pct = 100.0 - self.syrup_to_grain_pct - self.syrup_to_C_pct

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
            steam_type=config.steam_type,
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
        # are placeholders only; the loop replaces them before they matter.
        c_magma_A_pans = SugarStream(brix=self.c_magma_brix, purity=80, flow_lb_per_hr=0, temp_deg_F=130)

        # Initial Syrup Feed to pans
        syrup_as_fed = SugarStream.copy(self.syrup)
        syrup_to_A_pans = SugarStream.copy(self.syrup)
        syrup_to_A_pans.flow_lb_per_hr = self.syrup_to_A_pans_pct / 100 * self.syrup.flow_lb_per_hr

        # Dummy top-off A molasses — zero flow for the first A pan solve.
        # Overwritten each iteration from A centrifugals molasses_stream.
        top_off_a_mol = SugarStream(brix=70, purity=70, flow_lb_per_hr=0, temp_deg_F=140)

        for _ in range(iterations):
            self.A_pans = self._rebuild_pan(
                self._A_pans_cfg, [syrup_to_A_pans, c_magma_A_pans, top_off_a_mol]
            )
            self.A_centrifugals = self._rebuild_centrifugal(
                self._A_cen_cfg, self.A_pans.massecuite, self.A_pans.massecuite_flow_lb_hr
            )

            a_mol_diluted = dilute_molasses(self.A_centrifugals.molasses_stream, self.a_mol_dilution_brix)

            top_off_a_mol = SugarStream.copy(a_mol_diluted)
            top_off_a_mol.flow_lb_per_hr = self.a_mol_top_off_pct / 100 * top_off_a_mol.flow_lb_per_hr

            a_mol_grain = SugarStream.copy(a_mol_diluted)
            a_mol_grain.flow_lb_per_hr = self.a_mol_to_grain_pct / 100 * a_mol_grain.flow_lb_per_hr

            a_mol_C_pans = SugarStream.copy(a_mol_diluted) # Remainder to C pans
            a_mol_C_pans.flow_lb_per_hr = self.a_mol_to_C_pans_pct / 100 * a_mol_diluted.flow_lb_per_hr

            syrup_to_grain = SugarStream.copy(syrup_as_fed)
            syrup_to_grain.flow_lb_per_hr = self.syrup_to_grain_pct / 100 * syrup_as_fed.flow_lb_per_hr

            syrup_to_C = SugarStream.copy(syrup_as_fed)
            syrup_to_C.flow_lb_per_hr = self.syrup_to_C_pct / 100 * syrup_as_fed.flow_lb_per_hr

            self.grain_pans = self._rebuild_pan(
                self._grain_pans_cfg, [syrup_to_grain, a_mol_grain]
            )

            grain_massecuite = SugarStream(
                brix=self.grain_pans.masse_brix,
                purity=self.grain_pans.masse_purity,
                flow_lb_per_hr=self.grain_pans.massecuite_flow_lb_hr,
                temp_deg_F=self.grain_pans.massecuite.massecuite_temp,
                pressure_psia=14.7,
                level_ft=0,
            )

            self.C_pans = self._rebuild_pan(
                self._C_pans_cfg, [grain_massecuite, a_mol_C_pans, syrup_to_C]
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

            c_magma = make_magma(self.C_centrifugals.sugar_stream, mingler_brix=self.c_magma_brix)

            c_magma_A_pans = SugarStream.copy(c_magma)
            c_magma_A_pans.flow_lb_per_hr = (100 - self.c_magma_remelt_pct) / 100 * c_magma_A_pans.flow_lb_per_hr

            c_magma_to_rmlt = SugarStream.copy(c_magma)
            c_magma_to_rmlt.flow_lb_per_hr = self.c_magma_remelt_pct / 100 * c_magma_to_rmlt.flow_lb_per_hr
            c_remelt = make_remelt(c_magma_to_rmlt, remelt_brix=self.c_remelt_brix)

            total_flows = self.syrup.flow_lb_per_hr + c_remelt.flow_lb_per_hr 
            total_solids = self.syrup.solids_flow + c_remelt.solids_flow
            total_pols = self.syrup.pol_flow + c_remelt.pol_flow

            syrup_as_fed = SugarStream.copy(self.syrup)
            syrup_as_fed.flow_lb_per_hr = total_flows
            syrup_as_fed.brix = total_solids / total_flows * 100
            syrup_as_fed.purity = total_pols / total_solids * 100

            syrup_to_A_pans = SugarStream.copy(syrup_as_fed)
            syrup_to_A_pans.flow_lb_per_hr = self.syrup_to_A_pans_pct / 100 * syrup_to_A_pans.flow_lb_per_hr

        self.syrup_as_fed = syrup_as_fed

        # Save final-iteration magma/remelt/dilution streams for water accounting
        self._c_magma          = c_magma
        self._c_magma_A_pans   = c_magma_A_pans
        self._c_magma_to_rmlt  = c_magma_to_rmlt
        self._c_remelt         = c_remelt
        self._a_mol_diluted    = a_mol_diluted


    @property
    def pan_condensers(self):
        """Each pan's vapor goes to its own barometric condenser: [(name, Condenser)]."""
        from Condenser import Condenser
        return [
            (pan.name, Condenser(pan.vapor_evaporated, self.injection_water_temp_F, self.condensor_leg_temp_drop_F))
            for pan in (self.A_pans, self.grain_pans, self.C_pans)
        ]

    @property
    def _pans(self):
        return (self.A_pans, self.grain_pans, self.C_pans)

    def _steam_demand_lb_hr(self, steam_type: int) -> float:
        return sum(pan.steam_flow_lb_hr for pan in self._pans if pan.steam_type == steam_type)

    @property
    def total_raw_sugar(self) -> SugarStream:
        """Object of combined Sugars leaving process, in this case, just A sugar"""
        return SugarStream.copy(self.A_centrifugals.sugar_stream)

    @property
    def total_exhaust_steam_lb_hr(self) -> float:
        """Total live/exhaust steam consumed by pans on steam_type 0 (lb/hr)."""
        return self._steam_demand_lb_hr(0)

    @property
    def total_V1_steam_lb_hr(self) -> float:
        """Total V1 vapor consumed by pans on steam_type 1 (lb/hr)."""
        return self._steam_demand_lb_hr(1)

    @property
    def total_V2_steam_lb_hr(self) -> float:
        """Total V2 vapor consumed by pans on steam_type 2 (lb/hr)."""
        return self._steam_demand_lb_hr(2)

    @property
    def total_V3_steam_lb_hr(self) -> float:
        """Total V3 vapor consumed by pans on steam_type 3 (lb/hr)."""
        return self._steam_demand_lb_hr(3)

    @property
    def total_V4_steam_lb_hr(self) -> float:
        """Total V4 vapor consumed by pans on steam_type 4 (lb/hr)."""
        return self._steam_demand_lb_hr(4)

    @property
    def clean_condensate(self) -> float:
        """Post-flash condensate from pans on exhaust steam (steam_type 0) (lb/hr)."""
        return sum(flash_condensate(pan.steam_flow_lb_hr, pan.calandria_T_sat_F)
                   for pan in self._pans if pan.steam_type == 0)

    @property
    def dirty_condensate(self) -> float:
        """Post-flash condensate from pans on vapor bleed steam (steam_type 1-4) (lb/hr)."""
        return sum(flash_condensate(pan.steam_flow_lb_hr, pan.calandria_T_sat_F)
                   for pan in self._pans if pan.steam_type != 0)

    @property
    def total_water(self) -> SugarStream:
        """All fresh water added to the pan floor (lb/hr): centrifugal wash + magma minglers + remelts."""
        cen_wash     = (self.A_centrifugals.wash_water_lb_hr
                      + self.C_centrifugals.wash_water_lb_hr)
        c_mingler    = self._c_magma.flow_lb_per_hr    - self.C_centrifugals.sugar_stream.flow_lb_per_hr
        c_rmlt_water = self._c_remelt.flow_lb_per_hr   - self._c_magma_to_rmlt.flow_lb_per_hr
        a_dil_water  = self._a_mol_diluted.flow_lb_per_hr - self.A_centrifugals.molasses_stream.flow_lb_per_hr
        total_lb_hr  = (cen_wash + c_mingler + c_rmlt_water
                        + a_dil_water)
        return SugarStream(brix=0, purity=0, flow_lb_per_hr=total_lb_hr)

    def generate_pfd(self, show=True, save_path=None, include_table=True):
        """Generate a process flow diagram with a stream table. Returns the Figure."""
        from two_boiling_diagram import plot_two_boiling
        return plot_two_boiling(self, show=show, save_path=save_path,
                                include_table=include_table)

    def to_excel(self, workbook):
        """Write the full floor balance to its own styled sheet: the PFD
        (diagram only), the numbered stream table, the water streams not
        drawn, the overall balance, and every station."""
        import matplotlib.pyplot as plt
        from excel_export import SheetWriter
        from two_boiling_diagram import _collect_streams, _collect_water
        from pan_floor_excel import (HDRS, FMTS, srow, wrow, totals_rows,
                                     pan_table, cen_table, dil_table, heatx_table,
                                     condenser_table, magma_table, magma_split_table,
                                     remelt_table, syrup_recombination_table)

        a_sugar = self.A_centrifugals.sugar_stream
        c_mol   = self.C_centrifugals.molasses_stream
        total_evap = (self.A_pans.water_evaporated_lb_hr + self.grain_pans.water_evaporated_lb_hr
                      + self.C_pans.water_evaporated_lb_hr)
        pol_extr = a_sugar.pol_flow / self.syrup.pol_flow * 100

        sw = SheetWriter(workbook, "Pan Floor - Two Boiling", ncols=9)
        sw.title("Two Boiling — Pan Floor",
                 f"Syrup {self.syrup.flow_lb_per_hr:,.0f} lb/hr @ {self.syrup.brix:.1f} Bx "
                 f"| Pol recovered in raw sugar = {pol_extr:.2f}%")

        sw.section("PROCESS FLOW DIAGRAM")
        sw.blank()
        fig = self.generate_pfd(show=False, include_table=False)
        sw.image(fig, width_in=10.00)
        plt.close(fig)

        sw.page_break()
        sw.section("STREAM TABLE  (tags match the diagram)")
        sw.table(["#", "Stream", "Flow (lb/hr)", "Brix %", "Purity %"],
                 _collect_streams(self),
                 fmts=["0", "@", "#,##0", "0.0", "0.0"])

        sw.page_break()
        sw.section("STREAMS NOT SHOWN — WATER")
        wleft, wright, (total_in, total_evap_chk) = _collect_water(self)
        water_rows = wleft + wright
        water_totals_row = sw.r + 1 + len(water_rows)   # row of the first totals line below
        sw.table(["Stream", "Flow (lb/hr)"], water_rows, fmts=["@", "#,##0"],
                 totals=[("Total Fresh Water In (wash + mingler + remelt + dilution)", total_in),
                         ("Total Water Evaporated", total_evap_chk)])

        sw.section("OVERALL FLOOR BALANCE")
        tw = self.total_water
        in_f  = self.syrup.flow_lb_per_hr + tw.flow_lb_per_hr
        in_s  = self.syrup.solids_flow
        in_p  = self.syrup.pol_flow
        out_f = a_sugar.flow_lb_per_hr + c_mol.flow_lb_per_hr + total_evap
        out_s = a_sugar.solids_flow + c_mol.solids_flow
        out_p = a_sugar.pol_flow + c_mol.pol_flow
        sw.table(HDRS, [
            srow("Syrup From Evaporators", "In", self.syrup),
            wrow("Wash and Dilution Water", "In", tw.flow_lb_per_hr),
            srow("A Product Sugar", "Out", a_sugar),
            srow("C Final Molasses", "Out", c_mol),
            wrow("Evaporated (all pans)", "Out", total_evap),
        ], fmts=FMTS, totals=totals_rows(in_f, in_s, in_p, in_f - in_s,
                                         out_f, out_s, out_p, out_f - out_s))
        sw.row("Pol % recovered", pol_extr, "%", col=1)

        sw.section("PAN FLOOR SYRUP  (Evaporator Syrup + Remelt)")
        syrup_recombination_table(sw, self.syrup, [("C", self._c_remelt)], self.syrup_as_fed)

        # ── Stations ───────────────────────────────────────────────────────
        sw.page_break()
        sw.section(f"A PANS  [{self.A_pans.name}]")
        pan_table(sw, self.A_pans, ["Syrup", "C Magma", "A Molasses Top-off"])
        sw.section(f"A CENTRIFUGALS  [{self.A_centrifugals.name}]")
        cen_table(sw, self.A_centrifugals)
        sw.section(f"A MOLASSES DILUTION  (target {self.a_mol_dilution_brix:.1f} Bx)")
        dil_table(sw, self.A_centrifugals.molasses_stream, self._a_mol_diluted, "A Molasses")

        sw.page_break()
        sw.section(f"GRAIN PANS  [{self.grain_pans.name}]")
        pan_table(sw, self.grain_pans, ["Syrup", "A Molasses"])

        sw.section(f"C PANS  [{self.C_pans.name}]")
        pan_table(sw, self.C_pans, ["Grain Massecuite", "A Molasses", "Syrup"])
        sw.section(f"C CRYSTALLIZERS  [{self.C_crystallizers.name}]")
        heatx_table(sw, self.C_crystallizers, "Cooling Water")
        sw.section(f"C REHEATERS  [{self.C_reheaters.name}]")
        heatx_table(sw, self.C_reheaters, "Hot Water")
        sw.section(f"C CENTRIFUGALS  [{self.C_centrifugals.name}]")
        cen_table(sw, self.C_centrifugals)

        sw.section(f"C MAGMA  (mingler target {self.c_magma_brix:.1f} Bx)")
        magma_table(sw, self.C_centrifugals.sugar_stream, self._c_magma, "C")
        sw.section("C MAGMA DISTRIBUTION")
        magma_split_table(sw, self._c_magma, [
            ("C Magma to A Footing", self._c_magma_A_pans),
            ("C Magma to Remelt",    self._c_magma_to_rmlt),
        ])
        sw.section(f"C REMELT  (target {self.c_remelt_brix:.1f} Bx)")
        remelt_table(sw, self._c_magma_to_rmlt, self._c_remelt, "C", self.c_remelt_brix)

        sw.section("PAN VAPOR CONDENSERS  (one per pan)")
        condenser_table(sw, self.pan_condensers, self.injection_water_temp_F)
        sw.row("Note: if using CoolingTowerSystem, ignore these injection water "
               "demands - they are re-solved there at the delivered water temp.", "")

        sw.section("CONDENSATE RETURN")
        sw.row("Clean condensate (Exhaust steam pans)",  self.clean_condensate, "lb/hr", fmt="#,##0")
        sw.row("Dirty condensate (V1-V4 steam pans)",    self.dirty_condensate, "lb/hr", fmt="#,##0")
        sw.row("Total condensate", self.clean_condensate + self.dirty_condensate, "lb/hr", fmt="#,##0")

        ws = sw.finish()
        col_widths_px = {'A': 164, 'B': 142, 'C': 93, 'D': 78, 'E': 109,
                         'F': 98, 'G': 96, 'H': 87, 'I': 98}
        for letter, px in col_widths_px.items():
            ws.column_dimensions[letter].width = (px - 5) / 7
        from openpyxl.styles import Alignment
        wrap = Alignment(horizontal='left', vertical='center', wrap_text=True)
        ws.cell(row=water_totals_row, column=1).alignment = wrap
        return ws


if __name__ == "__main__":
    pan_floor = TwoBoiling(
        syrup=SugarStream(brix=60, purity=78, flow_lb_per_hr=166_666, temp_deg_F=140),
        A_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=22500,
            inches_vacuum=23.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=92,
            ml_purity=55,
            calandria_pressure_psia=21.696,   # V1 (7 psig)
            heat_loss_factor=0.02, name='A Pans'),
        grain_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=3000,
            inches_vacuum=25.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=88,
            ml_purity=45,
            calandria_pressure_psia=29.696,   # Exhaust (15 psig)
            heat_loss_factor=0.05, name='Grain Pans'),
        C_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=12000,
            inches_vacuum=26.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=95.5,
            ml_purity=30,
            calandria_pressure_psia=21.696,   # V1 (7 psig)
            heat_loss_factor=0.05, name='C Pans'),
        A_centrifugals=Centrifugal(
            massecuite=None, 
            massecuite_flow_lb_hr=0, 
            target_molasses_brix=82, 
            purity_rise=2,
            sugar_moisture=0.3, 
            sugar_purity=99.4, 
            sugar_temp=150, 
            molasses_temp=145, 
            name="A Centrifugals"
            ),
        C_centrifugals=Centrifugal(
            massecuite=None, 
            massecuite_flow_lb_hr=0, 
            target_molasses_brix=82, 
            purity_rise=4,
            sugar_moisture=5, 
            sugar_purity=78, 
            sugar_temp=150, 
            molasses_temp=145, 
            name="C Centrifugals"
            ),
        C_crystallizers=Crystallizer(
            massecuite_in=None, 
            massecuite_flow_lb_hr=0,
            masse_temp_out_deg_F=120, ml_purity_out=30,
            water_temp_in_deg_F=85, water_temp_out_deg_F=105,
            name="C Crystallizers"
            ),
        C_reheaters=Reheater(
            massecuite_in=None, 
            massecuite_flow_lb_hr=0,
            masse_temp_out_deg_F=130,
            water_temp_in_deg_F=150, 
            water_temp_out_deg_F=135,
            name="C Reheaters"
            ),
        c_magma_remelt_pct=20,
        syrup_to_grain_pct=1,
        syrup_to_C_pct=5,
        a_mol_to_grain_pct=3,
        a_mol_top_off_pct=30,
    )

    print(f"A Sugar: {pan_floor.A_centrifugals.sugar_stream.flow_lb_per_hr:,.0f} lb/hr "
          f"@ {pan_floor.A_centrifugals.sugar_stream.purity:.1f} purity")
    print(f"C Final Molasses: {pan_floor.C_centrifugals.molasses_stream.flow_lb_per_hr:,.0f} lb/hr "
          f"@ {pan_floor.C_centrifugals.molasses_stream.purity:.1f} purity")
    pol_extr = (pan_floor.A_centrifugals.sugar_stream.pol_flow
                / pan_floor.syrup.pol_flow * 100)
    print(f"Pol % recovered in raw sugar: {pol_extr:.2f} %")

    # pan_floor.generate_pfd(show=True, save_path=None)

    # Excel export demo — one workbook, this unit on its own sheet
    from excel_export import new_workbook
    wb = new_workbook()
    pan_floor.to_excel(wb)
    wb.save("two_boiling.xlsx")
    print("\nSaved two_boiling.xlsx") 