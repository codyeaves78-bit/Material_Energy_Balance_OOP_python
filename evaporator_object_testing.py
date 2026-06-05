from Evaporator import Evaporator
from SteamStream import EvaporatorSteam
from SugarStream import SugarStream
from evaporator_functions import convert_psig_to_psia, convert_inHg_vacuum_to_psia
import numpy

clear_juice = SugarStream(brix=12,
                          purity=90,
                          flow_lb_per_hr=200_000,
                          temp_deg_F=225,
                          pressure_psia=60,
                          level_ft=0)

evaporator_steam = EvaporatorSteam(P_psia=convert_psig_to_psia(20), 
flow_lb_per_hr=53902)

# Build Initial Sets

evap_1 = Evaporator(
    juice_side_in=clear_juice,
    calandria_side=evaporator_steam,
    area_ft2=4800,
    liquid_level_ft=2,
    dessin_coefficient=18000,
    vapor_pressure_psia=convert_psig_to_psia(9),
    vapor_bleed=0
)

evap_1.solve()
evap_2 = Evaporator(
    juice_side_in=evap_1.juice_side_out,
    calandria_side=evap_1.vapor_out,
    area_ft2=4800,
    liquid_level_ft=2,
    dessin_coefficient=18000,
    vapor_pressure_psia=convert_inHg_vacuum_to_psia(2),
    vapor_bleed=0
)
evap_2.solve()

evap_3 = Evaporator(
    juice_side_in=evap_2.juice_side_out,
    calandria_side=evap_2.vapor_out,
    area_ft2=4800,
    liquid_level_ft=2,
    dessin_coefficient=18000,
    vapor_pressure_psia=convert_inHg_vacuum_to_psia(26),
    vapor_bleed=0
)
evap_3.solve()
brix_trial_1 = evap_3.juice_side_out.brix
print(f"{'-'*50}\n\n Changing inlet flow to 50000... \n\n")
evap_1.calandria_side.flow_lb_per_hr = 50000
evap_1.solve()
evap_2.solve()
evap_3.solve()
brix_trial_2 = evap_3.juice_side_out.brix
print(f"Initial trial syrup brix: {brix_trial_1:.2f}")
print(f'Second trial syrup brix: {brix_trial_2:.2f}')
# so simply changing one input actually updates all of the objects
# consider a few functions to build, manage, and update evaporators instead of a Set object

# Basic solver loop for steam below
# adjust the steam flow
target_brix = 60
max_steam_iterations = 100
steam_iteration = 0
brix_tolerance = 0.0001
x_n_min_1 = evap_1.calandria_side.flow_lb_per_hr
f_x_n_min_1 = target_brix - evap_3.juice_side_out.brix
x_n = x_n_min_1 * 1.02
target_difference = target_brix - evap_3.juice_side_out.brix
while abs(target_difference) > brix_tolerance and steam_iteration < max_steam_iterations:
    evap_1.calandria_side.flow_lb_per_hr = x_n # update inlet steam flow
    # solve each effect
    evap_1.solve()
    evap_2.solve()
    evap_3.solve()
    
    # Newton Rhapson method for new steam flow
    f_x_n = target_brix - evap_3.juice_side_out.brix
    f_prime_x_n_min_1 = (f_x_n - f_x_n_min_1) / (x_n - x_n_min_1)
    x_n_min_1 = x_n
    x_n = x_n_min_1 - (f_x_n / f_prime_x_n_min_1)
    f_x_n_min_1 = f_x_n
    
    # check the difference, update target difference
    target_difference = target_brix - evap_3.juice_side_out.brix
    print(f"Current guess: {x_n_min_1:,.2f} lb/hr | Difference: {target_difference:,.4f} | Iteration: {steam_iteration}")
    steam_iteration += 1
    
if target_difference <= brix_tolerance:
    #pass # incase you want to take the # out of the print line
    print(f"Convergence succesful! Final guess: {x_n:,.2f} lb/hr | Difference: {target_difference:,.6f} | Iteration: {steam_iteration}")
elif target_difference > brix_tolerance:
    #pass # incase you want to take the # out of the print line
    print(f"XXX Failure to converge! XXX : Final guess: {x_n:,.2f} lb/hr | Difference: {target_difference:,.6f} | Iteration: {steam_iteration}")

evap_list = [evap_1, evap_2, evap_3]
for i in range(len(evap_list)):
    print(f"Evaporator {i+1} outlet brix: {evap_list[i].juice_side_out.brix:.2f}")

# So it seems we need these functions
# 1 - a function to build the evaporator objects based on input criteria, outputs a list
# 2 - a function to solve for initial conditions
# 3 - a function to input the initial conditions, needs to have initial conditions and a list of evaporators
# 4 - a function to solve for steam flow via the above newton-rhapson method
# 5 - a function to adjust the pressure profile based on my U ratio logic present in my google colab evaporator notebook
# 6 - finally, a function to balance the juice distribution between sets again based on U ratio, also in my google colab notebook
