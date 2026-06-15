"""
You are free to use this program and distribute as you please, however, please give the recognition where it is due.
Cody Eaves (Chemical Engineer) for the python Code and solving method for multiple sets
and Dr Harold Birkett (PhD Chemical Engineering) for the method of solving a single set of evaporators. 
Keep in mind this is specific for the Sugar Industry, results are unknown for evaporators with other fluids.
"""

# Import and Install Section


# import packages
import pandas as pd
import numpy as np
import time
import math
from scipy.optimize import fsolve

#---------------------------------------------------------------------------------------------------------
"""Input Data Section, this is where you can change your input data for the evaporator sets and pre evaporator"""
#---------------------------------------------------------------------------------------------------------

# Juice to Evaporators
clear_juice_tph = 750
clear_juice_brix = 14
clear_juice_temp = 225 # deg F
desired_syrup_brix = 65 # all effects will target this number

# Exhaust Steam, assumes saturated
exh_psig_pre_3 = 14
exh_psig_set_1 = 15
exh_psig_set_2 = 15
exh_psig_set_3 = 4

# Vacuum at last effect
last_eff_vac_set_1 = 25 # in Hg
last_eff_vac_set_2 = 25 # in Hg
last_eff_vac_set_3 = 25 # in Hg

# Injection water in and out temp for condensor, all use same values
inj_wat_temp_in = 95 # deg F
inj_wat_temp_out = 120 # deg F

# Vapor Bleed Lists [v1, v2, v3]
pre_3_bleed = 122 # tph
set_1_vbleed_list = [81, 0, 0] # tph
set_2_vbleed_list = [0, 0, 0] # tph
set_3_vbleed_list = [0, 0, 0] # tph

# Heating Surface Lists in ft2 [effect 1, effect 2, effect 3, ...]
pre_3_hs = 35000 # ft2
set_1_hs_list = [25000, 25000, 25000, 25000] # ft2
set_2_hs_list = [12000, 12000, 12000, 12000]
set_3_hs_list = [11000, 9000, 9000]

# Dessin Constants
pre_3_dessin = 18000
set_1_dessin = 18000
set_2_dessin = 18000
set_3_dessin = 18000

# liquid level in feet for bpe calculation
pre_3_liquid_level = 2
set_1_liquid_level = 2
set_2_liquid_level = 2
set_3_liquid_level = 2

# Units online, True / False
pre_3_online = False
set_1_online = False
set_2_online = False
set_3_online = True


start_time = time.time()

# --------------------------------------------------------------------------------------------------------
"""Defining All Functions First!!!"""
# --------------------------------------------------------------------------------------------------------

#shortcut calculations first

def shortcut_evap(jce_in, jce_brx, syrup_brx, num_effects, v1_bleed, v2_bleed, v3_bleed):
    sol_tph = jce_in * jce_brx / 100 # solids tons per hour
    syr_tph = sol_tph * 100 / syrup_brx # syrup tons per hour
    evap_tph = jce_in - syr_tph
    x_factor = (evap_tph - v1_bleed - 2 * v2_bleed - 3 * v3_bleed) / num_effects
    exh_req = x_factor + v1_bleed + v2_bleed + v3_bleed
    exh_savings = v1_bleed / num_effects + v2_bleed * 2 / num_effects + v3_bleed * 3 / num_effects

    evap_list = [] # list of shortcut tons evaporatored in each effect
    evap_list.append(exh_req) # evap effect 1
    evap_list.append(x_factor + v2_bleed + v3_bleed) # evap effect 2
    evap_list.append(x_factor + v3_bleed) # evap effect 3
    if num_effects > 3:
      evap_list.append(x_factor)
    if num_effects > 4:
      evap_list.append(x_factor)

    brix_list = [] # brix list of each stream
    flow_list = [] # flow list of each stream
    for i in range(num_effects + 1):
      if len(brix_list) == 0:
        flow_list.append(jce_in)
        brix_list.append(jce_brx)
      else:
        flow_list.append(flow_list[-1] - evap_list[i - 1])
        brix_list.append(sol_tph / flow_list[-1] * 100)

    evap_dict = {
        'juice_in_tph': jce_in,
        'juice_brx': jce_brx,
        'solids_tph': sol_tph,
        'syrup_tph': syrup_brx,
        'evaporated_tph': evap_tph,
        'x_factor': x_factor,
        'exhaust_required_tph': exh_req,
        'exhaust_saving_tph': exh_savings,
        'brix_list_shortcut': brix_list,
        'flow_list_shortcut': flow_list,
        'evap_list_shortcut': evap_list,
        }
    return evap_dict

def show_dict(example_dict):
    for key, value in example_dict.items():
        if isinstance(value, list):
            # Format each item in the list to 2 decimal places
            formatted_list = [f"{item:.2f}" for item in value]
            print(f"{key}: {formatted_list}")
        else:
            # Format the single number to 2 decimal places
            print(f"{key}: {value:.4f}")

"""# Shortcut method

Some notes: from birkett's paper, here are some evaporation to heating surface ratios (pph per sqr ft heat surface)
Triples: Use 11
Quads: Use 8
Quintuples: use 5.5
"""

# Get Juice Distribution
def juice_distr(set_1_hs, set_1_n_eff, set_2_hs=0, set_2_n_eff=3, set_3_hs=0, set_3_n_eff=3):
    """A function to distribute juices via the shortcut method"""
    def evap_rate(n, hs):
        if n == 3:
            rate = 11 * hs
        elif n == 4:
            rate = 8 * hs
        elif n == 5:
            rate = 5.5 * hs
        else:
            print('Invalid number of effects')
        return rate
    set_1_rate = evap_rate(set_1_n_eff, set_1_hs)
    set_2_rate = evap_rate(set_2_n_eff, set_2_hs)
    set_3_rate = evap_rate(set_3_n_eff, set_3_hs)

    total_rate = set_1_rate + set_2_rate + set_3_rate

    set_1_jce_frac = set_1_rate / total_rate
    set_2_jce_frac = set_2_rate / total_rate
    set_3_jce_frac = set_3_rate / total_rate

    jce_dist_list = [set_1_jce_frac, set_2_jce_frac, set_3_jce_frac]

    return jce_dist_list

# building my functions to call
def bpe_brix(brix):
  """ bpe from brix alone"""
  bpe = 4.266667 * brix / (100 - brix)
  return bpe

def bpe_head(lvl, brix, t_vap):
  """ bpe from head, level in ft"""
  brix_poly = (
      0.99991
      + 0.0038008 * brix
      + 0.000012662 * (brix**2)
      + 0.00000009596 * (brix**3)
  )

  temp_poly = (
      5.314
      - 0.07135 * t_vap
      + 0.00033908 * (t_vap**2)
      - 0.00000055728 * (t_vap**3)
  )

  bpe_calc = lvl * 6 * brix_poly * temp_poly
  if bpe_calc <1:
    bpe_calc = 1
  return bpe_calc

def sat_steam_temp(p_psia):
    """saturation steam temperature, I use this over IAPWS97 for speed"""
    """Only for pressure 1-60 psia"""
    A = 6.239238
    B = 2988.801361
    C = 377.305590
    temp = B / (A - np.log10(p_psia)) - C
    return temp

def bpe_total(lvl, brix, p_vap_psia):
   """bpe total, combine previous functions, lvl in ft"""
   t_vap = sat_steam_temp(p_vap_psia)
   bpe1 = bpe_brix(brix)
   bpe2 = bpe_head(lvl, brix, t_vap) # lvl in ft
   bpe_total = bpe1 + bpe2
   return bpe_total

def get_latent_heat(p_psia):
    """gets the latent heat of the steam or liquid"""
    # only for psia 1 to 60
    # this is much much faster but very slightly less accurate than using IAPWS97
    # Calculate the polynomial
    temp = sat_steam_temp(p_psia)
    h_fg = -0.00000152231563 * temp**3 + .000504774867 * temp**2 - 0.634291695987 * temp + 1096.29
    return h_fg

def get_cp(brix):
  """gets the specific heat capacity"""
  cp = 0.9964 - 0.005656 * brix
  return cp

def initial_pressure_profile(exh_psig, inHg_vac, n_eff):
  """solves for the initial pressure profile"""
  psia_0 = exh_psig + 14.696
  psia_f = (29.92 - inHg_vac) / 29.92 * 14.696
  delta_p = (psia_0 - psia_f) / n_eff
  psia_list = []
  for i in range(n_eff + 1):
    if len(psia_list) == 0:
      psia_list.append(psia_0)
    else:
      psia_list.append(psia_list[-1] - delta_p)
  return psia_list

def u_dessin(brix_out, temp_steam_in, h_fg_vap_out, k_constant):
    """calculates the dessin heat transfer coefficient"""
    u = (100 - brix_out) * (temp_steam_in - 130) * h_fg_vap_out / k_constant
    return u

def u_calc(heat_duty, area_ft2, temp_steam_in, temp_liquid):
    """calculates the heat transfer coefficient via regular heat transfer method"""
    # Q = U A lmtd ---> U = Q / (A * lmtd), lmtd is just td because they are at a constanct temp across heating surface
    u = heat_duty / (area_ft2 * (temp_steam_in - temp_liquid))
    return u

"""# comparing IAPWS97 to fast steam property formula

Now that our basic functions are built, we need to set up the method to solve a single set of evaporators, 
then wrap that up in a function to call later on to make solving multiple sets easy.

"""

# compare iapws to my calculation
# print(sat_steam_temp(15 + 14.696))
# print(sat_steam_temp(6 + 14.696))
# from my iapws calculator, i got 249.72 and 229.74 respectively, very close for this calculator

def solve_set(name, juice_in_tph, juice_brix, juice_temp, syrup_brix, v_bld_list, hs_list, exh_psig, last_eff_vac, liq_level, dessin_constant, inj_wat_temp_in, inj_wat_temp_out):
    # solve set y (will test with set 1, then replace instances of set_1 with set_y to make into function)
    # need the folliwng variables --> juice_in_tph, juice_brix, syrup_brix, v_bld_list , hs_list
    # will solve for n effects and set variables based on inputed lists
    # initial values
    clear_juice_in = juice_in_tph
    clear_juice_brix = juice_brix
    n_eff = len(hs_list)
    des_cnst = dessin_constant
    clear_juice_temp = juice_temp # deg f


    shortcut_dict = shortcut_evap(
        clear_juice_in,
        clear_juice_brix,
        syrup_brix,
        n_eff,
        v_bld_list[0],
        v_bld_list[1],
        v_bld_list[2]
        )

    press_list = initial_pressure_profile(exh_psig, last_eff_vac, n_eff)
    vap_temp_list = []
    latent_heat_list = []
    cp_list = []
    bpe_list = []
    liq_temp_list = []
    for i in range(n_eff + 1):
        vap_temp_list.append(sat_steam_temp(press_list[i]))
        latent_heat_list.append(get_latent_heat(press_list[i]))
        cp_list.append(get_cp(shortcut_dict['brix_list_shortcut'][i]))
        if i == 0:
            liq_temp_list.append(clear_juice_temp)
            bpe_list.append(0)
        else:
            bpe_list.append(bpe_total(liq_level, shortcut_dict['brix_list_shortcut'][i], press_list[i]))
            liq_temp_list.append(vap_temp_list[i] + bpe_list[i])

    # now the trial and error loop
    for iter in range(50):
        if iter == 0:
            exh_in = shortcut_dict['exhaust_required_tph']
        
        for trials in range(5):
            difference = 1 # initialize difference variable to enter loop
            # solve for exhaust first
            while difference > 0.00001 or difference < -0.00001:
                evap_list_calc = []
                steam_list = [exh_in]
                juice_list = [clear_juice_in]

                # evaporation effect 1
                evap_list_calc.append((exh_in * latent_heat_list[0]
                                    - clear_juice_in * cp_list[0] * (liq_temp_list[1] - liq_temp_list[0]))
                                    / latent_heat_list[1])

                # steam and juice to next effect
                steam_list.append(evap_list_calc[-1] - v_bld_list[0])
                juice_list.append(juice_list[-1] - evap_list_calc[-1])

                # evaporation effect 2
                evap_list_calc.append((steam_list[-1] * latent_heat_list[1]
                                    - juice_list[-1] * cp_list[1] * (liq_temp_list[2] - liq_temp_list[1]))
                                    / latent_heat_list[2])

                # steam and juice to next effect
                steam_list.append(evap_list_calc[-1] - v_bld_list[1])
                juice_list.append(juice_list[-1] - evap_list_calc[-1])

                # evaporation effect 3
                evap_list_calc.append((steam_list[-1] * latent_heat_list[2]
                                    - juice_list[-1] * cp_list[2] * (liq_temp_list[3] - liq_temp_list[2]))
                                    / latent_heat_list[3])

                # steam and juice to next effect if n > 3, otherwise is  vapors to condensor and syrup out
                steam_list.append(evap_list_calc[-1] - v_bld_list[2])
                juice_list.append(juice_list[-1] - evap_list_calc[-1])

                # evaporation effect 4 if n > 3
                if n_eff > 3:
                    evap_list_calc.append((steam_list[-1] * latent_heat_list[3]
                                    - juice_list[-1] * cp_list[3] * (liq_temp_list[4] - liq_temp_list[3]))
                                    / latent_heat_list[4])

                    # steam and juice to next effect if n > 4, otherwise is  vapors to condensor and syrup out
                    steam_list.append(evap_list_calc[-1])
                    juice_list.append(juice_list[-1] - evap_list_calc[-1])

                # evaporation effect 5 if n > 4
                if n_eff > 4:
                    evap_list_calc.append((steam_list[-1] * latent_heat_list[4]
                                    - juice_list[-1] * cp_list[4] * (liq_temp_list[5] - liq_temp_list[4]))
                                    / latent_heat_list[5])

                    # vapors to condensor and syrup out
                    steam_list.append(evap_list_calc[-1])
                    juice_list.append(juice_list[-1] - evap_list_calc[-1])

                # now compare tons evaporated calculated to actual tons evaporated

                tons_evap_calc = sum(evap_list_calc)
                tons_evap_actual = shortcut_dict['evaporated_tph']
                difference = tons_evap_calc - tons_evap_actual
                # a note on the logic, if the difference is positive, we need less exhaust, if the difference is negative we need more exhaust
                exh_in = exh_in - (difference / (8)) # a simple gain/loss for the exh_in variable

            # now to adjust the brix, bpe, temp, and cp profiles

            brix_list = [clear_juice_brix]
            for i in range(n_eff):
                brix_list.append(shortcut_dict['solids_tph'] / juice_list[i + 1] * 100)
            vap_temp_list = []
            latent_heat_list = []
            cp_list = []
            bpe_list = []
            liq_temp_list = []
            for i in range(n_eff + 1):
                vap_temp_list.append(sat_steam_temp(press_list[i]))
                latent_heat_list.append(get_latent_heat(press_list[i]))
                cp_list.append(get_cp(brix_list[i]))
                if i == 0:
                    liq_temp_list.append(clear_juice_temp)
                    bpe_list.append(0)
                else:
                    bpe_list.append(bpe_total(liq_level, brix_list[i], press_list[i]))
                    liq_temp_list.append(vap_temp_list[i] + bpe_list[i])

        # now to adjust the pressure profile
        # use the u dessin a u calc methods to adjust pressure profile
        heat_list = []
        u_dessin_list = []
        u_calc_list = []
        u_ratio_list = []
        last_eff_press = press_list[-1]
        for j in range(len(steam_list) - 1):
            heat = steam_list[j] * latent_heat_list[j] * 2000
            heat_list.append(heat)
            # correction, I need to make a brix list before vap temp list, redo code to call frm
            u_dessin_list.append(u_dessin(brix_list[j + 1], vap_temp_list[j], latent_heat_list[j + 1], des_cnst))
            u_calc_list.append(u_calc(heat_list[j], hs_list[j], vap_temp_list[j], liq_temp_list[j + 1]))
            u_ratio_list.append(u_calc_list[j] / u_dessin_list[j])
        avg_u_ratio = sum(u_ratio_list) / len(u_ratio_list)
        #avg / vessel ratio

        for k in range(n_eff):
            press_list[k + 1] = press_list[k + 1] * (avg_u_ratio / u_ratio_list[k])**0.1

        # reset last effect pressure
        press_list[-1] = last_eff_press

    # now to store everything into a data frame
    press_psig_inHg_list = []
    for pressure in press_list:
        if pressure > 14.696:
            val = pressure - 14.696
            # Append as a string with " psig"
            press_psig_inHg_list.append(f"{val:,.2f} psig")
        else:
            # Calculate vacuum in inches of Mercury
            press_in_Hg = (29.92 - (29.92 * pressure / 14.696))
            # Append as a string with " inHg"
            press_psig_inHg_list.append(f"{press_in_Hg:,.2f} in Hg")

    # return vapor list to original length
    v_bld_list = v_bld_list[:3]

    effect_list = ['Effect 1', 'Effect 2', 'Effect 3']
    if n_eff > 3:
        effect_list.append('Effect 4')
        v_bld_list.append(0) # to fit into dataframe
    if n_eff > 4:
        effect_list.append('Effect 5')
        v_bld_list.append(0) # to fit into dataframe

    # Evaporation to HS Ratio and Dessin Evaporation Rate
    evap_to_hs_ratio = []
    for i in range(n_eff):
        evap_to_hs_ratio.append(evap_list_calc[i] * 2000 / hs_list[i])
    dessin_evap_rate = []
    for i in range(n_eff):
        dessin_evap_rate.append(u_dessin_list[i] * hs_list[i] * (vap_temp_list[i] - liq_temp_list[i + 1]) / latent_heat_list[i + 1] / 2000)
        


    # Exhaust Required List [exh_in, 0, 0,....]
    exhaust_list = [exh_in * 2000]
    for i in range(n_eff - 1):
        exhaust_list.append("--------")

    # Condensor Injection Water, water temp out = vapor temp
    vap_to_condense = evap_list_calc[-1]
    vap_latent_heat = latent_heat_list[-1]
    temp_out = inj_wat_temp_out
    temp_in = inj_wat_temp_in
    heat_req_to_condense = vap_to_condense * vap_latent_heat
    inj_wat_tph = heat_req_to_condense / (temp_out - temp_in)
    inj_wat_gpm = inj_wat_tph * 2000 / 60 / 8.3

    # put into dataframe
    inj_wat_gpm_list = [inj_wat_gpm]
    inj_wat_temp_list = [inj_wat_temp_in]
    for i in range(n_eff - 1):
        inj_wat_gpm_list.append("-----")
        if i == 0:
            inj_wat_temp_list.append(temp_out)
        else:
            inj_wat_temp_list.append("--------")

    # seperator for condensore information
    seperator_list = []
    for i in range(n_eff):
        seperator_list.append('--------')

    # make name list to fit into dataframe
    name_list = [name] + ["--------" for x in range(n_eff - 1)]

    df_set = pd.DataFrame({
        "Name": name_list,
        "Effect Number": effect_list,
        "Steam In (tph)": steam_list[:-1],
        "Calandria Temp (deg F)": vap_temp_list[:-1],
        "Calandria Pressure (psia)": press_list[:-1],
        "Calandria Pressure (psig / in Hg)": press_psig_inHg_list[:-1],
        "Steam in Latent Heat (btu/lb)": latent_heat_list[:-1],
        "Juice In (tph)": juice_list[:-1],
        "Brix in": brix_list[:-1],
        "Juice Temp In (deg F)": liq_temp_list[:-1],
        "cp in (btu/lb-F)": cp_list[:-1],
        "Juice Out (tph)": juice_list[1:],
        "Brix out": brix_list[1:],
        "Juice Temp Out (deg F)": liq_temp_list[1:],
        "cp out (btu/lb-F)": cp_list[1:],
        "Evaporated (tph)": evap_list_calc,
        "Vapor Bleed (tph)": v_bld_list,
        "Vapor Pressure (psia)": press_list[1:],
        "Vapor Pressure (psig / in Hg)": press_psig_inHg_list[1:],
        "Vapor Temperature (deg F)": vap_temp_list[1:],
        "Boiling Point Elevation (deg F)": bpe_list[1],
        "Vapor Latent Heat (btu/lb)": latent_heat_list[1:],
        "Heat Duty (btu/hr)": heat_list,
        "Heating Surface (ft2)": hs_list,
        "Evaporation to HS Ratio (lb/ft2)": evap_to_hs_ratio,
        "U calculated (btu/lb-hr-F)": u_calc_list,
        "U dessin (btu/lb-hr-F)": u_dessin_list,
        "U ratio": u_ratio_list,
        "Dessin Evaporation Rate (tph)": dessin_evap_rate,
        "--------": seperator_list,
        "Exhaust Required (lb/hr)": exhaust_list,
        "Injection Water (gpm)": inj_wat_gpm_list,
        "Injection Water Temp in, out (deg F)": inj_wat_temp_list,
        })
    
    # return vapor list to original length
    v_bld_list = v_bld_list[:3]
    

    return df_set
    # After Wrapping into a function, end function here

# Pre evaporator Function
def pre_evap(name, juice_in_tph, juice_in_brix, juice_temp, exh_psig, vapor_bleed, heat_surface, liquid_level, dessin_constant):
    evap_tph = vapor_bleed
    solids_tph = juice_in_brix * juice_in_tph / 100
    juice_out_tph = juice_in_tph - evap_tph
    juice_out_brix = solids_tph / juice_out_tph * 100
    cp_in = get_cp(juice_in_brix)
    cp_out = get_cp(juice_out_brix)
    caland_press = exh_psig + 14.696
    caland_temp = sat_steam_temp(caland_press)
    caland_latent_heat = get_latent_heat(caland_press)
    vap_press = caland_press * 0.7 # initial guess
    for i in range(20):
        vap_temp = sat_steam_temp(vap_press)
        vap_latent_heat = get_latent_heat(vap_press)
        bpe_juice = bpe_total(liquid_level, juice_in_brix, vap_press)
        liq_temp = vap_temp + bpe_juice
        u_dessin_pre = u_dessin(juice_out_brix, caland_temp, vap_latent_heat, dessin_constant)
        exh_req = (juice_in_tph * cp_in * (liq_temp - juice_temp) + vapor_bleed * vap_latent_heat) / caland_latent_heat
        heat_duty = exh_req * caland_latent_heat * 2000
        delta_t_m = heat_duty / (u_dessin_pre * heat_surface)
        liq_temp = caland_temp - delta_t_m
        vap_temp = liq_temp - bpe_juice
        vap_press = 4.29243 - 0.117802*vap_temp + 0.001330114*vap_temp**2 - 0.00000679176*vap_temp**3 + 0.0000000199634*vap_temp**4
    vap_psig = vap_press - 14.696

    
    df_pre = pd.Series({
            "Name": name,
            "Pre Evaporator": 'Pre Evaporator',
            "Steam In (tph)": exh_req,
            "Calandria Temp (deg F)": caland_temp,
            "Calandria Pressure (psia)": caland_press,
            "Calandria Pressure (psig)": exh_psig,
            "Steam in Latent Heat (btu/lb)": caland_latent_heat,
            "Juice In (tph)": juice_in_tph,
            "Brix in": juice_in_brix,
            "Juice Temp In (deg F)": juice_temp,
            "cp in (btu/lb-F)": cp_in,
            "Juice Out (tph)": juice_out_tph,
            "Brix out": juice_out_brix,
            "Juice Temp Out (deg F)": liq_temp,
            "cp out (btu/lb-F)": cp_out,
            "Evaporated (tph)": evap_tph,
            "Vapor Bleed (tph)": vapor_bleed,
            "Vapor Pressure (psia)": vap_press,
            "Vapor Pressure (psig)": vap_psig,
            "Vapor Temperature (deg F)": vap_temp,
            "Vapor Latent Heat (btu/lb)": vap_latent_heat,
            "Heat Duty (btu/hr)": heat_duty,
            "Heating Surface (ft2)": heat_surface,
            "U dessin (btu/lb-hr-F)": u_dessin_pre,
            "--------": '--------',
            "Exhaust Required (lb/hr)": exh_req * 2000,

            })
    return df_pre

#------------------------------------------------------------------------------------------------------------
"""Now to build a function to solve multiple cases at once"""
#------------------------------------------------------------------------------------------------------------



pre_3 = {
    "name": "Pre Evaporator 3",
    "juice_in_tph": clear_juice_tph,
    "juice_in_brix": clear_juice_brix,
    "juice_temp": clear_juice_temp,
    "exh_psig": exh_psig_pre_3,
    "vapor_bleed": pre_3_bleed,
    "heat_surface": pre_3_hs,
    "liquid_level": pre_3_liquid_level,
    "dessin_constant": pre_3_dessin,

}

if pre_3_online:
    df_pre_3 = pre_evap(**pre_3)
    brix_for_sets = df_pre_3['Brix out']
    juice_temp_for_sets = df_pre_3['Juice Temp Out (deg F)']
else:
    df_pre_3 = pd.Series()
    brix_for_sets = clear_juice_brix # if pre is offline, use clear juice brix for sets
    juice_temp_for_sets = clear_juice_temp # if pre is offline, use clear juice temp for sets



set_1 = {
    "name": "Set 1",
    "juice_in_tph": 0,
    "juice_brix": brix_for_sets,
    "juice_temp": juice_temp_for_sets,
    "syrup_brix": desired_syrup_brix,
    "v_bld_list": set_1_vbleed_list,
    "hs_list": set_1_hs_list,
    "exh_psig": exh_psig_set_1,
    "last_eff_vac": last_eff_vac_set_1,
    "liq_level": set_1_liquid_level,
    "dessin_constant": set_1_dessin,
    "inj_wat_temp_in": inj_wat_temp_in,
    "inj_wat_temp_out": inj_wat_temp_out,
}

set_2 = {
    "name": "Set 2",
    "juice_in_tph": 0,
    "juice_brix": brix_for_sets,
    "juice_temp": juice_temp_for_sets,
    "syrup_brix": desired_syrup_brix,
    "v_bld_list": set_2_vbleed_list,
    "hs_list": set_2_hs_list,
    "exh_psig": exh_psig_set_2,
    "last_eff_vac": last_eff_vac_set_2,
    "liq_level": set_2_liquid_level,
    "dessin_constant": set_2_dessin,
    "inj_wat_temp_in": inj_wat_temp_in,
    "inj_wat_temp_out": inj_wat_temp_out,
}

set_3 = {
    "name": "Set 3",
    "juice_in_tph": 0,
    "juice_brix": brix_for_sets,
    "juice_temp": juice_temp_for_sets,
    "syrup_brix": desired_syrup_brix,
    "v_bld_list": set_3_vbleed_list,
    "hs_list": set_3_hs_list,
    "exh_psig": exh_psig_set_3,
    "last_eff_vac": last_eff_vac_set_3,
    "liq_level": set_3_liquid_level,
    "dessin_constant": set_3_dessin,
    "inj_wat_temp_in": inj_wat_temp_in,
    "inj_wat_temp_out": inj_wat_temp_out,
}

# 1. Setup - This is the only place you need to update if sets change
all_sets_configs = [set_1, set_2, set_3]
all_sets_online = [set_1_online, set_2_online, set_3_online]

num_total = len(all_sets_configs)
active_indices = [i for i, online in enumerate(all_sets_online) if online]
num_active = len(active_indices)

def objective_function(trial_params):
    # Always maintain the full length for internal calculations
    fractions = [0.0] * num_total
    
    if num_active > 1:
        # Map trial_params to the correct online slots
        for i in range(num_active - 1):
            fractions[active_indices[i]] = trial_params[i]
        
        # The remainder goes to the last active set index
        fractions[active_indices[-1]] = 1.0 - sum(fractions)
    elif num_active == 1:
        fractions[active_indices[0]] = 1.0

    # Determine juice source logic
    total_juice = df_pre_3['Juice Out (tph)'] if pre_3_online else clear_juice_tph

    u_values = {}
    for i in active_indices:
        all_sets_configs[i]['juice_in_tph'] = fractions[i] * total_juice
        res = solve_set(**all_sets_configs[i])
        u_values[i] = res["U ratio"].mean()

    # Create the list of differences for fsolve to minimize
    active_u_list = [u_values[i] for i in active_indices]
    return [active_u_list[i] - active_u_list[i+1] for i in range(len(active_u_list) - 1)]

# --- Execution ---

# 1. Initialize the full-length result list with zeros
final_fractions = [0.0] * num_total

if num_active > 1:
    initial_guess = [1.0 / num_active] * (num_active - 1)
    opt_params, info, ier, msg = fsolve(objective_function, initial_guess, full_output=True)

    if ier == 1:
        # Fill the final_fractions list using active_indices
        for i in range(num_active - 1):
            final_fractions[active_indices[i]] = opt_params[i]
        
        # Assign remainder to the last active set
        final_fractions[active_indices[-1]] = 1.0 - sum(final_fractions)
    else:
        print(f"Convergence Error: {msg}")

elif num_active == 1:
    # If only one is online, it takes 100% (at its specific index)
    final_fractions[active_indices[0]] = 1.0

# final_fractions is now [f1, f2, f3] where offline sets are 0.0
# You can now call final_fractions[0], final_fractions[1], etc. safely.

if pre_3_online:
    juice_for_sets = df_pre_3['Juice Out (tph)'] 
else:
    juice_for_sets = clear_juice_tph


set_1["juice_in_tph"] = final_fractions[0] * juice_for_sets if set_1_online else 0
set_2["juice_in_tph"] = final_fractions[1] * juice_for_sets if set_2_online else 0
set_3["juice_in_tph"] = final_fractions[2] * juice_for_sets if set_3_online else 0

# once again, only solve if the set is online, otherwise set to empty dataframe to avoid errors
if set_1_online:
    df_set_1_opt = solve_set(**set_1)
else:
    df_set_1_opt = pd.DataFrame()

if set_2_online:
    df_set_2_opt = solve_set(**set_2)
else:
    df_set_2_opt = pd.DataFrame()

if set_3_online:
    df_set_3_opt = solve_set(**set_3)
else:
    df_set_3_opt = pd.DataFrame()


print("Final Juice Distribution results after optimization")
print(df_pre_3)
print("\n")
print(df_set_1_opt.T)
print("\n")
print(df_set_2_opt.T)
print("\n")
print(df_set_3_opt.T)
print("\n")

# now to put these dataframes into an excel file
"""
with pd.ExcelWriter('evaporator_results.xlsx') as writer:
    df_pre_3.to_frame().T.to_excel(writer, sheet_name='Pre Evaporator 3', index=False)
    df_set_1.T.to_excel(writer, sheet_name='Set 1 initial')
    df_set_2.T.to_excel(writer, sheet_name='Set 2 initial')
    df_set_3.T.to_excel(writer, sheet_name='Set 3 initial')

    df_set_1_opt.T.to_excel(writer, sheet_name='Set 1')
    df_set_2_opt.T.to_excel(writer, sheet_name='Set 2')
    df_set_3_opt.T.to_excel(writer, sheet_name='Set 3')
"""



#-----------------------------------
end_time = time.time()
elapsed_time = end_time - start_time
print(f"Elapsed time: {elapsed_time:.4f} seconds")
