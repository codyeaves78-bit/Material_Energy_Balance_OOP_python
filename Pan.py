# Vacuum pan — complete material and energy balance.
# Massecuite purity is derived from the feed stream pol/solids balance (not specified directly).
# The Massecuite object is built internally once purity is known.
# Heating steam is selected from standard Louisiana steam types (Exhaust, V1–V4).
# calandria_steam_temp_F defaults to the standard T_sat for the chosen type but can be
# overridden at any time — either for a single-pass U refinement or a future nested loop.

from SteamStream import EvaporatorSteam
from Massecuite import Massecuite


class Pan:
    """
    Vacuum pan material and energy balance.

    feed_streams           : SugarStream or list of SugarStreams entering the pan
                             (syrup, footing, seed remelt, etc.)
    heating_surface_ft2    : calandria heating area (ft²)
    inches_vacuum          : pan vapor space vacuum (in Hg)
    supersaturation        : target supersaturation coefficient (e.g. 1.1)
    head_ft                : massecuite depth in the pan (ft)
    masse_brix             : target massecuite outlet Brix
    ml_purity              : mother liquor apparent purity
    steam_type             : one of 'Exhaust', 'V1', 'V2', 'V3', 'V4'
                             Selects standard h_fg and default calandria T from STEAM_CONDITIONS.
    calandria_steam_temp_F : override for calandria saturation temperature (°F).
                             If None (default), uses STEAM_CONDITIONS[steam_type]['T_sat_F'].
                             Set this to the real measured/calculated steam temp for a
                             more accurate U back-calculation after the evaporator solve.

    Massecuite apparent purity is computed from the feed pol/solids balance:
        masse_purity = Σ(flow_i × purity_i × brix_i) / Σ(flow_i × brix_i)

    Solve order:
        1. Pol/solids balance     →  masse_purity, feed_solids_lb_hr
        2. Massecuite object      →  T_massecuite, vapor_pressure, BPR
        3. Material balance       →  massecuite_flow_lb_hr, water_evaporated_lb_hr
        4. Energy balance         →  Q = Q_sensible + Q_latent  (h_fg at vapor-space pressure)
        5. Steam consumption      →  steam_flow = Q / h_fg_calandria  (standard h_fg for steam_type)
        6. Back-calculate         →  U = Q / (A × ΔT)
    """

    # Standard Louisiana steam conditions.
    # h_fg values are fixed for steam consumption calculations — variation from actual
    # conditions is < 1% within each type's realistic operating range.
    # Pressures listed for reference; T_sat and h_fg were computed from IAPWS-97.
    # To adapt for other regions or cogen mills, adjust P_psia entries here.
    STEAM_CONDITIONS = {
        'Exhaust': {'P_psia': 29.696, 'T_sat_F': 249.7, 'h_fg': 945.7},  # 15 psig
        'V1':      {'P_psia': 21.696, 'T_sat_F': 232.3, 'h_fg': 957.1},  # 7 psig
        'V2':      {'P_psia': 14.696, 'T_sat_F': 212.0, 'h_fg': 970.0},  # 0 psig (atm)
        'V3':      {'P_psia': 10.276, 'T_sat_F': 194.4, 'h_fg': 980.9},  # ~9 in Hg vac
        'V4':      {'P_psia':  3.399, 'T_sat_F': 146.3, 'h_fg': 1009.5}, # ~23 in Hg vac
    }

    def __init__(self, feed_streams, heating_surface_ft2,
                 inches_vacuum, supersaturation, head_ft,
                 masse_brix, ml_purity,
                 steam_type='V1',
                 calandria_steam_temp_F=None,
                 heat_loss_factor=0.0):
        if steam_type not in self.STEAM_CONDITIONS:
            raise ValueError(
                f"steam_type '{steam_type}' is not valid. "
                f"Choose from: {list(self.STEAM_CONDITIONS)}"
            )
        self.feed_streams        = (feed_streams if isinstance(feed_streams, list)
                                    else [feed_streams])
        self.heating_surface_ft2 = heating_surface_ft2
        self.inches_vacuum       = inches_vacuum
        self.supersaturation     = supersaturation
        self.head_ft             = head_ft
        self.masse_brix          = masse_brix
        self.ml_purity           = ml_purity
        self.steam_type          = steam_type
        self.heat_loss_factor    = heat_loss_factor

        # Default calandria temp from standard table; override any time for U refinement
        self.calandria_steam_temp_F = (calandria_steam_temp_F
                                       if calandria_steam_temp_F is not None
                                       else self.STEAM_CONDITIONS[steam_type]['T_sat_F'])

        # Build the Massecuite using the pol/solids-derived purity
        self.massecuite = Massecuite(
            ml_purity=ml_purity,
            masse_purity=self.masse_purity,
            masse_brix=masse_brix,
            inches_vacuum=inches_vacuum,
            supersaturation=supersaturation,
            head_ft=head_ft,
        )

    # ------------------------------------------------------------------
    # Calandria steam (from standard table)
    # ------------------------------------------------------------------

    @property
    def h_fg_calandria(self):
        """Standard latent heat of the heating steam (BTU/lb) — from STEAM_CONDITIONS table.
        Used for steam consumption: steam_flow = Q / h_fg_calandria.
        Fixed per steam type; < 1% error vs actual operating conditions.
        """
        return self.STEAM_CONDITIONS[self.steam_type]['h_fg']

    @property
    def calandria_steam_pressure_psia(self):
        """Standard pressure for the selected steam type (psia) — reference only."""
        return self.STEAM_CONDITIONS[self.steam_type]['P_psia']

    # ------------------------------------------------------------------
    # Feed-side helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _cp_sugar(brix):
        """Specific heat of a sugar solution (BTU/lb·°F) — linear Brix approximation."""
        return 1.0 - 0.006 * brix

    @property
    def feed_flow_lb_hr(self):
        """Total inlet flow — sum of all feed streams (lb/hr)."""
        return sum(f.flow_lb_per_hr for f in self.feed_streams)

    @property
    def feed_solids_lb_hr(self):
        """Total dissolved solids entering the pan (lb/hr)."""
        return sum(f.flow_lb_per_hr * f.brix / 100 for f in self.feed_streams)

    @property
    def feed_temp_F(self):
        """Flow-weighted average temperature of all feed streams (°F)."""
        return (sum(f.flow_lb_per_hr * f.temp_deg_F for f in self.feed_streams)
                / self.feed_flow_lb_hr)

    @property
    def masse_purity(self):
        """Massecuite apparent purity from feed pol/solids balance:
        P = Σ(flow × purity × brix) / Σ(flow × brix)
        """
        total_pol    = sum(f.flow_lb_per_hr * f.purity * f.brix / 10000
                           for f in self.feed_streams)
        total_solids = self.feed_solids_lb_hr
        return total_pol / total_solids * 100

    @property
    def cp_massecuite(self):
        """Cp used for the sensible heat term (BTU/lb·°F)."""
        return self._cp_sugar(self.masse_brix)

    # ------------------------------------------------------------------
    # Material balance
    # ------------------------------------------------------------------

    @property
    def massecuite_flow_lb_hr(self):
        """Massecuite outlet flow from solids balance: feed_solids / (masse_brix / 100) (lb/hr)."""
        return self.feed_solids_lb_hr / (self.masse_brix / 100)

    @property
    def water_evaporated_lb_hr(self):
        """Water removed by boiling: total feed minus massecuite out (lb/hr)."""
        return self.feed_flow_lb_hr - self.massecuite_flow_lb_hr

    # ------------------------------------------------------------------
    # Energy balance  (h_fg here is at vapor-space pressure, not calandria)
    # ------------------------------------------------------------------

    @property
    def h_fg_vapor(self):
        """Latent heat of vaporization at the pan vapor-space pressure (BTU/lb)."""
        return EvaporatorSteam(self.massecuite.vapor_pressure_psia).h_fg

    @property
    def heat_sensible_btu_hr(self):
        """Sensible heat to raise the feed to the massecuite boiling point (BTU/hr)."""
        return (self.feed_flow_lb_hr * self.cp_massecuite
                * (self.massecuite.massecuite_temp - self.feed_temp_F))

    @property
    def heat_evaporation_btu_hr(self):
        """Latent heat carried away by evaporated water (BTU/hr)."""
        return self.water_evaporated_lb_hr * self.h_fg_vapor

    @property
    def heat_loss_btu_hr(self):
        """Radiation and convection losses from the pan body (BTU/hr)."""
        return (self.heat_sensible_btu_hr + self.heat_evaporation_btu_hr) * self.heat_loss_factor

    @property
    def heat_transfer_btu_hr(self):
        """Total calandria duty  Q = Q_sensible + Q_latent + Q_loss (BTU/hr)."""
        return self.heat_sensible_btu_hr + self.heat_evaporation_btu_hr + self.heat_loss_btu_hr

    # ------------------------------------------------------------------
    # Steam consumption  (h_fg here is the calandria-side standard value)
    # ------------------------------------------------------------------

    @property
    def steam_flow_lb_hr(self):
        """Steam consumed by the calandria: Q / h_fg_calandria (lb/hr).
        Uses the standard table h_fg for the selected steam_type — accurate to < 1%
        without requiring knowledge of the actual header pressure.
        """
        return self.heat_transfer_btu_hr / self.h_fg_calandria

    @property
    def steam_to_evaporation_ratio(self):
        """lb steam consumed per lb water evaporated — compare directly to Birkett (A=1.15, C=1.25)."""
        return self.steam_flow_lb_hr / self.water_evaporated_lb_hr

    # ------------------------------------------------------------------
    # Back-calculated heat transfer coefficient
    # ------------------------------------------------------------------

    @property
    def delta_T(self):
        """Driving force: T_calandria − T_massecuite (°F)."""
        dT = self.calandria_steam_temp_F - self.massecuite.massecuite_temp
        if dT <= 0:
            raise ValueError(
                f"Calandria steam ({self.calandria_steam_temp_F:.1f}°F) must exceed "
                f"massecuite boiling point ({self.massecuite.massecuite_temp:.1f}°F)."
            )
        return dT

    @property
    def U_btu_hr_ft2_F(self):
        """Overall HTC back-calculated: U = Q / (A × ΔT) (BTU/hr·ft²·°F).
        Refine by setting calandria_steam_temp_F to the actual measured steam temp
        after the evaporator solve — no loop required.
        """
        return self.heat_transfer_btu_hr / (self.heating_surface_ft2 * self.delta_T)

    # ------------------------------------------------------------------
    # Vapor leaving the pan
    # ------------------------------------------------------------------

    @property
    def vapor_evaporated(self):
        """EvaporatorSteam at the pan vapor-space pressure; flow = water_evaporated_lb_hr."""
        P_vap = self.massecuite.vapor_pressure_psia
        return EvaporatorSteam(P_vap, flow_lb_per_hr=self.water_evaporated_lb_hr)

    # ------------------------------------------------------------------
    # Dunder / display
    # ------------------------------------------------------------------

    def __repr__(self):
        return (
            f"Pan(steam={self.steam_type}, "
            f"A={self.heating_surface_ft2:,.0f} ft², "
            f"vacuum={self.inches_vacuum:.1f} inHg, "
            f"SS={self.supersaturation:.2f}, "
            f"feed={self.feed_flow_lb_hr:,.0f} lb/hr)"
        )

    def properties(self):
        return {
            # Feed
            'feed_flow_lb_hr':            self.feed_flow_lb_hr,
            'feed_solids_lb_hr':          self.feed_solids_lb_hr,
            'feed_temp_F':                self.feed_temp_F,
            # Massecuite composition
            'ml_purity':                  self.ml_purity,
            'masse_purity':               self.masse_purity,
            'masse_brix':                 self.masse_brix,
            'crystal_content_pct':        self.massecuite.crystal_content,
            'mother_liquor_brix':         self.massecuite.mother_liquor_brix,
            'crystal_yield_pct_brix':     self.massecuite.crystal_yield_pct_brix,
            # Material balance
            'massecuite_flow_lb_hr':      self.massecuite_flow_lb_hr,
            'water_evaporated_lb_hr':     self.water_evaporated_lb_hr,
            # Thermodynamic state
            'inches_vacuum':              self.inches_vacuum,
            'vapor_pressure_psia':        self.massecuite.vapor_pressure_psia,
            'supersaturation':            self.supersaturation,
            'head_ft':                    self.head_ft,
            'water_bp_surface_F':         self.massecuite.water_bp_surface,
            'massecuite_temp_surface_F':  self.massecuite.massecuite_temp_surface,
            'water_bp_at_head_F':         self.massecuite.water_bp_at_head,
            'massecuite_temp_F':          self.massecuite.massecuite_temp,
            'bpr_at_head_F':              self.massecuite.bpr_at_head,
            'density_lb_ft3':             self.massecuite.density,
            # Energy balance
            'cp_massecuite':              self.cp_massecuite,
            'h_fg_vapor':                 self.h_fg_vapor,
            'heat_sensible_btu_hr':       self.heat_sensible_btu_hr,
            'heat_evaporation_btu_hr':    self.heat_evaporation_btu_hr,
            'heat_loss_factor':           self.heat_loss_factor,
            'heat_loss_btu_hr':           self.heat_loss_btu_hr,
            'heat_transfer_btu_hr':       self.heat_transfer_btu_hr,
            # Steam consumption
            'steam_type':                 self.steam_type,
            'h_fg_calandria':             self.h_fg_calandria,
            'steam_flow_lb_hr':           self.steam_flow_lb_hr,
            'steam_to_evaporation_ratio': self.steam_to_evaporation_ratio,
            # Heat transfer coefficient
            'calandria_steam_temp_F':     self.calandria_steam_temp_F,
            'delta_T_F':                  self.delta_T,
            'heating_surface_ft2':        self.heating_surface_ft2,
            'U_btu_hr_ft2_F':             self.U_btu_hr_ft2_F,
        }

    def display_properties(self):
        props = self.properties()
        print("Units: T(°F), flow(lb/hr), Q(BTU/hr), A(ft²), U(BTU/hr·ft²·°F), density(lb/ft³)")
        for k, v in props.items():
            if isinstance(v, str):
                print(f"  {k:<30}: {v}")
            else:
                print(f"  {k:<30}: {v:,.3f}")


if __name__ == "__main__":
    from SugarStream import SugarStream

    syrup   = SugarStream(brix=80, purity=52, flow_lb_per_hr=250_000,
                          temp_deg_F=144, pressure_psia=14.7, level_ft=0)
    footing = SugarStream(brix=88, purity=65, flow_lb_per_hr=50_000,
                          temp_deg_F=150, pressure_psia=14.7, level_ft=0)

    pan = Pan(
        feed_streams=[syrup, footing],
        heating_surface_ft2=22_000,
        inches_vacuum=26.5,
        supersaturation=1.2,
        head_ft=2,
        masse_brix=96,
        ml_purity=30,
        steam_type='V1',
        heat_loss_factor=0.05,
    )

    print(pan)
    print()
    pan.display_properties()

    print()
    print("--- single-pass U refinement after evaporator solve ---")
    pan.calandria_steam_temp_F = 228.0   # actual V1 temp from evaporator balance
    print(f"  U (standard 232.3F) -> U (actual 228.0F): {pan.U_btu_hr_ft2_F:.1f} BTU/hr.ft2.F")
