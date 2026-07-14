# condensate_balance: reconciles available condensate (clean exhaust vs.
# dirty inter-effect/vapor condensate, tallied elsewhere via each unit's
# clean_condensate/dirty_condensate) against water demand locations (boiler
# feed water, imbibition, wash water, dilution water, etc.).
#
# The supply section (clean/dirty condensate totals) and demand section
# (condensate/well water split per location) are computed independently and
# shown side by side — this does NOT auto-allocate condensate to demands.
# You reconcile the two by eye and decide routing yourself; the "Note" field
# on a demand is just a label you attach (e.g. flagging boiler feed water as
# clean-condensate-only), it does not change the calculation.
#
# For a demand that is BLENDED, the condensate/well water split is a simple
# energy balance against one combined condensate temperature (a single
# number for the whole balance, since tracking a separate temperature per
# condensate source would only matter if this file were doing the
# allocation itself, which it isn't):
#     flow_cond * T_cond + flow_well * T_well = flow_target * T_target
#     flow_cond + flow_well = flow_target
# For a demand that is COOLED (via heat exchanger, not blended with well
# water), the full flow is condensate by definition.

from excel_export import SheetWriter


class CondensateDemand:
    """
    One water demand location (boiler feed water, imbibition, wash water,
    dilution water/molasses/remelt, etc.).

    flow_lb_hr : total water flow required at this location (lb/hr).
    temp_F     : target temperature at this location (°F).
    method     : 'blended' (mix condensate + well water to hit temp_F) or
                 'cooled' (full flow is condensate, cooled via heat
                 exchanger rather than diluted with well water).
    note       : optional free-text tag, e.g. a usage recommendation —
                 purely informational, printed/exported as-is.

    Solved fields (set by CondensateBalance):
        condensate_flow_lb_hr, well_water_flow_lb_hr, warning
    """

    def __init__(self, name: str, flow_lb_hr: float, temp_F: float,
                 method: str = 'blended', note: str = ''):
        method = method.lower()
        if method not in ('blended', 'cooled'):
            raise ValueError(f"method must be 'blended' or 'cooled', got '{method}'")
        self.name = name
        self.flow_lb_hr = flow_lb_hr
        self.temp_F = temp_F
        self.method = method
        self.note = note

        self.condensate_flow_lb_hr = 0.0
        self.well_water_flow_lb_hr = 0.0
        self.warning = ''

    @property
    def condensate_pct(self):
        return self.condensate_flow_lb_hr / self.flow_lb_hr * 100 if self.flow_lb_hr else 0.0


class CondensateBalance:
    """
    Balances available condensate against water demand locations.

    clean_condensate_dict, dirty_condensate_dict : {label: lb/hr}
        Available condensate streams (e.g. evap_set.clean_condensate,
        pan_floor.dirty_condensate, par_heaters.clean_condensate, ...),
        tagged by source purity. Shown as two lists + totals — informational
        only, not consumed by the demand-side calc below.
    demands : list of CondensateDemand
        Water requirement at each use location.
    well_water_temp_F : cold well water supply temperature (°F).
    combined_condensate_temp_F : single blended condensate temperature used
        for every 'blended' demand's split calc (°F). Default 210°F —
        a typical value once hotter/colder condensate streams mix and pick
        up line losses — if you don't have a measured number, pass one in.

    Example::

        clean_condensate_dict = {
            'Evap Set - Effect 1':      evap_set.clean_condensate,
            'Pan Floor - Exhaust Pans': pan_floor.clean_condensate,
            'Juice Heaters - Exhaust':  par_heaters.clean_condensate,
        }
        dirty_condensate_dict = {
            'Evap Set - Effects 2+':  evap_set.dirty_condensate,
            'Pan Floor - V1-V4 Pans': pan_floor.dirty_condensate,
            'Juice Heaters - V1-V4':  par_heaters.dirty_condensate,
        }
        demands = [
            CondensateDemand('Boiler Feed Water', flow_lb_hr=800_000, temp_F=227,
                             method='blended',
                             note="Recommend usage of clean condensate, make up "
                                  "with minimal dirty condensate or well water"),
            CondensateDemand('Imbibition', flow_lb_hr=1_200_000, temp_F=150, method='blended'),
            CondensateDemand('Wash Water - Pans', flow_lb_hr=150_000, temp_F=160, method='cooled'),
            CondensateDemand('Dilution Water - Molasses/Remelt', flow_lb_hr=90_000, temp_F=180, method='blended'),
        ]
        cb = CondensateBalance(clean_condensate_dict, dirty_condensate_dict, demands,
                               well_water_temp_F=90, combined_condensate_temp_F=210)
        cb.neat_display()
        cb.to_excel(wb)
    """

    def __init__(self,
                 clean_condensate_dict: dict,
                 dirty_condensate_dict: dict,
                 demands: list,
                 well_water_temp_F: float = 90,
                 combined_condensate_temp_F: float = 210,
                 name: str = 'Condensate Balance'):
        self.name = name
        self.clean_condensate_dict = clean_condensate_dict
        self.dirty_condensate_dict = dirty_condensate_dict
        self.demands = demands
        self.well_water_temp_F = well_water_temp_F
        self.combined_condensate_temp_F = combined_condensate_temp_F
        self._solve()

    def _solve(self):
        t_cond = self.combined_condensate_temp_F
        t_well = self.well_water_temp_F

        for d in self.demands:
            d.warning = ''

            if d.method == 'cooled':
                d.condensate_flow_lb_hr = d.flow_lb_hr
                d.well_water_flow_lb_hr = 0.0
                continue

            target = d.temp_F
            if target > t_cond:
                d.warning = (f"Target {target:.1f} °F is above the condensate temp "
                             f"({t_cond:.1f} °F) — clamped to 100% condensate.")
                target = t_cond
            elif target < t_well:
                d.warning = (f"Target {target:.1f} °F is below well water temp "
                             f"({t_well:.1f} °F) — clamped to 100% well water.")
                target = t_well

            if t_cond == t_well:
                cond_frac = 1.0 if target >= t_cond else 0.0
            else:
                cond_frac = (target - t_well) / (t_cond - t_well)
                cond_frac = min(max(cond_frac, 0.0), 1.0)

            d.condensate_flow_lb_hr = d.flow_lb_hr * cond_frac
            d.well_water_flow_lb_hr = d.flow_lb_hr - d.condensate_flow_lb_hr

    # ------------------------------------------------------------------
    # Supply-side totals
    # ------------------------------------------------------------------

    @property
    def total_clean_condensate_lb_hr(self):
        return sum(self.clean_condensate_dict.values())

    @property
    def total_dirty_condensate_lb_hr(self):
        return sum(self.dirty_condensate_dict.values())

    @property
    def total_condensate_available_lb_hr(self):
        return self.total_clean_condensate_lb_hr + self.total_dirty_condensate_lb_hr

    # ------------------------------------------------------------------
    # Demand-side totals
    # ------------------------------------------------------------------

    @property
    def total_water_demand_lb_hr(self):
        return sum(d.flow_lb_hr for d in self.demands)

    @property
    def total_condensate_required_lb_hr(self):
        return sum(d.condensate_flow_lb_hr for d in self.demands)

    @property
    def total_well_water_required_lb_hr(self):
        return sum(d.well_water_flow_lb_hr for d in self.demands)

    @property
    def condensate_surplus_deficit_lb_hr(self):
        """Available minus required (informational only — positive = surplus, negative = shortfall)."""
        return self.total_condensate_available_lb_hr - self.total_condensate_required_lb_hr

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def neat_display(self):
        W = 90
        HEAVY = "=" * W
        LIGHT = "-" * W

        print(HEAVY)
        print(f"{'CONDENSATE BALANCE  -  ' + self.name:^{W}}")
        print(HEAVY)

        print("\n  CLEAN CONDENSATE (exhaust)")
        print(LIGHT)
        for label, flow in self.clean_condensate_dict.items():
            print(f"  {label:<60} {flow:>15,.0f} lb/hr")
        print(LIGHT)
        print(f"  {'Total Clean Condensate':<60} {self.total_clean_condensate_lb_hr:>15,.0f} lb/hr")

        print("\n  DIRTY CONDENSATE (V1-V4 / inter-effect vapor)")
        print(LIGHT)
        for label, flow in self.dirty_condensate_dict.items():
            print(f"  {label:<60} {flow:>15,.0f} lb/hr")
        print(LIGHT)
        print(f"  {'Total Dirty Condensate':<60} {self.total_dirty_condensate_lb_hr:>15,.0f} lb/hr")
        print(LIGHT)
        print(f"  {'TOTAL CONDENSATE AVAILABLE':<60} {self.total_condensate_available_lb_hr:>15,.0f} lb/hr")

        print(f"\n  CONDENSATE DEMAND")
        print(f"  (combined condensate temp = {self.combined_condensate_temp_F:.1f} °F, "
              f"well water temp = {self.well_water_temp_F:.1f} °F)")
        print(LIGHT)
        print(f"  {'Location':<28} {'Method':>8} {'Flow lb/hr':>12} {'Temp F':>8}"
              f" {'Cond lb/hr':>12} {'Well lb/hr':>12} {'Cond %':>8}")
        print(LIGHT)
        for d in self.demands:
            print(f"  {d.name:<28} {d.method:>8} {d.flow_lb_hr:>12,.0f} {d.temp_F:>8.1f}"
                  f" {d.condensate_flow_lb_hr:>12,.0f} {d.well_water_flow_lb_hr:>12,.0f} {d.condensate_pct:>7.1f}%")
            if d.note:
                print(f"      -> {d.note}")
            if d.warning:
                print(f"      WARNING: {d.warning}")
        print(LIGHT)
        print(f"  {'TOTAL':<28} {'':>8} {self.total_water_demand_lb_hr:>12,.0f} {'':>8}"
              f" {self.total_condensate_required_lb_hr:>12,.0f} {self.total_well_water_required_lb_hr:>12,.0f}")

        print(f"\n  CONDENSATE CHECK  (informational — reconcile against the demand list yourself)")
        print(LIGHT)
        print(f"  {'Total condensate available':<40} {self.total_condensate_available_lb_hr:>15,.0f} lb/hr")
        print(f"  {'Total condensate required':<40} {self.total_condensate_required_lb_hr:>15,.0f} lb/hr")
        print(f"  {'Surplus / (Deficit)':<40} {self.condensate_surplus_deficit_lb_hr:>15,.0f} lb/hr")
        print(HEAVY)

    def to_excel(self, workbook, sheet_writer=None):
        """Write the condensate supply and demand tables to their own sheet.
        Pass an existing SheetWriter to append onto a shared sheet instead
        of creating a new one."""
        standalone = sheet_writer is None
        sw = sheet_writer or SheetWriter(workbook, self.name, ncols=7)
        if standalone:
            sw.title(self.name,
                     f"condensate available = {self.total_condensate_available_lb_hr:,.0f} lb/hr | "
                     f"required = {self.total_condensate_required_lb_hr:,.0f} lb/hr")

        sw.section("CLEAN CONDENSATE (exhaust)")
        sw.table(["Stream", "Flow (lb/hr)"],
                 list(self.clean_condensate_dict.items()),
                 fmts=["@", "#,##0"],
                 totals=[("Total Clean Condensate", self.total_clean_condensate_lb_hr)])

        sw.section("DIRTY CONDENSATE (V1-V4 / inter-effect vapor)")
        sw.table(["Stream", "Flow (lb/hr)"],
                 list(self.dirty_condensate_dict.items()),
                 fmts=["@", "#,##0"],
                 totals=[("Total Dirty Condensate", self.total_dirty_condensate_lb_hr)])
        sw.row("TOTAL CONDENSATE AVAILABLE", self.total_condensate_available_lb_hr, "lb/hr", fmt="#,##0")

        sw.section("CONDENSATE DEMAND")
        sw.row("Combined condensate temp", self.combined_condensate_temp_F, "°F", fmt="0.0")
        sw.row("Well water temp", self.well_water_temp_F, "°F", fmt="0.0")
        sw.table(
            ["Location", "Method", "Flow (lb/hr)", "Temp (°F)", "Condensate (lb/hr)",
             "Well Water (lb/hr)", "Condensate %"],
            [
                (d.name, d.method, d.flow_lb_hr, d.temp_F,
                 d.condensate_flow_lb_hr, d.well_water_flow_lb_hr, d.condensate_pct)
                for d in self.demands
            ],
            fmts=["@", "@", "#,##0", "0.0", "#,##0", "#,##0", "0.0"],
            totals=[("TOTAL", "", self.total_water_demand_lb_hr, "",
                     self.total_condensate_required_lb_hr, self.total_well_water_required_lb_hr, "")],
        )
        for d in self.demands:
            if d.note:
                sw.row(f"{d.name} — note", d.note, "")
            if d.warning:
                sw.row(f"{d.name} — warning", d.warning, "")

        sw.section("CONDENSATE CHECK  (informational)")
        sw.row("Total condensate available", self.total_condensate_available_lb_hr, "lb/hr", fmt="#,##0")
        sw.row("Total condensate required",  self.total_condensate_required_lb_hr, "lb/hr", fmt="#,##0")
        sw.row("Surplus / (Deficit)",        self.condensate_surplus_deficit_lb_hr, "lb/hr", fmt="#,##0")

        if not standalone:
            return sw
        ws = sw.finish()
        col_widths_px = {'A': 231, 'B': 151, 'C': 72, 'D': 59, 'E': 112, 'F': 110, 'G': 84}
        for letter, px in col_widths_px.items():
            ws.column_dimensions[letter].width = (px - 5) / 7
        return ws


if __name__ == "__main__":
    clean_condensate_dict = {
        'Evap Set - Effect 1':      41_000,
        'Pan Floor - Exhaust Pans': 15_000,
        'Juice Heaters - Exhaust':  52_000,
    }
    dirty_condensate_dict = {
        'Evap Set - Effects 2+':  102_000,
        'Pan Floor - V1-V4 Pans': 50_000,
        'Juice Heaters - V1-V4':  111_000,
    }

    demands = [
        CondensateDemand('Boiler Feed Water', flow_lb_hr=800_000, temp_F=227, method='blended',
                         note="Recommend usage of clean condensate, make up with "
                              "minimal dirty condensate or well water"),
        CondensateDemand('Imbibition', flow_lb_hr=1_200_000, temp_F=150, method='blended'),
        CondensateDemand('Wash Water - Pans', flow_lb_hr=150_000, temp_F=160, method='cooled'),
        CondensateDemand('Dilution Water - Molasses/Remelt', flow_lb_hr=90_000, temp_F=180, method='blended'),
    ]

    cb = CondensateBalance(clean_condensate_dict, dirty_condensate_dict, demands,
                           well_water_temp_F=90, combined_condensate_temp_F=210,
                           name='Condensate Balance')
    cb.neat_display()

    from excel_export import new_workbook
    wb = new_workbook()
    cb.to_excel(wb)
    wb.save("condensate_balance.xlsx")
    print("\nSaved condensate_balance.xlsx")
