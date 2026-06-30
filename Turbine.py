# Steam turbine object using IAPWS97 for thermodynamic accuracy.
# Isentropic expansion to outlet pressure, corrected by isentropic efficiency.
# HP demand drives the required steam flow calculation.

from iapws import IAPWS97
from SteamStream import SteamStream

_BTU_PER_HP_HR  = 2545.0    # BTU/hr per mechanical HP
_PSIA_TO_MPA    = 0.00689476
_KJ_KG_TO_BTU_LB = 1 / 2.326
_BTU_LB_R_TO_KJ_KG_K = 4.1868


class Turbine:
    """
    Isentropic steam turbine with efficiency correction.

    inlet_steam           : SteamStream at live steam conditions
    outlet_pressure_psia  : desired exhaust (back) pressure (psia)
    isentropic_efficiency : turbine isentropic efficiency (0–1, e.g. 0.75)
    hp_demand             : mechanical power output required (HP)
                            → determines the required steam flow rate

    Thermodynamic process:
        1. Ideal:   expand isentropically (s_out = s_in) to outlet pressure → h_out_isen
        2. Actual:  h_out = h_in - η × (h_in - h_out_isen)
        3. Flow:    m_dot = hp_demand × 2545 BTU/HP-hr / (h_in - h_out)
        4. Exhaust: SteamStream(P=outlet_pressure_psia, h=h_out, flow=m_dot)
    """

    def __init__(self, inlet_steam, outlet_pressure_psia, isentropic_efficiency, hp_demand, name="Turbine", desuperheating_water_temp=212):
        if not (0 < isentropic_efficiency <= 1):
            raise ValueError(f"Isentropic efficiency must be between 0 and 1, got {isentropic_efficiency}")
        self.inlet_steam          = inlet_steam
        self.outlet_pressure_psia = outlet_pressure_psia
        self.isentropic_efficiency = isentropic_efficiency
        self.hp_demand            = hp_demand
        self.name                 = name
        self.desuperheating_water_temp = desuperheating_water_temp
    # ------------------------------------------------------------------
    # Inlet conditions
    # ------------------------------------------------------------------

    @property
    def h_in(self):
        """Inlet enthalpy (BTU/lb)."""
        return self.inlet_steam.h

    @property
    def s_in(self):
        """Inlet entropy (BTU/lb·°R)."""
        return self.inlet_steam.s

    # ------------------------------------------------------------------
    # Isentropic expansion
    # ------------------------------------------------------------------

    @property
    def h_out_isentropic(self):
        """Enthalpy after ideal isentropic expansion to outlet pressure (BTU/lb)."""
        s_si  = self.s_in * _BTU_LB_R_TO_KJ_KG_K
        P_si  = self.outlet_pressure_psia * _PSIA_TO_MPA
        state = IAPWS97(P=P_si, s=s_si)
        return state.h * _KJ_KG_TO_BTU_LB

    @property
    def h_out_actual(self):
        """Actual outlet enthalpy after applying isentropic efficiency (BTU/lb)."""
        return self.h_in - self.isentropic_efficiency * (self.h_in - self.h_out_isentropic)

    # ------------------------------------------------------------------
    # Work & flow
    # ------------------------------------------------------------------

    @property
    def work_per_lb(self):
        """Actual shaft work per lb of steam (BTU/lb)."""
        return self.h_in - self.h_out_actual

    @property
    def steam_flow_lb_hr(self):
        """Steam flow required to meet the HP demand (lb/hr)."""
        return self.hp_demand * _BTU_PER_HP_HR / self.work_per_lb

    @property
    def steam_rate(self):
        """Steam rate (lb steam / HP-hr) — standard turbine performance metric."""
        return _BTU_PER_HP_HR / self.work_per_lb

    # ------------------------------------------------------------------
    # Exhaust steam
    # ------------------------------------------------------------------

    @property
    def exhaust_steam(self):
        """
        SteamStream representing the exhaust conditions.
        Defined by outlet pressure and actual outlet enthalpy.
        Quality < 1 indicates wet steam — check exhaust.x before assuming superheated.
        """
        return SteamStream(
            P=self.outlet_pressure_psia,
            h=self.h_out_actual,
            flow_lb_per_hr=self.steam_flow_lb_hr,
        )
    
    @property
    def exhaust_available(self):
        """Steam stream to represent exhaust available after water separation if x < 1, or after desuperheating if superheated"""
        # create sat steam stream x = 1
        sat_exhaust_h = SteamStream(P=self.outlet_pressure_psia, x=1).h
        if self.exhaust_steam.h == sat_exhaust_h:
            return self.exhaust_steam.flow_lb_per_hr
        elif self.exhaust_steam.h > sat_exhaust_h:
            h_to_sat = self.exhaust_steam.h - sat_exhaust_h
            water_h = SteamStream(P=self.outlet_pressure_psia, T=self.desuperheating_water_temp).h
            btu_1_lb_water = sat_exhaust_h - water_h
            water_lb_hr = h_to_sat * self.exhaust_steam.flow_lb_per_hr / btu_1_lb_water
            return self.exhaust_steam.flow_lb_per_hr + water_lb_hr
        else:
            # so if its a saturated mix... simply do this
            return self.exhaust_steam.flow_lb_per_hr * self.exhaust_steam.x

    # ------------------------------------------------------------------
    # Dunder / display
    # ------------------------------------------------------------------

    def __repr__(self):
        return (
            f"Turbine(P_in={self.inlet_steam.P:.1f} psia → "
            f"P_out={self.outlet_pressure_psia:.1f} psia, "
            f"η={self.isentropic_efficiency:.0%}, "
            f"HP={self.hp_demand:,.0f})"
        )

    def properties(self):
        exhaust = self.exhaust_steam
        return {
            'inlet_pressure_psia':      self.inlet_steam.P,
            'inlet_temp_F':             self.inlet_steam.T,
            'inlet_enthalpy_btu_lb':    self.h_in,
            'inlet_entropy_btu_lb_R':   self.s_in,
            'outlet_pressure_psia':     self.outlet_pressure_psia,
            'outlet_temp_F':            exhaust.T,
            'outlet_enthalpy_btu_lb':   self.h_out_actual,
            'outlet_quality':           exhaust.x,
            'h_out_isentropic_btu_lb':  self.h_out_isentropic,
            'isentropic_efficiency':    self.isentropic_efficiency,
            'work_per_lb_btu':          self.work_per_lb,
            'hp_demand':                self.hp_demand,
            'steam_flow_lb_hr':         self.steam_flow_lb_hr,
            'steam_rate_lb_per_hp_hr':  self.steam_rate,
            'exhaust_available':        self.exhaust_available
        }

    def neat_display(self):
        exhaust = self.exhaust_steam
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

        title = f"TURBINE  —  {self.name.upper()}"
        print(div)
        print(f"{title:^{W}}")
        print(div)

        section("INLET CONDITIONS")
        row("Inlet Pressure",            f"{self.inlet_steam.P:,.1f} psia")
        row("Inlet Temperature",         f"{self.inlet_steam.T:,.1f} °F")
        row("Inlet Enthalpy (h_in)",     f"{self.h_in:,.2f} BTU/lb")
        row("Inlet Entropy (s_in)",      f"{self.s_in:,.4f} BTU/lb·°R")

        section("OUTLET CONDITIONS")
        row("Outlet Pressure",           f"{self.outlet_pressure_psia:,.1f} psia")
        row("Outlet Temperature",        f"{exhaust.T:,.1f} °F")
        row("Outlet Enthalpy (actual)",  f"{self.h_out_actual:,.2f} BTU/lb")
        row("Outlet Enthalpy (isen.)",   f"{self.h_out_isentropic:,.2f} BTU/lb")
        x = exhaust.x
        row("Exhaust Quality",           f"{x:.4f}" if x is not None and x < 1.0 else "Superheated")
        row("Exhaust for Process",       f"{self.exhaust_available:,.0f} lb/hr")
        if self.exhaust_available > self.exhaust_steam.flow_lb_per_hr:
            row("Desuper Heater Water",  f"{self.exhaust_available - self.exhaust_steam.flow_lb_per_hr:,.0f} lb/hr")

        section("PERFORMANCE")
        row("Isentropic Efficiency",     f"{self.isentropic_efficiency:.1%}")
        row("Work per lb Steam",         f"{self.work_per_lb:,.2f} BTU/lb")
        row("Steam Rate",                f"{self.steam_rate:,.2f} lb/HP-hr")
        row("HP Demand",                 f"{self.hp_demand:,.0f} HP")
        row("Steam Flow Required",       f"{self.steam_flow_lb_hr:,.0f} lb/hr")

        print(f"\n{div}\n")

    def display_properties(self):
        props = self.properties()
        print("Units: T(°F), P(psia), h(BTU/lb), s(BTU/lb·°R), flow(lb/hr)")
        for k, v in props.items():
            if v is not None:
                print(f"  {k:<30}: {v:,.3f}")
            else:
                print(f"  {k:<30}: ---")


if __name__ == "__main__":
    # Example: 600 psia / 750°F live steam expanding to 30 psia back pressure
    # 75% isentropic efficiency, driving a 5000 HP demand
    live_steam = SteamStream(T=750, P=600)
    turbine    = Turbine(
        inlet_steam=live_steam,
        outlet_pressure_psia=30,
        isentropic_efficiency=0.75,
        hp_demand=5000,
    )
    print(turbine)
    print()
    turbine.neat_display()
    print()
    print("Exhaust steam:")
    turbine.exhaust_steam.display_properties()
