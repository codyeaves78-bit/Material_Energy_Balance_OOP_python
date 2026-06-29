# Barometric condenser object for vacuum pan / evaporator systems.
# Energy balance assumes outlet water reaches vapor saturation temperature.
# Cp of water taken as 1.0 BTU/(lb·°F) — accurate to <0.2% in the typical range.

from SteamStream import EvaporatorSteam


class Condenser:
    """
    Barometric condenser — condenses incoming vapor with cold injection water.

    vapor             : EvaporatorSteam or SteamStream with flow_lb_per_hr set
    water_inlet_temp_F: temperature of the injection water supply (°F)

    Assumption: outlet water/condensate mixture leaves at the vapor saturation
    temperature (perfect mixing, no sub-cooling).

    Energy balance:
        m_vap × h_fg  =  m_water × Cp × (T_sat - T_water_in)
        m_water = m_vap × h_fg / (T_sat - T_water_in)        [Cp = 1.0 BTU/lb·°F]
    """

    _CP_WATER = 1.0  # BTU / (lb·°F)

    def __init__(self, vapor, water_inlet_temp_F):
        self.vapor = vapor
        self.water_inlet_temp_F = water_inlet_temp_F

    # ------------------------------------------------------------------
    # Vapor properties (supports both EvaporatorSteam and SteamStream)
    # ------------------------------------------------------------------

    @property
    def vapor_sat_temp_F(self):
        """Saturation temperature of the incoming vapor (°F)."""
        if hasattr(self.vapor, 'sat_temp_deg_F'):
            return self.vapor.sat_temp_deg_F   # EvaporatorSteam
        return self.vapor.T                     # SteamStream at sat. conditions

    @property
    def vapor_flow_lb_hr(self):
        return self.vapor.flow_lb_per_hr

    @property
    def vapor_h_fg_btu_lb(self):
        return self.vapor.h_fg

    # ------------------------------------------------------------------
    # Energy & mass balance
    # ------------------------------------------------------------------

    @property
    def heat_load_btu_hr(self):
        """Total heat removed from the vapor (BTU/hr)."""
        return self.vapor_flow_lb_hr * self.vapor_h_fg_btu_lb

    @property
    def water_outlet_temp_F(self):
        """Outlet temperature of the water/condensate mixture (°F)."""
        return self.vapor_sat_temp_F

    @property
    def injection_water_flow_lb_hr(self):
        """Injection water required to condense the vapor (lb/hr)."""
        delta_T = self.vapor_sat_temp_F - self.water_inlet_temp_F
        if delta_T < 0:
            raise ValueError(
                f"Injection water inlet ({self.water_inlet_temp_F}°F) must be "
                f"below vapor saturation temp ({self.vapor_sat_temp_F:.2f}°F)."
            )
        return self.heat_load_btu_hr / (self._CP_WATER * delta_T)

    @property
    def total_outlet_flow_lb_hr(self):
        """Total flow leaving the condenser — condensate + injection water (lb/hr)."""
        return self.injection_water_flow_lb_hr + self.vapor_flow_lb_hr

    # ------------------------------------------------------------------
    # Dunder / display
    # ------------------------------------------------------------------

    def __repr__(self):
        return (f"Condenser(vapor_sat_temp={self.vapor_sat_temp_F:.1f}°F, "
                f"water_inlet={self.water_inlet_temp_F}°F, "
                f"vapor_flow={self.vapor_flow_lb_hr:,.0f} lb/hr)")

    def properties(self):
        return {
            'vapor_sat_temp_F':          self.vapor_sat_temp_F,
            'vapor_h_fg_btu_lb':         self.vapor_h_fg_btu_lb,
            'vapor_flow_lb_hr':          self.vapor_flow_lb_hr,
            'heat_load_btu_hr':          self.heat_load_btu_hr,
            'water_inlet_temp_F':        self.water_inlet_temp_F,
            'water_outlet_temp_F':       self.water_outlet_temp_F,
            'injection_water_flow_lb_hr': self.injection_water_flow_lb_hr,
            'total_outlet_flow_lb_hr':   self.total_outlet_flow_lb_hr,
        }

    def display_properties(self):
        props = self.properties()
        print("Units: T(°F), flow(lb/hr), h_fg(BTU/lb), heat_load(BTU/hr)")
        for k, v in props.items():
            print(f"  {k:<30}: {v:,.2f}")


if __name__ == "__main__":
    # Example: 50,000 lb/hr of vapor at 26.5 in Hg vacuum, 75°F injection water
    vapor = EvaporatorSteam(P_psia=14.696 - 26.5 * 0.491154, flow_lb_per_hr=50_000)
    cond  = Condenser(vapor, water_inlet_temp_F=75)
    print(cond)
    print()
    cond.display_properties()
