import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # so this runs standalone from any cwd

from EvaporatorSet import EvaporatorSet, EvaporatorSetSciPy
from SugarStream import SugarStream
from SteamStream import EvaporatorSteam
from evaporator_functions import convert_inHg_vacuum_to_psia

# We will size an evaporator with a simple script here
# Assumed it is supplying 80000 lb/hr to primary heaters and 60000 lb/hr to secondary heaters
# This is roughly what a sugar factory running at 500 tph will need on heaters ~140,000 lb/hr heaters
# Feel free to use this script and adjust bleeds and number of effects how you like
# tweaking of the pressure profile is required to get equal effect areas for non bled bodies

juice = SugarStream(brix=13, purity=85, flow_lb_per_hr=1_000_000, temp_deg_F=205, pressure_psia=40, level_ft=2)
steam = EvaporatorSteam(P_psia=30)

evaporator_set = EvaporatorSetSciPy(
    juice_in=juice,
    supply_steam=steam,
    last_effect_pressure_psia=convert_inHg_vacuum_to_psia(25),
    target_brix_out=65,
    effect_areas_ft2=[1000, 1000, 1000, 1000],
    vapor_bleeds=[80000, 40000],
    name='Evaporator Set',
)

for i in range(3):
    evaporator_set.manually_set_pressures([22, 16, 10.2]) # your desired pressure profile
    ratio_list = [evap.U_ratio for evap in evaporator_set.evaporator_list]
    new_hs_list = [a*b for a,b in zip(ratio_list,evaporator_set.effect_areas_ft2)]
    evaporator_set = EvaporatorSetSciPy(
        juice_in=juice,
        supply_steam=steam,
        last_effect_pressure_psia=convert_inHg_vacuum_to_psia(25),
        target_brix_out=65,
        effect_areas_ft2=new_hs_list,
        vapor_bleeds=[80000, 60000],
        name='Evaporator Set',
    )

evaporator_set.adjust_pressure_profile_scipy() # get final pressure profile
evaporator_set.neat_display()
print(f"Steam Required: {evaporator_set.supply_steam.flow_lb_per_hr:,.0f}")
i = 0
for hs in new_hs_list:
    print(f"HS on body {i+1}: {new_hs_list[i]:,.0f} ft2")
    i+=1
