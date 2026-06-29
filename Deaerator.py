from SteamStream import SteamStream


class Deaerator:
    """
    Deaerator energy and mass balance.

    Incoming cold water is heated to saturation at deaerator pressure by
    condensing live steam. Vent loss is applied to the steam requirement.

    Inputs
    ------
    deaerator_psig    : operating pressure (psig)
    water_in_deg_F    : temperature of incoming feedwater (°F)
    water_in_lb_hr    : mass flow of incoming feedwater (lb/hr)
    vent_pct          : steam vented to atmosphere as % of steam_in (default 1 %)
    """

    def __init__(self,
                 deaerator_psig: float = 10,
                 water_in_deg_F: float = 200,
                 water_in_lb_hr: float = 100,
                 vent_pct: float = 1.0):

        self.psia           = deaerator_psig + 14.696
        self.water_in_deg_F = water_in_deg_F
        self.water_in_lb_hr = water_in_lb_hr
        self.vent_pct       = vent_pct

    # ------------------------------------------------------------------
    # Private: thermodynamic states only (no flow) — avoids circular refs
    # ------------------------------------------------------------------

    @property
    def _steam_state(self):
        return SteamStream(x=1, P=self.psia)

    @property
    def _water_out_state(self):
        return SteamStream(x=0, P=self.psia)

    @property
    def _water_in_state(self):
        return SteamStream(x=0, T=self.water_in_deg_F)

    # ------------------------------------------------------------------
    # Energy balance
    # ------------------------------------------------------------------

    @property
    def steam_flow_lb_hr(self):
        """Steam required to heat feedwater to saturation, including vent loss (lb/hr)."""
        Q_sens = self.water_in_lb_hr * (self._water_out_state.h - self._water_in_state.h)
        steam_net = Q_sens / self._steam_state.h_fg
        return steam_net / (1 - self.vent_pct / 100)

    @property
    def vent_flow_lb_hr(self):
        """Steam vented to atmosphere (lb/hr)."""
        return self.steam_flow_lb_hr * self.vent_pct / 100

    @property
    def water_out_flow_lb_hr(self):
        """Deaerated water leaving (lb/hr) = water_in + steam condensed (no vent)."""
        return self.water_in_lb_hr + self.steam_flow_lb_hr - self.vent_flow_lb_hr

    # ------------------------------------------------------------------
    # Public streams (thermodynamic state + flow)
    # ------------------------------------------------------------------

    @property
    def steam_in(self):
        """Saturated steam entering the deaerator."""
        s = SteamStream(x=1, P=self.psia)
        s.flow_lb_per_hr = self.steam_flow_lb_hr
        return s

    @property
    def water_in(self):
        """Incoming feedwater stream."""
        s = SteamStream(x=0, T=self.water_in_deg_F)
        s.flow_lb_per_hr = self.water_in_lb_hr
        return s

    @property
    def water_out(self):
        """Deaerated water leaving at saturation temperature."""
        s = SteamStream(x=0, P=self.psia)
        s.flow_lb_per_hr = self.water_out_flow_lb_hr
        return s

    @property
    def vent(self):
        """Vented steam stream."""
        s = SteamStream(x=1, P=14.696)
        s.flow_lb_per_hr = self.vent_flow_lb_hr
        return s

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __repr__(self):
        return (f"Deaerator(P={self.psia:.2f} psia, T_sat={self._water_out_state.T:.1f}°F, "
                f"water_in={self.water_in_lb_hr:,.0f} lb/hr @ {self.water_in_deg_F:.0f}°F, "
                f"vent={self.vent_pct:.1f}%)")

    def display_properties(self):
        w = 45
        print(f"\n{'=' * 59}")
        print(f"  Deaerator  |  {self.psia:.2f} psia  |  "
              f"T_sat = {self._water_out_state.T:.1f} degF")
        print(f"{'=' * 59}")

        def row(label, value, unit=""):
            print(f"  {label:<{w}} {value:>12,.2f}  {unit}")

        print("\n  ENTERING")
        row("Feedwater flow",         self.water_in_lb_hr,       "lb/hr")
        row("Feedwater temperature",  self.water_in_deg_F,       "degF")
        row("Feedwater enthalpy",     self._water_in_state.h,    "BTU/lb")
        row("Steam flow (total)",     self.steam_flow_lb_hr,     "lb/hr")
        row("Steam enthalpy",         self._steam_state.h,       "BTU/lb")
        row("Steam h_fg",             self._steam_state.h_fg,    "BTU/lb")

        print("\n  LEAVING")
        row("Deaerated water flow",   self.water_out_flow_lb_hr, "lb/hr")
        row("Water out temperature",  self._water_out_state.T,   "degF")
        row("Water out enthalpy",     self._water_out_state.h,   "BTU/lb")
        row("Vent flow",              self.vent_flow_lb_hr,      "lb/hr")
        row("Vent pct",               self.vent_pct,             "%")

        net = (self.water_in_lb_hr + self.steam_flow_lb_hr
               - self.water_out_flow_lb_hr - self.vent_flow_lb_hr)
        print(f"\n  {'Net (In - Out):':<{w}} {net:>12,.4f}  lb/hr")
        print(f"{'=' * 59}\n")


if __name__ == "__main__":
    da = Deaerator(deaerator_psig=10, water_in_deg_F=205, water_in_lb_hr=100_000, vent_pct=5.0)
    print(da)
    da.display_properties()
