# JuiceHeatingStation: arranges JuiceHeaterShellTube units in SERIES or
# PARALLEL and solves the train. The heat transfer math itself lives in
# JuiceHeaterShellTube — this class only wires the cold streams together
# (chained outlet->inlet for series, flow split for parallel), then reports
# the whole station (neat_display / generate_pfd / to_excel).

from SugarStream import SugarStream
from JuiceHeater import JuiceHeaterShellTube


class JuiceHeatingStation:
    """
    Juice heating station — a group of shell & tube heaters in series or parallel.

    Parameters
    ----------
    cold_stream : SugarStream entering the station.
    heaters     : list of JuiceHeaterShellTube objects used as CONFIG templates
                  (their cold_stream is replaced; hot_stream, outlet temp, U,
                  installed area, and name are kept). Order matters for series.
    mode        : 'series' or 'parallel'.
    split_pcts  : parallel only — percent of the cold stream to each heater
                  (defaults to an equal split; must sum to 100).
    name        : display name [default 'Juice Heating Station'].

    Example::

        station = JuiceHeatingStation(
            cold_stream=st_mary_clar.limed_juice_cold_stream,
            heaters=[primary_cfg, secondary_cfg],
            mode='parallel', split_pcts=[50, 50],
        )
        station.neat_display()
        station.to_excel(wb)
    """

    def __init__(self, cold_stream: SugarStream, heaters: list,
                 mode: str = 'series', split_pcts: list = None,
                 name: str = 'Juice Heating Station'):
        mode = mode.lower()
        if mode not in ('series', 'parallel'):
            raise ValueError(f"mode must be 'series' or 'parallel', got '{mode}'")
        self.name = name
        self.mode = mode
        self.cold_stream = cold_stream
        self._heater_cfgs = heaters

        if mode == 'parallel':
            n = len(heaters)
            self.split_pcts = (split_pcts if split_pcts is not None
                               else [100.0 / n] * n)
            if len(self.split_pcts) != n:
                raise ValueError("split_pcts must have one entry per heater")
            if abs(sum(self.split_pcts) - 100.0) > 0.01:
                raise ValueError(f"split_pcts must sum to 100, got {sum(self.split_pcts)}")
        else:
            self.split_pcts = None

        self._solve()

    @staticmethod
    def _copy_steam(s):
        """Fresh SteamStream at the same conditions, so each solved heater
        stamps its steam requirement onto its OWN stream (JuiceHeater sets
        hot_stream.flow_lb_per_hr at construction)."""
        from SteamStream import SteamStream
        if s.x is not None and 0 <= s.x <= 1:
            return SteamStream(P=s.P, x=s.x)
        return SteamStream(P=s.P, T=s.T)

    def _rebuild(self, cfg: JuiceHeaterShellTube, cold: SugarStream) -> JuiceHeaterShellTube:
        return JuiceHeaterShellTube(
            cold_stream=cold,
            hot_stream=self._copy_steam(cfg.hot_stream),
            name=cfg.name,
            juice_out_temp_degF=cfg.juice_out_temp_degF,
            U_btu_per_ft2_degF=cfg.U,
            installed_area_ft2=cfg.installed_area_ft2,
        )

    def _solve(self):
        self.heaters = []
        if self.mode == 'series':
            cold = self.cold_stream
            for cfg in self._heater_cfgs:
                heater = self._rebuild(cfg, cold)
                self.heaters.append(heater)
                cold = heater.juice_out
            self.juice_out = self.heaters[-1].juice_out
        else:
            for cfg, pct in zip(self._heater_cfgs, self.split_pcts):
                split = SugarStream.copy(self.cold_stream)
                split.flow_lb_per_hr = pct / 100 * self.cold_stream.flow_lb_per_hr
                self.heaters.append(self._rebuild(cfg, split))
            # combined hot juice: total flow at the mass-weighted blend temp
            total = sum(h.juice_out.flow_lb_per_hr for h in self.heaters)
            blend = (sum(h.juice_out.flow_lb_per_hr * h.juice_out.temp_deg_F
                         for h in self.heaters) / total)
            out = SugarStream.copy(self.cold_stream)
            out.flow_lb_per_hr = total
            out.temp_deg_F = blend
            self.juice_out = out

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------

    @property
    def total_steam_lb_hr(self):
        return sum(h.steam_required_lb_per_hr for h in self.heaters)

    @property
    def total_duty_btu_hr(self):
        return sum(h.Q_btu_per_hr for h in self.heaters)

    def __repr__(self):
        return (f"JuiceHeatingStation({self.mode}, {len(self.heaters)} heaters, "
                f"juice out {self.juice_out.flow_lb_per_hr:,.0f} lb/hr @ "
                f"{self.juice_out.temp_deg_F:.1f}°F, "
                f"steam={self.total_steam_lb_hr:,.0f} lb/hr)")

    # ------------------------------------------------------------------
    # Display / export
    # ------------------------------------------------------------------

    def neat_display(self):
        W = 115
        HEAVY = "=" * W
        LIGHT = "-" * W

        print(HEAVY)
        print(f"{self.name.upper() + '  -  ' + self.mode.upper():^{W}}")
        print(HEAVY)
        if self.mode == 'parallel':
            splits = " / ".join(f"{p:.0f}%" for p in self.split_pcts)
            print(f"  Juice split: {splits}")
        print(f"  {'Heater':<24} {'Juice lb/hr':>12} {'T in F':>8} {'T out F':>8}"
              f" {'LMTD F':>8} {'Duty BTU/hr':>14} {'U':>6}"
              f" {'Req ft2':>9} {'Inst ft2':>9} {'Steam psia':>10} {'Steam lb/hr':>12}")
        print(LIGHT)
        for h in self.heaters:
            print(f"  {h.name:<24} {h.cold_stream.flow_lb_per_hr:>12,.0f}"
                  f" {h.cold_stream.temp_deg_F:>8.1f} {h.juice_out_temp_degF:>8.1f}"
                  f" {h.LMTD_degF:>8.1f} {h.Q_btu_per_hr:>14,.0f} {h.U:>6.0f}"
                  f" {h.required_area_ft2:>9,.0f} {h.installed_area_ft2:>9,.0f}"
                  f" {h.hot_stream.P:>10.1f} {h.steam_required_lb_per_hr:>12,.0f}")
        print(LIGHT)
        print(f"  {'TOTAL':<24} {'':>12} {'':>8} {'':>8} {'':>8}"
              f" {self.total_duty_btu_hr:>14,.0f} {'':>6} {'':>9} {'':>9} {'':>10}"
              f" {self.total_steam_lb_hr:>12,.0f}")
        print()
        print(f"  Hot juice out: {self.juice_out.flow_lb_per_hr:,.0f} lb/hr "
              f"@ {self.juice_out.temp_deg_F:.1f} F  "
              f"({self.juice_out.brix:.2f} Bx, {self.juice_out.purity:.1f} purity)")
        for h in self.heaters:
            if h.is_steam_hot_enough != "YES":
                print(f"  WARNING [{h.name}]: {h.is_steam_hot_enough}")
        print(HEAVY)

    def generate_pfd(self, show=True, save_path=None, include_table=True):
        """Generate the station PFD (series or parallel layout). Returns the Figure."""
        from juice_heater_diagram import plot_juice_heating_station
        return plot_juice_heating_station(self, show=show, save_path=save_path,
                                          include_table=include_table)

    def to_excel(self, workbook):
        """Write the station to its own styled sheet: the PFD (diagram only),
        the numbered stream table, and the heater performance table."""
        import matplotlib.pyplot as plt
        from excel_export import SheetWriter
        from juice_heater_diagram import _collect_streams

        sw = SheetWriter(workbook, self.name, ncols=11)
        mode_txt = f" — {self.mode.title()}" if len(self.heaters) > 1 else ""
        sw.title(f"{self.name}{mode_txt}",
                 f"{len(self.heaters)} heaters | juice out "
                 f"{self.juice_out.flow_lb_per_hr:,.0f} lb/hr @ "
                 f"{self.juice_out.temp_deg_F:.1f} °F | steam = "
                 f"{self.total_steam_lb_hr:,.0f} lb/hr")

        sw.section("PROCESS FLOW DIAGRAM")
        sw.blank()
        fig = self.generate_pfd(show=False, include_table=False)
        sw.image(fig, scale=0.55)
        plt.close(fig)

        sw.section("STREAM TABLE  (tags match the diagram)")
        sw.table(["#", "Stream", "lb/hr", "°F", "psia"],
                 _collect_streams(self),
                 fmts=["0", "@", "#,##0", "0.0", "0.0"])

        sw.section("HEATER PERFORMANCE")
        sw.table(
            ["Heater", "Juice (lb/hr)", "T in (°F)", "T out (°F)", "LMTD (°F)",
             "Duty (BTU/hr)", "U (BTU/hr·ft²·°F)", "Req Area (ft²)",
             "Inst Area (ft²)", "Steam (psia)", "Steam (lb/hr)"],
            [
                (h.name, h.cold_stream.flow_lb_per_hr, h.cold_stream.temp_deg_F,
                 h.juice_out_temp_degF, h.LMTD_degF, h.Q_btu_per_hr, h.U,
                 h.required_area_ft2, h.installed_area_ft2, h.hot_stream.P,
                 h.steam_required_lb_per_hr)
                for h in self.heaters
            ],
            fmts=["@", "#,##0", "0.0", "0.0", "0.0", "#,##0", "0.0",
                  "#,##0", "#,##0", "0.0", "#,##0"],
            totals=[("TOTAL", "", "", "", "", self.total_duty_btu_hr, "", "", "",
                     "", self.total_steam_lb_hr)],
        )
        if self.mode == 'parallel':
            splits = " / ".join(f"{p:.0f}%" for p in self.split_pcts)
            sw.row("Juice split between heaters", splits, "")
        sw.row("Hot juice out", self.juice_out.flow_lb_per_hr, "lb/hr", fmt="#,##0")
        sw.row("Hot juice temperature", self.juice_out.temp_deg_F, "°F", fmt="0.0")

        return sw.finish()


if __name__ == "__main__":
    from SteamStream import SteamStream

    juice = SugarStream(brix=15, purity=88, flow_lb_per_hr=1_400_000,
                        temp_deg_F=95, pressure_psia=14.7, level_ft=0)

    primary = JuiceHeaterShellTube(
        cold_stream=juice, hot_stream=SteamStream(x=1, P=19),
        name="Primary Heaters", juice_out_temp_degF=220,
        U_btu_per_ft2_degF=220, installed_area_ft2=8000)
    secondary = JuiceHeaterShellTube(
        cold_stream=juice, hot_stream=SteamStream(x=1, P=30),
        name="Secondary Heaters", juice_out_temp_degF=220,
        U_btu_per_ft2_degF=220, installed_area_ft2=8000)

    par = JuiceHeatingStation(cold_stream=juice, heaters=[primary, secondary],
                              mode='parallel', split_pcts=[50, 50],
                              name='Juice Heaters - Parallel')
    par.neat_display()

    ser = JuiceHeatingStation(cold_stream=juice, heaters=[primary, secondary],
                              mode='series', name='Juice Heaters - Series')
    ser.neat_display()

    # Excel export demo — both stations in one workbook
    from excel_export import new_workbook
    wb = new_workbook()
    par.to_excel(wb)
    ser.to_excel(wb)
    wb.save("juice_heating_station.xlsx")
    print("\nSaved juice_heating_station.xlsx")

    print(f'primary heaters steam flow: {par.heaters[0].hot_stream.flow_lb_per_hr:,.0f}')
    par.heaters[0].hot_stream.display_properties()
    print(f'secondary heaters steam flow: {par.heaters[1].hot_stream.flow_lb_per_hr:,.0f}')
    par.heaters[1].hot_stream.display_properties()