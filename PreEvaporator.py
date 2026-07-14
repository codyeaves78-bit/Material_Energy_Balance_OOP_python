from SugarStream import SugarStream
from SteamStream import EvaporatorSteam
from evaporator_functions import calculate_U_dessin, sat_pressure_from_temp, calculate_U_heat_xfer
from sugar_stream_properties import bpe_total, get_latent_heat, sat_steam_temp, get_cp
from condensate_utils import flash_condensate


class PreEvaporator:
    """
    Single-effect pre-evaporator where the vapor output (bleed) is fixed and known.
    Iterates to find the vapor pressure (and hence liquid temperature) that is
    consistent with the available heating surface and Dessin U value.
    Mirrors Birkett's pre-evaporator method.
    """

    def __init__(self,
                 juice_in: SugarStream,
                 supply_steam: EvaporatorSteam,
                 vapor_bleed_lb_per_hr: float,
                 area_ft2: float,
                 liquid_level_ft: float = 2,
                 dessin_coefficient: float = 18000):
        self.juice_in = juice_in
        self.supply_steam = supply_steam
        self.vapor_bleed_lb_per_hr = vapor_bleed_lb_per_hr
        self.area_ft2 = area_ft2
        self.liquid_level_ft = liquid_level_ft
        self.dessin_coefficient = dessin_coefficient

        # juice-side mass balance is fixed (bleed = evaporation)
        solids_lb_hr = juice_in.flow_lb_per_hr * juice_in.brix / 100
        self.juice_out_flow_lb_per_hr = juice_in.flow_lb_per_hr - vapor_bleed_lb_per_hr
        self.juice_out_brix = solids_lb_hr / self.juice_out_flow_lb_per_hr * 100

        # outputs set by solve()
        self.vapor_pressure_psia = supply_steam.P_psia * 0.7  # initial guess
        self.exhaust_required_lb_per_hr = 0.0
        self.liquid_temp_deg_F = 0.0
        self.vapor_temp_deg_F = 0.0

        # juice output stream — updated in place by solve()
        self.juice_out = SugarStream(
            brix=self.juice_out_brix,
            purity=juice_in.purity,
            flow_lb_per_hr=self.juice_out_flow_lb_per_hr,
            temp_deg_F=juice_in.temp_deg_F,
            pressure_psia=self.vapor_pressure_psia,
            level_ft=liquid_level_ft,
        )
        self.solve()

    def solve(self, max_iter: int = 20):
        """Iterate vapor pressure using Dessin U and heating surface area."""
        cp_in = get_cp(self.juice_in.brix)
        caland_h_fg  = self.supply_steam.h_fg
        caland_temp  = self.supply_steam.sat_temp_deg_F

        for _ in range(max_iter):
            vap_temp   = sat_steam_temp(self.vapor_pressure_psia)
            vap_h_fg   = get_latent_heat(self.vapor_pressure_psia)
            bpe        = bpe_total(self.liquid_level_ft, self.juice_in.brix, self.vapor_pressure_psia)
            liq_temp   = vap_temp + bpe

            u_des = calculate_U_dessin(
                brix_out=self.juice_out_brix,
                calandria_temp_deg_F=caland_temp,
                h_fg_juice_vapors=vap_h_fg,
                dessin_coefficient=self.dessin_coefficient,
            )

            exh_req = (self.juice_in.flow_lb_per_hr * cp_in * (liq_temp - self.juice_in.temp_deg_F)
                       + self.vapor_bleed_lb_per_hr * vap_h_fg) / caland_h_fg

            heat_duty  = exh_req * caland_h_fg
            delta_t    = heat_duty / (u_des * self.area_ft2)
            liq_temp   = caland_temp - delta_t
            vap_temp   = liq_temp - bpe
            self.vapor_pressure_psia = sat_pressure_from_temp(vap_temp)

        self.exhaust_required_lb_per_hr = exh_req
        self.supply_steam.flow_lb_per_hr = exh_req # sync with solved value
        self.liquid_temp_deg_F = liq_temp
        self.vapor_temp_deg_F  = vap_temp

        # sync juice_out stream
        self.juice_out.brix            = self.juice_out_brix
        self.juice_out.flow_lb_per_hr  = self.juice_out_flow_lb_per_hr
        self.juice_out.temp_deg_F      = liq_temp
        self.juice_out.pressure_psia   = self.vapor_pressure_psia

    @property
    def heat_duty_btu_per_hr(self):
        return self.exhaust_required_lb_per_hr * self.supply_steam.h_fg

    @property
    def dessin_U(self):
        return calculate_U_dessin(
            brix_out=self.juice_out_brix,
            calandria_temp_deg_F=self.supply_steam.sat_temp_deg_F,
            h_fg_juice_vapors=get_latent_heat(self.vapor_pressure_psia),
            dessin_coefficient=self.dessin_coefficient,
        )
    
    @property
    def delta_T_mean(self):
        return self.supply_steam.sat_temp_deg_F - self.juice_out.temp_deg_F

    @property
    def U_calc(self):
        return calculate_U_heat_xfer(heat_duty_btu_per_hr=self.heat_duty_btu_per_hr, area_ft2=self.area_ft2, temp_diff_deg_F=self.delta_T_mean)

    @property
    def U_ratio(self):
        return self.U_calc / self.dessin_U

    @property
    def clean_condensate(self):
        """Post-flash condensate from the fresh exhaust supply steam (lb/hr)."""
        return flash_condensate(self.exhaust_required_lb_per_hr, self.supply_steam.sat_temp_deg_F)

    def display_properties(self):
        vap_psig = self.vapor_pressure_psia - 14.696
        print(f"  Juice in:          {self.juice_in.flow_lb_per_hr/2000:,.3f} tph @ {self.juice_in.brix:.2f} brix, {self.juice_in.temp_deg_F:.2f} °F")
        print(f"  Juice out:         {self.juice_out_flow_lb_per_hr/2000:,.3f} tph @ {self.juice_out_brix:.2f} brix, {self.liquid_temp_deg_F:.2f} °F")
        print(f"  Vapor bleed:       {self.vapor_bleed_lb_per_hr/2000:,.3f} tph")
        print(f"  Vapor pressure:    {self.vapor_pressure_psia:.4f} psia  ({vap_psig:.4f} psig)")
        print(f"  Vapor temp:        {self.vapor_temp_deg_F:.4f} °F")
        print(f"  Calandria temp:    {self.supply_steam.sat_temp_deg_F:.4f} °F")
        print(f"  Exhaust required:  {self.exhaust_required_lb_per_hr:,.2f} lb/hr  ({self.exhaust_required_lb_per_hr/2000:,.3f} tph)")
        print(f"  Heat duty:         {self.heat_duty_btu_per_hr:,.0f} BTU/hr")
        print(f"  Heating surface:   {self.area_ft2:,} ft²")
        print(f"  U dessin:          {self.dessin_U:.4f} BTU/hr·ft²·°F")

    def generate_pfd(self, show=True, save_path=None, name="Pre Evaporator"):
        """Render the process flow diagram. Returns the matplotlib Figure."""
        from evaporator_diagram import plot_pre_diagram  # lazy import avoids circular dependency
        return plot_pre_diagram(self, pre_name=name, show=show, save_path=save_path)

    def to_excel(self, workbook, sheet_writer=None, name="Pre-Evaporator"):
        """Write this pre-evaporator to its own styled sheet (streams,
        performance tables, and PFD). Pass an existing SheetWriter to append
        onto a shared sheet instead of creating a new one."""
        import matplotlib.pyplot as plt
        from excel_export import SheetWriter

        standalone = sheet_writer is None
        sw = sheet_writer or SheetWriter(workbook, name, ncols=4)
        sw.ws.page_setup.fitToHeight = 1  # fit the whole sheet onto one page
        if standalone:
            sw.title(name,
                     f"vapor bleed = {self.vapor_bleed_lb_per_hr:,.0f} lb/hr | "
                     f"area = {self.area_ft2:,.0f} ft² | U ratio = {self.U_ratio:.3f}")

        vap_psig = self.vapor_pressure_psia - 14.696
        sw.section(f"{name} — PROCESS FLOW DIAGRAM")
        sw.blank()
        fig = self.generate_pfd(show=False, name=name)
        sw.image(fig, scale=0.4)
        plt.close(fig)

        sw.section(f"{name} — STREAMS")
        sw.table(
            ["Stream", "Flow (lb/hr)", "Brix / P (psia)", "Temp (°F)"],
            [
                ("Juice In",      self.juice_in.flow_lb_per_hr,      self.juice_in.brix,       self.juice_in.temp_deg_F),
                ("Juice Out",     self.juice_out_flow_lb_per_hr,     self.juice_out_brix,      self.liquid_temp_deg_F),
                ("Vapor Bleed",   self.vapor_bleed_lb_per_hr,        self.vapor_pressure_psia, self.vapor_temp_deg_F),
                ("Exhaust Steam", self.exhaust_required_lb_per_hr,   self.supply_steam.P_psia, self.supply_steam.sat_temp_deg_F),
            ],
            fmts=["@", "#,##0", "0.00", "0.0"],
        )

        sw.section(f"{name} — PERFORMANCE")
        sw.row("Vapor pressure",           self.vapor_pressure_psia,       "psia",          fmt="0.0000")
        sw.row("Vapor pressure",           vap_psig,                       "psig",          fmt="0.0000")
        sw.row("Vapor temp",               self.vapor_temp_deg_F,          "°F",            fmt="0.0000")
        sw.row("Calandria temp",           self.supply_steam.sat_temp_deg_F, "°F",          fmt="0.0000")
        sw.row("Heat duty",                self.heat_duty_btu_per_hr,      "BTU/hr",        fmt="#,##0")
        sw.row("Heating surface",          self.area_ft2,                  "ft²",           fmt="#,##0")
        sw.row("U Dessin",                 self.dessin_U,                  "BTU/hr·ft²·°F", fmt="0.0000")
        sw.row("U calc",                   self.U_calc,                    "BTU/hr·ft²·°F", fmt="0.0000")
        sw.row("U ratio (calc/Dessin)",    self.U_ratio,                   "",              fmt="0.000")

        return sw.finish() if standalone else sw
