# Evaporator class for modeling steam evaporator behavior and multiple effect evaporators
from SugarStream import SugarStream
from SteamStream import EvaporatorSteam, SteamStream
from Evaporator import Evaporator
from evaporator_functions import (initial_brix_profile, pressure_profile_initial, 
                                  shortcut_evaporator_steam, convert_inHg_vacuum_to_psia, 
                                  convert_psig_to_psia, convert_psia_to_psig, 
                                  convert_psia_to_inHgVac)
import time
from statistics import stdev

class EvaporatorSet:
    """Class to represent a set of evaporators"""
    def __init__(self, juice_in: SugarStream,
                 supply_steam: EvaporatorSteam,
                 last_effect_pressure_psia=2.4,
                 target_brix_out=65,
                 effect_areas_ft2=[1000, 1000, 1000],
                 vapor_bleeds=[0, 0],
                 dessin_coefficient=18000,
                 liquid_level_ft=2,
                 name: str = 'Evaporator Set'):
        """initialize class"""
        self.name = name
        self.juice_in = juice_in
        self.supply_steam = supply_steam
        self.last_effect_pressure_psia = last_effect_pressure_psia
        self.target_brix_out = target_brix_out
        self.effect_areas_ft2 = effect_areas_ft2
        self.vapor_bleeds = vapor_bleeds
        self.dessin_coefficient = dessin_coefficient
        self.liquid_level_ft = liquid_level_ft
        self.number_of_effects = len(self.effect_areas_ft2)
        # 1. Package the shared arguments into a temporary dictionary
        evap_args = {
            "juice_in_lb_per_hr": self.juice_in.flow_lb_per_hr,
            "brix_in": self.juice_in.brix,
            "brix_out": self.target_brix_out,
            "number_of_effects": self.number_of_effects,
            "vapor_bleeds": self.vapor_bleeds
        }
        self.steam_initial_guess = shortcut_evaporator_steam(**evap_args)
        self.initial_brix_profile = initial_brix_profile(**evap_args)
        self.pressure_profile_initial = pressure_profile_initial(self.supply_steam.P_psia, self.last_effect_pressure_psia, self.number_of_effects)
        self.supply_steam.flow_lb_per_hr = self.steam_initial_guess
        self.build_effects()
    
    def build_effects(self):
        """Builds the evaporator effects objects and stores them in a list"""
        # print(f"Steam initial guess: {self.steam_initial_guess:,.1f} lb/hr")
        # print(f"Brix profile: {[f'{b:.1f}' for b in self.initial_brix_profile]}")
        # print(f"Pressure profile: {[f'{p:.2f}' for p in self.pressure_profile_initial]}")
        self.evaporator_list = [Evaporator(
            juice_side_in=self.juice_in,
            calandria_side=self.supply_steam,
            area_ft2=self.effect_areas_ft2[0],
            liquid_level_ft=self.liquid_level_ft,
            dessin_coefficient=self.dessin_coefficient,
            vapor_pressure_psia=self.pressure_profile_initial[1], # first list item is calandria, so second item [1] is first effect vapor pressure
            vapor_bleed=self.vapor_bleeds[0]
        )]

        self.evaporator_list[0].solve()

        for i in range(self.number_of_effects - 1):
            steam_to_next = self.evaporator_list[i].lbs_evaporated_per_hr - self.evaporator_list[i].vapor_bleed.flow_lb_per_hr
            bled_vapor = self.vapor_bleeds[i+1] if i+1 < len(self.vapor_bleeds) else 0 # safety check if out of range
            evaporator = Evaporator(
                juice_side_in=self.evaporator_list[i].juice_side_out,
                calandria_side=EvaporatorSteam(P_psia=self.pressure_profile_initial[i + 1],flow_lb_per_hr=steam_to_next), # recall, pressure profile list starts with supply steam
                area_ft2=self.effect_areas_ft2[i + 1],
                liquid_level_ft=self.liquid_level_ft,
                dessin_coefficient=self.dessin_coefficient,
                vapor_pressure_psia=self.pressure_profile_initial[i + 2], # remember, first list item is supply steam, so 2 list items down would be second eff vap press, so on and so forth
                vapor_bleed=bled_vapor
            )
        # note on the logic, okay look, if the number of effects is 3, then the list length of the pressure profile will be 4. 
        # so the loop number in this case would be 3 - 1 = 2. 
        # So that way, the calandria side on building evap effect 2 in the first loop (list item [1]) gets the second list item for juice_side_in
        # And the vapor_pressure_psia gets the third list item
        # the final loop logic will not be out of range because on the last loop (which means i=1, second loop because first i=0) i + 2 = 3,
        #  which is the 4th and last list item on the self.pressure_profile_initial list
            evaporator.solve()
            self.evaporator_list.append(evaporator)

    def update_steam_flow(self, new_steam_flow_lb_per_hr):
        """changes steam flow to the set and resolves the effects"""
        self.supply_steam.flow_lb_per_hr = new_steam_flow_lb_per_hr
        self.evaporator_list[0].calandria_side.flow_lb_per_hr = self.supply_steam.flow_lb_per_hr
        for i in range(self.number_of_effects - 1):
            vapor_to_next = self.evaporator_list[i].lbs_evaporated_per_hr - self.evaporator_list[i].vapor_bleed.flow_lb_per_hr
            self.evaporator_list[i+1].calandria_side.flow_lb_per_hr = vapor_to_next
        self.update_set()

    def update_set(self):
        for i in range(self.number_of_effects):
            self.evaporator_list[i].solve()

    def solve_for_steam(self):
        """Trial and error method to get the actual required steam flow rate"""
        # warm start: use current steam if already set, fall back to shortcut guess
        x_n_min_1 = self.supply_steam.flow_lb_per_hr if self.supply_steam.flow_lb_per_hr > 0 else self.steam_initial_guess
        self.update_steam_flow(x_n_min_1)
        max_iterations = 100
        tolerance = 0.0001 # higher or lower brix target difference
        current_iteration = 0
        f_x_n_min_1 = self.target_brix_out - self.evaporator_list[-1].juice_side_out.brix
        x_n = x_n_min_1 * 1.02
        while abs(self.brix_target_difference) >= tolerance and current_iteration < max_iterations:
            self.update_steam_flow(x_n)
            f_x_n = self.target_brix_out - self.evaporator_list[-1].juice_side_out.brix
            f_prime_x_n_min_1 = (f_x_n - f_x_n_min_1) / (x_n - x_n_min_1)
            x_n_min_1 = x_n
            x_n = x_n_min_1 - (f_x_n / f_prime_x_n_min_1)
            f_x_n_min_1 = f_x_n
            #print(f"Current guess: {x_n_min_1:,.2f} lb/hr | Difference: {self.brix_target_difference:,.4f} | Iteration: {current_iteration}")
            current_iteration += 1
        
        if abs(self.brix_target_difference) <= tolerance:
            pass # incase you want to take the # out of the print line
            #print(f"Convergence succesful! Final guess: {x_n_min_1:,.2f} lb/hr | Difference: {self.brix_target_difference:,.4f} | Iteration: {current_iteration}")
        else:
            #pass # incase you want to take the # out of the print line
            print(f"XXX Failure to converge! XXX : Final guess: {x_n_min_1:,.2f} lb/hr | Difference: {self.brix_target_difference:,.6f} | Iteration: {current_iteration}")
        self.update_steam_flow(x_n_min_1)  # apply last evaluated converged value, not the next extrapolation

    def adjust_pressure_profile(self):
        """Adjust the pressure profile based on the average_u_ratio / current body u_ratio"""
        self.update_set()
        # print(f"Initial pressure profiel: {self.pressure_profile_initial}")
        u_dessin_list = [evaporator.dessin_U for evaporator in self.evaporator_list]
        u_calc_list = [evaporator.heat_xfer_U for evaporator in self.evaporator_list]
        u_ratio_list = [float(u_calc / u_dessin) for u_calc, u_dessin in zip(u_calc_list, u_dessin_list)]
        average_u_ratio = sum(u_ratio_list) / len(u_ratio_list) # u_calc / u_dessin

        # adjust the pressures now
        pressure_iteration = 0
        max_pressure_iterations = 100
        # guard: stdev requires finite values; bail out if physics are invalid
        if not all(u == u and u != float('inf') and u != float('-inf') for u in u_ratio_list):
            print("Warning: non-finite U ratio encountered before pressure loop, skipping adjustment.")
            return
        while stdev(u_ratio_list) > 0.0001 and pressure_iteration < max_pressure_iterations:

            for i in range(self.number_of_effects - 1): # don't change last effect pressure
                ratio = average_u_ratio / u_ratio_list[i]
                if ratio > 0:  # skip adjustment if ratio is non-positive (avoids nan from negative base)
                    self.evaporator_list[i].vapor_pressure_psia *= ratio**0.1
                self.evaporator_list[i + 1].calandria_side.P_psia = self.evaporator_list[i].vapor_pressure_psia
            self.update_set()
            self.solve_for_steam()

            # update lists and average
            u_dessin_list = [evaporator.dessin_U for evaporator in self.evaporator_list]
            u_calc_list = [evaporator.heat_xfer_U for evaporator in self.evaporator_list]
            u_ratio_list = [float(u_calc / u_dessin) for u_calc, u_dessin in zip(u_calc_list, u_dessin_list)]
            average_u_ratio = sum(u_ratio_list) / len(u_ratio_list) # u_calc / u_dessin
            pressure_iteration += 1
            # bail out if nan/inf crept in during iteration
            if not all(u == u and u != float('inf') and u != float('-inf') for u in u_ratio_list):
                print("Warning: non-finite U ratio encountered during pressure adjustment, stopping early.")
                break
        current_pressure_list = [evaporator.vapor_pressure_psia for evaporator in self.evaporator_list]
        # print(f"Current pressure profile: {current_pressure_list} | Iterations to complete: {pressure_iteration}")
        # print(f"U ratio list: {u_ratio_list}")

    def manually_set_pressures(self, pressure_list):
        """Manually set the presure profile for testing purposes"""
        for i in range(self.number_of_effects - 1):
            self.evaporator_list[i].vapor_pressure_psia = pressure_list[i]
            self.evaporator_list[i + 1].calandria_side.P_psia = pressure_list[i]
        self.update_set()
        self.solve_for_steam()
    @property
    def total_hs(self):
        return sum(self.effect_areas_ft2)
    
    @property
    def hs_num_eff_ratio(self):
        return self.total_hs / self.number_of_effects
    
    @property
    def delta_P_set(self):
        return self.supply_steam.P_psia - self.last_effect_pressure_psia
    
    @property
    def weight_for_init_distr(self):
        return self.hs_num_eff_ratio * self.delta_P_set

    @property
    def brix_target_difference(self):
        return self.target_brix_out - self.evaporator_list[-1].juice_side_out.brix
    
    @property
    def U_ratio_avg(self):
        u_rat_list = [self.evaporator_list[i].U_ratio for i in range(self.number_of_effects)]
        u_avg = sum(u_rat_list) / self.number_of_effects
        return u_avg

    def show_brix_list_actual(self):
        print(f"Brix of Entering Juice: {self.juice_in.brix}")
        for i in range(self.number_of_effects):
            print(f"Brix in effect {i+1}: {self.evaporator_list[i].juice_side_out.brix}")

    def properties(self) -> dict:
        cls = type(self)
        prop_names = [k for k, v in vars(cls).items() if isinstance(v, property)]
        instance_vars = {k: v for k, v in vars(self).items() if not k.startswith('_')}
        return {**instance_vars, **{k: getattr(self, k) for k in prop_names}}
    
    def display_properties(self):
        props = self.properties()
        print("Units: T(°F), P(psia), h_fg(BTU/lb)")
        for key, value in props.items():
            formatted = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
            print(f"{key}: {formatted}")

    def show_me_evaporator_details(self):
        for i in range(self.number_of_effects):
            print(f"\n \n Evaporator {i+1} Details:\n {'-'*50} \n")
            self.evaporator_list[i].display_properties()
        print(f"\n {'-'*5} Steam Required for Set: {self.supply_steam.flow_lb_per_hr:,.2f} lb/hr {'-'*5} \n")

    def show_summary(self):
        n  = self.number_of_effects
        ef = self.evaporator_list
        syrup_out  = ef[-1].juice_side_out
        steam_psig = convert_psia_to_psig(self.supply_steam.P_psia)
        last_vac   = convert_psia_to_inHgVac(self.last_effect_pressure_psia)

        LBL = 18
        COL = 11
        SEP = " | "
        W   = LBL + len(SEP) + (COL + len(SEP)) * n

        heavy = "=" * W
        light = "-" * W

        # ── Set summary ──────────────────────────────────────────────────
        print(f"\n{heavy}")
        print(f"  {self.name}")
        print(f"{heavy}")
        print(f"  Juice In     : {self.juice_in.flow_lb_per_hr:>12,.0f} lb/hr"
              f"  |  {self.juice_in.brix:>6.2f} brix"
              f"  |  {self.juice_in.temp_deg_F:>6.1f} deg F")
        print(f"  Syrup Out    : {syrup_out.flow_lb_per_hr:>12,.0f} lb/hr"
              f"  |  {syrup_out.brix:>6.2f} brix"
              f"  |  {syrup_out.temp_deg_F:>6.1f} deg F")
        print(f"  Steam Req'd  : {self.supply_steam.flow_lb_per_hr:>12,.0f} lb/hr"
              f"  |  {self.supply_steam.P_psia:>6.2f} psia - {steam_psig:>6.2f} psig"
              f"  |  {self.supply_steam.sat_temp_deg_F:>6.1f} deg F")
        print(f"  Last Eff Vac : {last_vac:>6.2f} inHg")
        print(f"  Avg U Ratio  : {self.U_ratio_avg:>6.3f}")

        # ── Effect detail table ──────────────────────────────────────────
        print(f"\n{light}")

        def row(label, values, fmt="{:>11,.0f}"):
            cells = SEP.join(fmt.format(v) for v in values)
            print(f"{label:<{LBL}}{SEP}{cells}")

        # header
        hdrs = SEP.join(f"{'Effect ' + str(i+1):>{COL}}" for i in range(n))
        print(f"{self.name:<{LBL}}{SEP}{hdrs}")
        print(light)

        row("juice in lb/hr",   [e.juice_side_in.flow_lb_per_hr        for e in ef])
        row("syrup out lb/hr",  [e.juice_side_out.flow_lb_per_hr       for e in ef])
        row("steam in lb/hr",   [e.calandria_side.flow_lb_per_hr       for e in ef])
        row("evaporated lb/hr", [e.lbs_evaporated_per_hr               for e in ef])
        row("vap bleed lb/hr",  [e.vapor_bleed.flow_lb_per_hr          for e in ef])
        print(light)
        row("brix in",          [e.juice_side_in.brix                  for e in ef], "{:>11.2f}")
        row("brix out",         [e.juice_side_out.brix                 for e in ef], "{:>11.2f}")
        row("juice temp deg F", [e.juice_side_in.temp_deg_F            for e in ef], "{:>11.1f}")
        row("syrup temp deg F", [e.juice_side_out.temp_deg_F           for e in ef], "{:>11.1f}")
        row("juice cp",         [e.juice_side_in.cp_btu_per_lb_deg_F  for e in ef], "{:>11.3f}")
        row("syrup cp",         [e.juice_side_out.cp_btu_per_lb_deg_F for e in ef], "{:>11.3f}")
        print(light)
        row("vapor psia",       [e.vapor_pressure_psia                 for e in ef], "{:>11.2f}")
        row("vapor temp deg F", [e.vapor_temperature                   for e in ef], "{:>11.1f}")
        row("vapor h_fg BTU/lb",[e.vapor_out.h_fg                     for e in ef], "{:>11.1f}")
        row("calandria psia",   [e.calandria_side.P_psia               for e in ef], "{:>11.2f}")
        row("calandria deg F",  [e.calandria_side.sat_temp_deg_F       for e in ef], "{:>11.1f}")
        row("cal h_fg BTU/lb",  [e.calandria_side.h_fg                 for e in ef], "{:>11.1f}")
        print(light)
        row("Duty MM BTU/hr",   [e.heat_duty_btu_per_hr / 1e6         for e in ef], "{:>11.3f}")
        row("HS ft2",           [e.area_ft2                            for e in ef], "{:>11,.0f}")
        row("U calc",           [e.heat_xfer_U                         for e in ef], "{:>11.1f}")
        row("U Dessin",         [e.dessin_U                            for e in ef], "{:>11.1f}")
        print(light)
        print(f"  U is in BTU/(hr*ft2*degF)\n")

        # ── Energy balance per effect ────────────────────────────────────
        print(f"\n{light}")
        print(f"  ENERGY BALANCE AT EACH EFFECT FOR: {self.name}")
        print(light)
        for i, e in enumerate(ef):
            steam_flow  = e.calandria_side.flow_lb_per_hr
            h_fg_steam  = e.calandria_side.h_fg
            entering    = e.heat_duty_btu_per_hr / 1e6

            juice_flow  = e.juice_side_in.flow_lb_per_hr
            cp          = e.juice_side_in.cp_btu_per_lb_deg_F
            T_in        = e.juice_side_in.temp_deg_F
            T_out       = e.juice_side_out.temp_deg_F
            sensible    = e.heat_from_flash / 1e6   # positive when flashing (T_in > T_out)

            net         = e.heat_available_for_evaporation / 1e6
            h_fg_vap    = e.juice_side_out.latent_heat_btu_per_lb
            evap        = e.lbs_evaporated_per_hr

            print(f"\n  Effect {i + 1}")
            print(f"  {'Entering  ':<12}"
                  f"  {steam_flow:>10,.0f} lb/hr"
                  f" * {h_fg_steam:>7.1f} BTU/lb"
                  f" / 10^6"
                  f"  =  {entering:>8.3f} MM BTU/hr")
            print(f"  {'Sensible  ':<12}"
                  f"  {juice_flow:>10,.0f} lb/hr"
                  f" * {cp:>5.3f} cp"
                  f" * ({T_in:.1f} - {T_out:.1f}) degF"
                  f" / 10^6"
                  f"  =  {sensible:>8.3f} MM BTU/hr")
            
            print(f"  Net for Evaporation  -->  "
                  f"{entering:.3f} + ({sensible:.3f})"
                  f"  =  {net:.3f} MM BTU/hr")
            print(f"  Evaporated  =  {net:.3f} MM BTU/hr * 10^6"
                  f" / {h_fg_vap:.1f} BTU/lb"
                  f"  =  {evap:,.0f} lb/hr")
            print(f"  {'-' * (W - 2)}")
        print(f"\n{light}\n")

    def check_material_balance(self):
        """Checks the material balance of the system"""
        print(f"\n Checking Material Balance \n")
        for i in range(self.number_of_effects):
            # Juice Side Balance
            entering_juice = self.evaporator_list[i].juice_side_in.flow_lb_per_hr
            exiting_juice = self.evaporator_list[i].juice_side_out.flow_lb_per_hr
            vapors = self.evaporator_list[i].vapor_out.flow_lb_per_hr
            balance = entering_juice - exiting_juice - vapors
            balance_tolerance = 0.1
            if abs(balance) > balance_tolerance:
                print(f"warning! Balance Error in effect {i+1}, ")
                print(f"IN juice {entering_juice:,.2f} - OUT juice {exiting_juice:,.2f} - OUT {vapors:,.2f} = {balance:,.2f} lb/hr")
            # Steam Side Balance
            steam_in = self.evaporator_list[i].calandria_side.flow_lb_per_hr
            condensate_out = self.evaporator_list[i].condensate_out
            calandria_balance = steam_in - condensate_out
            calandria_tolerance = 0.1
            if abs(calandria_balance) > calandria_tolerance:
                print(f"warning! Balance Error in effect {i}, ")
                print(f"IN steam {steam_in:,.2f} - OUT condensate {condensate_out:,.2f} = {calandria_balance:,.2f} lb/hr")
            else:
                print(f"Material Balance OK in effect {i+1}")


    def check_energy_balance(self):
        """Checks the energy balance of the system"""
        print(f"\n Checking Energy Balance \n")
        for i in range(self.number_of_effects):

            # Juice Heat Energy Sensible Rise plus Vapor Latent Heat
            temp_in = self.evaporator_list[i].juice_side_in.temp_deg_F
            temp_out = self.evaporator_list[i].juice_side_out.temp_deg_F
            latent_heat = self.evaporator_list[i].juice_side_out.latent_heat_btu_per_lb
            flow_pph = self.evaporator_list[i].juice_side_in.flow_lb_per_hr
            cp = self.evaporator_list[i].juice_side_in.cp_btu_per_lb_deg_F
            temp_change = temp_out - temp_in
            Q_dot_sens = flow_pph * cp * temp_change
            Q_dot_latent = self.evaporator_list[i].vapor_out.flow_lb_per_hr * latent_heat
            juice_energy_rise = Q_dot_sens + Q_dot_latent

            # from supply steam
            steam_in = self.evaporator_list[i].calandria_side.flow_lb_per_hr
            steam_latent_heat = self.evaporator_list[i].calandria_side.h_fg
            steam_energy_drop = steam_in * steam_latent_heat

            # balance them
            energy_balance = juice_energy_rise - steam_energy_drop

            # check balance
            energy_tolerance = 100 # its a big number, so big tolerance
            
            if abs(energy_balance) > energy_tolerance:
                print(f"warning! Energy Balance Error in effect {i+1}, ")
                print(f"Juice: sensible heat: {Q_dot_sens:,.2f} + Latent heat: {Q_dot_latent:,.2f} = {juice_energy_rise:,.2f} BTU/hr")
                print(f"Steam: latent heat: {steam_in:,.2f} * {steam_latent_heat:,.2f} = {steam_energy_drop:,.2f} BTU/hr")
                print(f"Balance: {energy_balance:,.2f} BTU/hr")
            else:
                print(f"Energy Balance OK in effect {i+1}")


if __name__ == "__main__":
    test_set = EvaporatorSet(
        juice_in=SugarStream(brix=12, purity=90, flow_lb_per_hr=200_000, temp_deg_F=225, pressure_psia=60, level_ft=0),
        supply_steam=EvaporatorSteam(P_psia=convert_psig_to_psia(20), flow_lb_per_hr=0),
        last_effect_pressure_psia=convert_inHg_vacuum_to_psia(26),
        target_brix_out=60,
        effect_areas_ft2=[8800, 3100, 3100],
        vapor_bleeds=[31357+3895+28108],
        dessin_coefficient=18000,
        liquid_level_ft=2
    )

    start_time = time.time()
    # test_set.manually_set_pressures([23.252, 16.698, 9.769]) # for trouble shooting
    test_set.adjust_pressure_profile()
    test_set.show_me_evaporator_details()
    test_set.check_material_balance()
    test_set.check_energy_balance()
    test_set.show_summary()
    end_time = time.time()
    execution_time = end_time - start_time
    print(f"Execution time: {execution_time:.8f} seconds")