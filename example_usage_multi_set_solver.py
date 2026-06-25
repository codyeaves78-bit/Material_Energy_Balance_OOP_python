import sys

from multi_set_solver import solve_multi_set
from EvaporatorSet import EvaporatorSet
from SugarStream import SugarStream
from SteamStream import SteamStream, EvaporatorSteam
from time import time

start_time = time()

# An example with no Pre evaporator
clarified_juice = SugarStream(
    brix=14,
    purity=90,
    flow_lb_per_hr=1_500_000,
    temp_deg_F=220,
    pressure_psia=40,
    level_ft=0    
)

# No matter what, we have to build out out initial distribution function manually by passing lists
hs_list = [4*[25000], 4*[12000], [11000, 9000, 9000]] # set 1, 2, and 3
supply_steam_pressures = [30, 25, 16]
last_effect_psias = [2.4, 2.4, 2.4]

def get_initial_juice(hs_list: list, supply_steam_psias: list, last_effect_psias: list):
    """Returns a list of the initial juice distribution fractions
    hs_list is a list of lists with each sets heating surface by effect
    supply_steam_psias is a list of supply steam psia for each set
    last_effect_psias is a list of last effect pressures for each set"""
    num_eff_list = [len(eff) for eff in hs_list]
    hs_set_list = [sum(hs) for hs in hs_list]
    dps = []

    for i in range(len(supply_steam_pressures)):
        dp = supply_steam_pressures[i] - last_effect_psias[i]
        dps.append(dp)
    weights = []

    for i in range(len(num_eff_list)):
        wt = hs_set_list[i] * dps[i] / num_eff_list[i]
        weights.append(wt)

    sum_wts = sum(weights)

    fracs = [wt / sum_wts for wt in weights]
    return fracs
    

fracs = get_initial_juice(hs_list=hs_list, supply_steam_psias=supply_steam_pressures, last_effect_psias=last_effect_psias)
print(f"Initial Fractions: {fracs} \n\n")


frac1 = fracs[0]
frac2 = fracs[1]
frac3 = 1 - frac1 - frac2
initial_juice_fractions = [frac1, frac2, frac3] # This must add up to 1, assuming 3 sets


supply_steam_psia = 30

juice_to_set_1 = clarified_juice.copy(clarified_juice)
juice_to_set_1.flow_lb_per_hr = initial_juice_fractions[0] * clarified_juice.flow_lb_per_hr
exh_set_1 = EvaporatorSteam(supply_steam_psia)

juice_to_set_2 = juice_to_set_1.copy(clarified_juice)
juice_to_set_2.flow_lb_per_hr = initial_juice_fractions[1] * clarified_juice.flow_lb_per_hr
exh_set_2 = EvaporatorSteam(supply_steam_psia)

juice_to_set_3 = juice_to_set_1.copy(clarified_juice)
juice_to_set_3.flow_lb_per_hr = initial_juice_fractions[2] * clarified_juice.flow_lb_per_hr
exh_set_3 = EvaporatorSteam(16) # stress testing


# build out some initial sets

set_1 = EvaporatorSet(
    juice_in=juice_to_set_1,
    supply_steam=exh_set_1,
    last_effect_pressure_psia=2.4,
    target_brix_out=65,
    effect_areas_ft2=4*[25000], # 4 effects @ 25000 ft2
    vapor_bleeds=[100000, 50000],
    dessin_coefficient=18000,
    liquid_level_ft=2
)

set_2 = EvaporatorSet(
    juice_in=juice_to_set_2,
    supply_steam=exh_set_2,
    last_effect_pressure_psia=2.4,
    target_brix_out=65,
    effect_areas_ft2=4*[12000], # 4 effects @ 12000 ft2
    vapor_bleeds=[50000, 20000],
    dessin_coefficient=18000,
    liquid_level_ft=2
)

set_3 = EvaporatorSet(
    juice_in=juice_to_set_3,
    supply_steam=exh_set_3,
    last_effect_pressure_psia=2.4,
    target_brix_out=65,
    effect_areas_ft2=[11000, 9000, 9000], 
    vapor_bleeds=[0],
    dessin_coefficient=18000,
    liquid_level_ft=2
)

def initial_juice_distr(evaporators: list):
    """Needs a list of built evaporators"""
    juice_initial_weights = [evaporator.weight_for_init_distr for evaporator in evaporators]
    weight_sum = sum(juice_initial_weights)
    juice_initial_distribution = [wt / weight_sum for wt in juice_initial_weights]
    return juice_initial_distribution


# store in a list and solve pressure profile
evap_list = [set_1, set_2, set_3]

# update flows by using above function
juice_distr_initial = initial_juice_distr(evap_list)
frac1 = juice_distr_initial[0]
frac2 = juice_distr_initial[1]
frac3 = juice_distr_initial[2]

i = 0
for evap in evap_list: # print out the initial summary
    evap.juice_in.flow_lb_per_hr = juice_distr_initial[i] * clarified_juice.flow_lb_per_hr
    evap.adjust_pressure_profile()
    print(f"Summary of Set {i + 1}")
    print(25 * '_')
    evap.show_summary()
    print('\n')
    i += 1


# Now apply a basic solving algorithm
for _ in range(10):
    print(f"Iteration {_ + 1}")
    u_rat_list = []
    for i in range(len(evap_list)):
        u = evap_list[i].U_ratio_avg
        u_rat_list.append(u)

    urat_avg = sum(u_rat_list) / len(u_rat_list)
    # update fracs
    frac1 *= (urat_avg / u_rat_list[0])**0.1 # apply a dampening factor
    frac2 *= (urat_avg / u_rat_list[1])**0.1
    frac3 = 1 - frac1 - frac2
    new_fracs = [frac1, frac2, frac3]

    # Now update juice flows
    i = 0
    for evap in evap_list:
        evap.juice_in.flow_lb_per_hr = new_fracs[i] * clarified_juice.flow_lb_per_hr
        evap.adjust_pressure_profile()
        i += 1
        
    print(u_rat_list)
    print(urat_avg)
    print(new_fracs)
    print('\n\n')

for evap in evap_list:
    evap.show_summary()


end_time = time()
time_solve = (end_time - start_time) * 1000
print(f"time to solve: {time_solve:.2f} ms")

# this solver works, but is dependent upon decent initial guesses.
# For decent initial guesses, we will split by this --> (set hs * delta P) / number of effects
# This accounts for colder steam and lower vacuum, then the U ratio loop should split fine after that
# plugging this in... I just made these properties in EvaporatorSet to easily call weight_for_init_distr


