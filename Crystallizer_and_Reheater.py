# Water-cooled crystallizer and hot-water reheater for low-grade (C) massecuite.
# Both are non-contact heat exchangers: cooling/heating water never mixes with the
# massecuite, so massecuite mass flow is conserved through each unit.
# Heat balance is sensible-heat only — heat of crystallization of sucrose is small
# and neglected here.

from Massecuite import Massecuite

_CP_WATER        = 1.0    # BTU/lb·°F
_LB_PER_GAL_H2O  = 8.34   # lb per US gallon of water


class Crystallizer:
    """
    Water-cooled crystallizer — cools and exhausts massecuite after the pan.

    massecuite_in         : Massecuite leaving the pan (boiling or set-temperature mode)
    massecuite_flow_lb_hr : massecuite flow (lb/hr) — pass pan.massecuite_flow_lb_hr
    masse_temp_out_deg_F  : target massecuite outlet temperature (°F)
    ml_purity_out         : mother liquor purity after exhaustion (crystal growth
                            during cooling) — None means no purity drop
    water_temp_in_deg_F   : cooling water supply temperature (°F)
    water_temp_out_deg_F  : cooling water return temperature (°F) — must exceed supply

    Heat balance (sensible only):
        Q            = flow × cp(masse_brix) × (T_in − T_out)
        water_lb_hr  = Q / (cp_water × (Tw_out − Tw_in))

    massecuite_out is a set-temperature-mode Massecuite ready to feed the reheater
    or centrifugal; its lower ml_purity carries the exhaustion downstream.
    """

    def __init__(self, massecuite_in: Massecuite, massecuite_flow_lb_hr: float,
                 masse_temp_out_deg_F: float = 120.0, ml_purity_out: float = None,
                 water_temp_in_deg_F: float = 85.0, water_temp_out_deg_F: float = 105.0,
                 name: str = 'Crystallizer'):
        if water_temp_out_deg_F <= water_temp_in_deg_F:
            raise ValueError(
                f"Cooling water must leave hotter than it enters "
                f"({water_temp_in_deg_F}→{water_temp_out_deg_F}°F)."
            )
        self.massecuite_in         = massecuite_in
        self.massecuite_flow_lb_hr = massecuite_flow_lb_hr
        self.masse_temp_out_deg_F  = masse_temp_out_deg_F
        self.ml_purity_out         = ml_purity_out
        self.water_temp_in_deg_F   = water_temp_in_deg_F
        self.water_temp_out_deg_F  = water_temp_out_deg_F
        self.name                  = name

    # ------------------------------------------------------------------
    # Massecuite side
    # ------------------------------------------------------------------

    @property
    def masse_temp_in_deg_F(self):
        return self.massecuite_in.massecuite_temp

    @property
    def massecuite_out(self) -> Massecuite:
        """Cooled, exhausted massecuite (set-temperature mode)."""
        ml_out = (self.ml_purity_out if self.ml_purity_out is not None
                  else self.massecuite_in.ml_purity)
        return self.massecuite_in.copy(temp_F=self.masse_temp_out_deg_F,
                                       ml_purity=ml_out)

    @property
    def crystal_growth_lb_hr(self):
        """Crystal grown across the unit from the ml purity drop (lb/hr)."""
        delta_pct = (self.massecuite_out.crystal_content
                     - self.massecuite_in.crystal_content)
        return self.massecuite_flow_lb_hr * delta_pct / 100.0

    # ------------------------------------------------------------------
    # Heat balance / cooling water
    # ------------------------------------------------------------------

    @property
    def duty_btu_hr(self):
        """Heat removed from the massecuite (BTU/hr), sensible only."""
        dT = self.masse_temp_in_deg_F - self.masse_temp_out_deg_F
        if dT <= 0:
            raise ValueError(
                f"Crystallizer outlet ({self.masse_temp_out_deg_F}°F) must be cooler "
                f"than the inlet massecuite ({self.masse_temp_in_deg_F:.1f}°F)."
            )
        return self.massecuite_flow_lb_hr * self.massecuite_in.specific_heat * dT

    @property
    def water_lb_hr(self):
        return self.duty_btu_hr / (_CP_WATER * (self.water_temp_out_deg_F
                                                - self.water_temp_in_deg_F))

    @property
    def water_gpm(self):
        return self.water_lb_hr / (_LB_PER_GAL_H2O * 60)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __repr__(self):
        return (f"Crystallizer(name='{self.name}', "
                f"masse_temp_out_deg_F={self.masse_temp_out_deg_F}, "
                f"ml_purity_out={self.ml_purity_out}, "
                f"water {self.water_temp_in_deg_F}→{self.water_temp_out_deg_F}°F)")

    def properties(self):
        return {
            'masse_flow_lb_hr':       self.massecuite_flow_lb_hr,
            'masse_temp_in_F':        self.masse_temp_in_deg_F,
            'masse_temp_out_F':       self.masse_temp_out_deg_F,
            'ml_purity_in':           self.massecuite_in.ml_purity,
            'ml_purity_out':          self.massecuite_out.ml_purity,
            'crystal_content_in_pct': self.massecuite_in.crystal_content,
            'crystal_content_out_pct': self.massecuite_out.crystal_content,
            'crystal_growth_lb_hr':   self.crystal_growth_lb_hr,
            'duty_btu_hr':            self.duty_btu_hr,
            'water_temp_in_F':        self.water_temp_in_deg_F,
            'water_temp_out_F':       self.water_temp_out_deg_F,
            'water_lb_hr':            self.water_lb_hr,
            'water_gpm':              self.water_gpm,
        }

    def neat_display(self):
        print(f"=== {self.name} ===")
        p = self.properties()
        print(f"  Massecuite : {p['masse_flow_lb_hr']:,.0f} lb/hr, "
              f"{p['masse_temp_in_F']:.1f} → {p['masse_temp_out_F']:.1f} °F")
        print(f"  ML purity  : {p['ml_purity_in']:.1f} → {p['ml_purity_out']:.1f} %   "
              f"crystal content {p['crystal_content_in_pct']:.1f} → "
              f"{p['crystal_content_out_pct']:.1f} %  "
              f"(+{p['crystal_growth_lb_hr']:,.0f} lb/hr crystal)")
        print(f"  Duty       : {p['duty_btu_hr']:,.0f} BTU/hr removed")
        print(f"  Cooling water: {p['water_lb_hr']:,.0f} lb/hr ({p['water_gpm']:,.0f} gpm), "
              f"{p['water_temp_in_F']:.0f} → {p['water_temp_out_F']:.0f} °F")


class Reheater:
    """
    Hot-water massecuite reheater — warms the cooled massecuite back up before the
    centrifugals to cut viscosity. Hot water (not steam) avoids local overheating
    that would dissolve crystal, so ml purity is assumed unchanged by default.

    massecuite_in         : Massecuite from the crystallizer (set-temperature mode)
    massecuite_flow_lb_hr : massecuite flow (lb/hr)
    masse_temp_out_deg_F  : target massecuite outlet temperature (°F)
    ml_purity_out         : optional ml purity out — set slightly above the inlet
                            to model crystal redissolution; None means unchanged
    water_temp_in_deg_F   : hot water supply temperature (°F) — must exceed return
    water_temp_out_deg_F  : hot water return temperature (°F)

    Heat balance (sensible only):
        Q            = flow × cp(masse_brix) × (T_out − T_in)
        water_lb_hr  = Q / (cp_water × (Tw_in − Tw_out))
    """

    def __init__(self, massecuite_in: Massecuite, massecuite_flow_lb_hr: float,
                 masse_temp_out_deg_F: float = 130.0, ml_purity_out: float = None,
                 water_temp_in_deg_F: float = 150.0, water_temp_out_deg_F: float = 135.0,
                 name: str = 'Reheater'):
        if water_temp_in_deg_F <= water_temp_out_deg_F:
            raise ValueError(
                f"Heating water must enter hotter than it leaves "
                f"({water_temp_in_deg_F}→{water_temp_out_deg_F}°F)."
            )
        self.massecuite_in         = massecuite_in
        self.massecuite_flow_lb_hr = massecuite_flow_lb_hr
        self.masse_temp_out_deg_F  = masse_temp_out_deg_F
        self.ml_purity_out         = ml_purity_out
        self.water_temp_in_deg_F   = water_temp_in_deg_F
        self.water_temp_out_deg_F  = water_temp_out_deg_F
        self.name                  = name

    # ------------------------------------------------------------------
    # Massecuite side
    # ------------------------------------------------------------------

    @property
    def masse_temp_in_deg_F(self):
        return self.massecuite_in.massecuite_temp

    @property
    def massecuite_out(self) -> Massecuite:
        """Reheated massecuite (set-temperature mode) — feed to the centrifugals."""
        ml_out = (self.ml_purity_out if self.ml_purity_out is not None
                  else self.massecuite_in.ml_purity)
        return self.massecuite_in.copy(temp_F=self.masse_temp_out_deg_F,
                                       ml_purity=ml_out)

    # ------------------------------------------------------------------
    # Heat balance / heating water
    # ------------------------------------------------------------------

    @property
    def duty_btu_hr(self):
        """Heat added to the massecuite (BTU/hr), sensible only."""
        dT = self.masse_temp_out_deg_F - self.masse_temp_in_deg_F
        if dT <= 0:
            raise ValueError(
                f"Reheater outlet ({self.masse_temp_out_deg_F}°F) must be hotter "
                f"than the inlet massecuite ({self.masse_temp_in_deg_F:.1f}°F)."
            )
        return self.massecuite_flow_lb_hr * self.massecuite_in.specific_heat * dT

    @property
    def water_lb_hr(self):
        return self.duty_btu_hr / (_CP_WATER * (self.water_temp_in_deg_F
                                                - self.water_temp_out_deg_F))

    @property
    def water_gpm(self):
        return self.water_lb_hr / (_LB_PER_GAL_H2O * 60)

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def __repr__(self):
        return (f"Reheater(name='{self.name}', "
                f"masse_temp_out_deg_F={self.masse_temp_out_deg_F}, "
                f"water {self.water_temp_in_deg_F}→{self.water_temp_out_deg_F}°F)")

    def properties(self):
        return {
            'masse_flow_lb_hr':  self.massecuite_flow_lb_hr,
            'masse_temp_in_F':   self.masse_temp_in_deg_F,
            'masse_temp_out_F':  self.masse_temp_out_deg_F,
            'ml_purity_out':     self.massecuite_out.ml_purity,
            'duty_btu_hr':       self.duty_btu_hr,
            'water_temp_in_F':   self.water_temp_in_deg_F,
            'water_temp_out_F':  self.water_temp_out_deg_F,
            'water_lb_hr':       self.water_lb_hr,
            'water_gpm':         self.water_gpm,
        }

    def neat_display(self):
        print(f"=== {self.name} ===")
        p = self.properties()
        print(f"  Massecuite : {p['masse_flow_lb_hr']:,.0f} lb/hr, "
              f"{p['masse_temp_in_F']:.1f} → {p['masse_temp_out_F']:.1f} °F")
        print(f"  Duty       : {p['duty_btu_hr']:,.0f} BTU/hr added")
        print(f"  Hot water  : {p['water_lb_hr']:,.0f} lb/hr ({p['water_gpm']:,.0f} gpm), "
              f"{p['water_temp_in_F']:.0f} → {p['water_temp_out_F']:.0f} °F")


if __name__ == "__main__":
    # C massecuite drops from the pan, cools + exhausts in the crystallizer,
    # reheats before the fugals.
    c_masse = Massecuite(ml_purity=33, masse_purity=54, masse_brix=95.5,
                         inches_vacuum=26.5, supersaturation=1.2, head_ft=2)
    flow = 100_000

    crys = Crystallizer(c_masse, flow,
                        masse_temp_out_deg_F=120, ml_purity_out=30,
                        water_temp_in_deg_F=85, water_temp_out_deg_F=105,
                        name='C Crystallizer')
    crys.neat_display()
    print()

    reheat = Reheater(crys.massecuite_out, flow,
                      masse_temp_out_deg_F=130,
                      water_temp_in_deg_F=150, water_temp_out_deg_F=135,
                      name='C Reheater')
    reheat.neat_display()
    print()
    print("To centrifugal:", reheat.massecuite_out)
