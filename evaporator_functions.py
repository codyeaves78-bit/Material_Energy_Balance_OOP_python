# functions to use in Evaporator.py and EvaporatorSet.py

# define a couple heat transfer coefficient functions first
def calculate_U_dessin(brix_out, calandria_temp_deg_F, h_fg_juice_vapors, dessin_coefficient):
    """Calculate the overall heat transfer coefficient U using Dessin's method"""
    u = (100 - brix_out) * (calandria_temp_deg_F - 130) * h_fg_juice_vapors / dessin_coefficient
    return u

def calculate_U_heat_xfer(heat_duty_btu_per_hr, area_ft2, temp_diff_deg_F):
    """Calculate the overall heat transfer coefficient U using the basic heat transfer equation"""
    # liquids are both boiling so LMTD is subbed out for T_hot - T_cold
    u = heat_duty_btu_per_hr / (area_ft2 * temp_diff_deg_F) 
    return u

def shortcut_evaporator_steam(juice_in_lb_per_hr: float, brix_in: float, brix_out: float,
                               number_of_effects: int, vapor_bleeds: list = None) -> float:
    """
    Shortcut solver for evaporator set to estimate initial steam requirement.
    vapor_bleeds: list eg [100000, 50000, 30000]
    """
    if vapor_bleeds is None:
        vapor_bleeds = []

    # mass balance
    solids_lb_per_hr = juice_in_lb_per_hr * brix_in / 100
    syrup_lb_per_hr = solids_lb_per_hr * 100 / brix_out
    evap_lb_per_hr = juice_in_lb_per_hr - syrup_lb_per_hr

    # generating weight vapor bleed list
    effect_number_list = [i + 1 for i in range(number_of_effects)]
    vapor_bleed_list_weighted = [vap_bleed * effect_number for vap_bleed, effect_number in zip(vapor_bleeds, effect_number_list)]
    
    # calculating steam requirements
    sum_of_weighted_bleeds = sum(vapor_bleed_list_weighted)
    x_factor = (evap_lb_per_hr - sum_of_weighted_bleeds) / number_of_effects
    steam_req = x_factor + sum(vapor_bleeds) # this will be an output
    
    return steam_req

def initial_brix_profile(juice_in_lb_per_hr: float, brix_in: float, brix_out: float,
                               number_of_effects: int, vapor_bleeds: list = None) -> list[float]:
    
    # safety
    if vapor_bleeds is None:
        vapor_bleeds = []

    # call earlier function for less writing of code
    steam_req = shortcut_evaporator_steam(juice_in_lb_per_hr, brix_in, brix_out, number_of_effects, vapor_bleeds)
    solids_lb_per_hr = juice_in_lb_per_hr * brix_in / 100

    # generating brix list
    evaporated_list = [steam_req]
    flow_list = [juice_in_lb_per_hr]
    brix_list = [brix_in]
    for i in range(number_of_effects):
        # 1. Safely grab the bleed value, default to 0 if out of bounds
        bleed = vapor_bleeds[i] if i < len(vapor_bleeds) else 0
        
        # 2. Calculate and store next evaporation step (skip the very last effect)
        if i < number_of_effects - 1:
            evaporated_list.append(evaporated_list[i] - bleed)
            
        # 3. Calculate and store next flow rate
        current_flow = flow_list[i] - evaporated_list[i]
        flow_list.append(current_flow)
        
        # 4. Calculate and store next brix percentage
        brix_list.append((solids_lb_per_hr / current_flow) * 100)
    return brix_list

def convert_psig_to_psia(pressure_psig: float):
    """Convert pressure from psig to psia"""
    psia = pressure_psig + 14.696
    return psia

def convert_inHg_vacuum_to_psia(vacuum_inHg: float):
    """Convert pressure from inHg to psia"""
    # get vacuum inHg to absolute pressure
    inHg_abs = 29.9213596 - vacuum_inHg
    psia = 0.491154 * inHg_abs
    return psia

def pressure_profile_initial(supply_steam_pressure_psia: float, last_effect_pressure_psia: float, number_of_effects: int):
    """initial pressure profile for trial and error calculations"""
    delta_p = (supply_steam_pressure_psia - last_effect_pressure_psia) / number_of_effects
    pressure_list = [supply_steam_pressure_psia]
    for i in range(number_of_effects):
        pressure_list.append(pressure_list[i] - delta_p)
    return pressure_list
