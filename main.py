# This is an example usage for setting up your solver

# import all neccesary items

from mill_floor_material_balance import mill_floor_material_balance, display_mill_balance, extract_key_outputs
from clarification import clarification_material_balance, display_clarification_balance, extract_clarification_outputs
from SugarStream import SugarStream
from SteamStream import SteamStream, EvaporatorSteam
from Massecuite import Massecuite
from JuiceHeater import JuiceHeaterShellTube
from Evaporator import Evaporator
from EvaporatorSet import EvaporatorSet
from multi_effect_solver_vers_2 import solve_evaporator_sets
from Condenser import Condenser
from Pan import Pan
from Centrifugal import Centrifugal
from BoilingScheme import three_boiling_double_magma

# First solve the mill floor material balance
grinding_rate_daily = 18000 # tcpd

mill_balance = mill_floor_material_balance(
    cane_tpd=grinding_rate_daily,
    cane_pol_pct=13.5,
    cane_fiber_pct=14,
    imbibition_pct_on_cane=25,
    bagasse_pol_pct=2.0,
    bagasse_moisture_pct=50,
    last_roll_purity=70,
    mix_juice_purity=88,
    number_of_mills=6,
    mill_1_fiber_rise_load_fraction=0.35 # This is to calculate fiber % rise of bagasse out of mill 1 for maceration flow balance
)

display_mill_balance(mill_balance)
key_mill_data = extract_key_outputs(mill_balance)


clarification_results = clarification_material_balance(
        mixed_juice_lb_per_hr=key_mill_data['mixed_juice_lb_per_hr'],
        mixed_juice_brix_pct=key_mill_data['mixed_juice_brix'],
        mixed_juice_purity_pct=key_mill_data['mixed_juice_purity'],
        cane_tpd=grinding_rate_daily,
        filter_wash_water_pct_on_cane=8.0,
        filter_cake_pct_on_cane=6.0,
        filter_cake_pol_pct=2.0,
        clarified_juice_purity=90.0,
        mixed_juice_temp_f=80,
        limed_juice_hot_temp_f=220.0,
        lime_lb_per_ton_cane=1.3,
        lime_baume=10,
        polymer_lb_per_ton_cane=0.045,
        polymer_conc_ppm=5000,
        clarifier_underflow_pct_cane=20,
    )

print('\n')
display_clarification_balance(clarification_results)
key_clarification_data = extract_clarification_outputs(clarification_results)

# Limed juice object for JuiceHeaters

# Use this boiler plate to view any stream items for use in this code
#for key, value in clarification_results["streams"]["Limed Juice Cold"].items(): # example if you want details on a stream
        #print(f"{key}: {value}")

limed_juice = SugarStream(
    brix=clarification_results['streams']['Limed Juice Cold']['brix_pct'],
    purity=clarification_results['streams']['Limed Juice Cold']['purity_pct'],
    temp_deg_F=clarification_results['streams']['Limed Juice Cold']['temp_f'],
    flow_lb_per_hr=clarification_results['streams']['Limed Juice Cold']['lb_per_hr'],
    pressure_psia=40, #psia
    )


# Juice Heaters
# Assign Steam Pressures for juice heater calcs
# Note that you can come back and manually update Vapor Pressures based on Evaporator balance, for now use standard values
exhaust_psia = 30 # about 15 psig
v1_psia = 21 # about 6 psig
v2_psia = 14.7 # about 0 psig

# Set up for primary and secondary, rearrange how you like it
# Primary heaters
primary_heaters = JuiceHeaterShellTube(
    cold_stream=limed_juice,
    hot_stream=SteamStream(P=v2_psia, x=1),
    juice_out_temp_degF=160,
    U_btu_per_ft2_degF=220,
    installed_area_ft2=12000,
    name="Primary Heaters"
    )

primary_heaters.neat_display()

# Secondary heaters, uses flow out of primary heaters
secondary_heaters = JuiceHeaterShellTube(
        cold_stream=primary_heaters.juice_out,
        hot_stream=SteamStream(P=v1_psia, x=1),
        juice_out_temp_degF=clarification_results['streams']['Limed Juice Hot']['temp_f'], 
        U_btu_per_ft2_degF=220,
        installed_area_ft2=10000,
        name="Secondary Heaters"
        )

secondary_heaters.neat_display()


# Very brief evaporation calc to obtain syrup flow for pans

