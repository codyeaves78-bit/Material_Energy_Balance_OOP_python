# script to control the Juice Heater Objects
from SugarStream import SugarStream
from SteamStream import SteamStream
import numpy as np


class JuiceHeaterShellTube:
    """Class to represent shell and tube juice heater"""

    def __init__(
        self,
        cold_stream        : SugarStream,
        hot_stream         : SteamStream,
        name               : str   = "Heater",
        juice_out_temp_degF: float = 220,
        U_btu_per_ft2_degF : float = 220,
        installed_area_ft2 : float = 22_000,
        steam_type         : int   = 0, # 0 = Exh,  1 = V1,  2 = V2,  3 = V3,  4 = V4
    ):
        self.name               = name
        self.U                  = U_btu_per_ft2_degF
        self.cold_stream        = cold_stream
        self.hot_stream         = hot_stream
        self.juice_out_temp_degF = juice_out_temp_degF
        self.installed_area_ft2 = installed_area_ft2
        self.steam_type         = steam_type # 0 = Exh,  1 = V1,  2 = V2,  3 = V3,  4 = V4

        self.juice_out = SugarStream(
            self.cold_stream.brix,
            self.cold_stream.purity,
            self.cold_stream.flow_lb_per_hr,
            self.juice_out_temp_degF, # updated temp
            self.cold_stream.pressure_psia,
            self.cold_stream.level_ft,
        )

        # Stamp the required steam flow onto the supply stream so downstream
        # code can read hot_stream.flow_lb_per_hr directly. NOTE: if one
        # SteamStream object is shared by several heaters, the last heater
        # constructed wins — give each heater its own SteamStream.
        self.hot_stream.flow_lb_per_hr = self.steam_required_lb_per_hr

    # ------------------------------------------------------------------ #
    #  Properties                                                          #
    # ------------------------------------------------------------------ #

    @property
    def cold_delta_T(self):
        """Juice temperature rise"""
        return self.juice_out_temp_degF - self.cold_stream.temp_deg_F

    @property
    def Q_btu_per_hr(self):
        """Heat transfer rate (BTU/hr)"""
        return self.cold_stream.flow_lb_per_hr * self.cold_stream.cp_btu_per_lb_deg_F * self.cold_delta_T

    @property
    def LMTD_degF(self):
        """Log mean temperature difference (°F)"""
        delta_T1 = self.hot_stream.T - self.cold_stream.temp_deg_F
        delta_T2 = self.hot_stream.T - self.juice_out_temp_degF
        if delta_T1 == delta_T2:
            return delta_T1
        return (delta_T1 - delta_T2) / np.log(delta_T1 / delta_T2)

    @property
    def required_area_ft2(self):
        """Required heat transfer area (ft²)"""
        return self.Q_btu_per_hr / (self.U * self.LMTD_degF)

    @property
    def steam_required_lb_per_hr(self):
        """Required steam flow rate (lb/hr)"""
        return self.Q_btu_per_hr / self.hot_stream.h_fg

    @property
    def is_steam_hot_enough(self):
        """Check whether steam is hot enough to reach the target juice outlet temperature"""
        if self.hot_stream.T <= self.juice_out_temp_degF:
            return f"NO! Steam temp ({self.hot_stream.T:.2f} °F) <= juice out temperature ({self.juice_out_temp_degF} °F)."
        return "YES"

    # ------------------------------------------------------------------ #
    #  Display methods                                                     #
    # ------------------------------------------------------------------ #

    def properties(self) -> dict:
        cls        = type(self)
        prop_names = [k for k, v in vars(cls).items() if isinstance(v, property)]
        inst_vars  = {k: v for k, v in vars(self).items() if not k.startswith("_")}
        return {**inst_vars, **{k: getattr(self, k) for k in prop_names}}

    def neat_display(self):
        """Display heater parameters and results in a formatted table."""
        W  = 62
        C1 = 38
        C2 = 20
        div  = "=" * W
        sdiv = "-" * W

        def row(label, value):
            print(f"  {label:<{C1}}{value:>{C2}}")

        def section(title):
            print(f"\n  {title}")
            print(sdiv)

        title = f"JUICE HEATER  —  {self.name.upper()}"
        print(div)
        print(f"{title:^{W}}")
        print(div)

        section("DESIGN PARAMETERS")
        row("Overall HT Coeff. (U)",       f"{self.U:,.1f} BTU/ft²·°F")
        row("Juice Outlet Temperature",     f"{self.juice_out_temp_degF:,.1f} °F")
        row("Installed Area",               f"{self.installed_area_ft2:,.0f} ft²")

        section("INLET CONDITIONS")
        row("Juice Inlet Temperature",      f"{self.cold_stream.temp_deg_F:,.1f} °F")
        row("Juice Flow Rate",              f"{self.cold_stream.flow_lb_per_hr:,.0f} lb/hr")
        row("Juice Brix",                   f"{self.cold_stream.brix:.1f} °Bx")
        row("Juice Purity",                 f"{self.cold_stream.purity:.1f} %")
        row("Steam Temperature",            f"{self.hot_stream.T:,.1f} °F")

        section("HEAT TRANSFER RESULTS")
        row("Juice Temperature Rise (ΔT)",  f"{self.cold_delta_T:,.1f} °F")
        row("LMTD",                         f"{self.LMTD_degF:,.1f} °F")
        row("Heat Duty (Q)",                f"{self.Q_btu_per_hr:,.0f} BTU/hr")
        row("Required Area",                f"{self.required_area_ft2:,.0f} ft²")
        row("Steam Required",               f"{self.steam_required_lb_per_hr:,.0f} lb/hr")
        row("Steam Hot Enough?",            self.is_steam_hot_enough)

        print(f"\n{div}\n")

    def display_properties(self):
        """Display all properties in a simple key: value format"""
        props = self.properties()
        for key, value in props.items():
            formatted = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
            print(f"{key}: {formatted}")

    # ------------------------------------------------------------------ #
    #  PFD / Excel export (reuses JuiceHeatingStation with one heater)     #
    # ------------------------------------------------------------------ #

    def _as_station(self):
        """Wrap this heater in a one-unit JuiceHeatingStation so the PFD and
        Excel machinery can be reused (lazy import avoids the circular one)."""
        from JuiceHeatingStation import JuiceHeatingStation
        return JuiceHeatingStation(cold_stream=self.cold_stream, heaters=[self],
                                   mode='series', name=self.name)

    def generate_pfd(self, show=True, save_path=None, include_table=True):
        """Generate a single-heater PFD. Returns the matplotlib Figure."""
        return self._as_station().generate_pfd(show=show, save_path=save_path,
                                               include_table=include_table)

    def to_excel(self, workbook):
        """Write this heater to its own styled sheet (PFD + stream and
        performance tables)."""
        return self._as_station().to_excel(workbook)


if __name__ == "__main__":
    # Clarified juice heater example (like main.py) + Excel export demo
    clar_juice = SugarStream(brix=14.6, purity=88.5, flow_lb_per_hr=1_390_000,
                             temp_deg_F=205, pressure_psia=14.7, level_ft=0)
    heater = JuiceHeaterShellTube(
        cold_stream=clar_juice,
        hot_stream=SteamStream(x=1, P=30),
        name="Clarified Juice Heater",
        juice_out_temp_degF=225,
        U_btu_per_ft2_degF=185,
        installed_area_ft2=6000,
    )
    heater.neat_display()
    # heater.generate_pfd(show=True, save_path=None)

    from excel_export import new_workbook
    wb = new_workbook()
    heater.to_excel(wb)
    wb.save("juice_heater.xlsx")
    print("Saved juice_heater.xlsx")
