"""
Example 1
NOTE: all specific details to each station will be listed INSIDE each station
        the main parameters are given here
A cane sugar factory is running 13000 tons of cane
They have 6 mills in a single tandem, using 30% imbibition
They have primary heaters only running on V1
They have 2 sets of evaporators, both quadruple sets
The sugar boiling scheme used is 3 boiling double magma
Live steam pressure generated: 200 psig, at turbines: 175 psig
Exhaust pressure used: 18 psig
V1 pressure used in calcs: 7 psig (can update upon solving evaporators
Worked exmaples only showcase the neat_display() functions
"""
import Clarification
import SteamStream
import SugarStream
from MillFloor import MillFloor

mills = MillFloor(cane_tpd=13000, cane_pol_pct=13.5, cane_fiber_pct=14.5,
                  bagasse_moisture_pct=49.5, bagasse_pol_pct=2.2, bagasse_ash_pct=5,
                  imbibition_pct_on_cane=30, mix_juice_purity=86, last_roll_purity=70,
                  number_of_mills=6, mill_1_fiber_rise_load_fraction=0.35,
                  name='Mill Floor')
# the input 'mill_1_fiber_rise_load_fraction' is for approximating maceration flows
# unimportant for overall calcs
mills.neat_display()

# Clarification is done before JuiceHeaters to solve the mass balance first
# use 'mills.mixed_juice_stream' and 'mills.cane_tpd' as inputs for this station
from Clarification import Clarification

clarifiers = Clarification(mixed_juice_stream=mills.mixed_juice_stream, cane_tpd=mills.cane_tpd,
                            filter_cake_pct_on_cane=5, filter_cake_pol_pct=2, filter_wash_water_pct_on_cane=5,
                           clarified_juice_purity=86.5, clarified_juice_temp_f=205, limed_juice_cold_temp_f=90,
                           limed_juice_hot_temp_f=220, lime_baume=10, lime_lb_per_ton_cane=1.3,
                           polymer_conc_ppm=5000, polymer_lb_per_ton_cane=0.045, clarifier_underflow_pct_cane=20,
                           name='Clarification and Mud Filters')
clarifiers.neat_display()

# we now feed JuiceHeaterShellTube the outputs from clarifiers and a SteamStream object
from JuiceHeater import JuiceHeaterShellTube
from SteamStream import SteamStream

exhaust_psia = 18 + 14.7 # psia
V1_psia = 7 + 14.7 # psia

juice_heaters = JuiceHeaterShellTube(
    cold_stream=clarifiers.limed_juice_cold_stream, # feeding it the stream created in clarification
    hot_stream=SteamStream(P=V1_psia, x=1), # creating a steam object based on out V1 pressure
    name='Limed Juice Heaters',
    juice_out_temp_degF=clarifiers.limed_juice_hot_temp_f, # another parameter defined in clarification
    U_btu_per_ft2_degF=220, installed_area_ft2=10000, steam_type=1 # 1 means V1 used, 0 means exhaust
)
juice_heaters.neat_display()

# Next we will solve the Pan floor, this balance must be solved so EvaporatorSet has bleed flowrates
# First we create a syrup object to feed the Pans
from SugarStream import SugarStream

syrup = SugarStream.copy(clarifiers.clarified_juice_stream) # copy the clarified juice stream
syrup.evaporate(new_brix=63, new_temp=144) # use the evaporate function to handle the material balnce
syrup.display_properties() # check properties, can remove this line if needed

from ThreeBoilingDoubleMagma import ThreeBoilingDoubleMagma
from Pan import Pan
from Centrifugal import Centrifugal
from Crystallizer_and_Reheater import Crystallizer, Reheater

# Exhaust will be used on the entire Pan Floor
# for feed_stream, use None, the ThreeBoilingDoubleMagma object handles rebuilding and feeding it the right streams
# Same for centrifugals, massecuite=None, the master object handles
# NOTE: this section handles the largest amount of inputs, so it is highly recommended to use this as boiler plate
pan_floor = ThreeBoilingDoubleMagma(
    syrup=syrup,
    A_pans=Pan(
        feed_streams=None, heating_surface_ft2=12000, inches_vacuum=23.5,
        supersaturation=1.2, head_ft=2, masse_brix=92, ml_purity=70, # mother liquor purity
        calandria_pressure_psia=exhaust_psia, heat_loss_factor=0.02,
        name='A Pans', steam_type=0 # meaning exhaust
        ),
    A_centrifugals=Centrifugal(
        massecuite=None, massecuite_flow_lb_hr=0, # master object updates this flow
        target_molasses_brix=82, purity_rise=2, molasses_temp=145,
        sugar_moisture=0.35, sugar_purity=99.4, sugar_temp=150,
        name="A Centrifugals"),
    B_pans=Pan(
        feed_streams=None, heating_surface_ft2=5000, inches_vacuum=25,
        supersaturation=1.2, head_ft=2, masse_brix=94, ml_purity=48,
        calandria_pressure_psia=exhaust_psia, heat_loss_factor=0.05,
        name='B Pans', steam_type=0
        ),
    B_centrifugals=Centrifugal(
        massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82, purity_rise=2,
        sugar_moisture=5, sugar_purity=90, sugar_temp=150, molasses_temp=145,
        name="B Centrifugals"
    ),
    grain_pans=Pan(
        feed_streams=None, heating_surface_ft2=2000, inches_vacuum=25.5,
        supersaturation=1.2, head_ft=2, masse_brix=88, ml_purity=39,
        calandria_pressure_psia=exhaust_psia, heat_loss_factor=0.05,
        name='Grain Pans', steam_type=0
    ),
    C_pans=Pan(
        feed_streams=None, heating_surface_ft2=5000, inches_vacuum=26.5,
        supersaturation=1.2, head_ft=2, masse_brix=95.5, ml_purity=33,
        calandria_pressure_psia=exhaust_psia, heat_loss_factor=0.05,
        name='C Pans', steam_type=0
    ),
    C_centrifugals=Centrifugal(
        massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82, purity_rise=4,
        sugar_moisture=5, sugar_purity=82, sugar_temp=150, molasses_temp=145,
        name="C Centrifugals"
    ),
    C_crystallizers=Crystallizer(
        massecuite_in=None, massecuite_flow_lb_hr=0,
        masse_temp_out_deg_F=120, ml_purity_out=30,
        water_temp_in_deg_F=85, water_temp_out_deg_F=105,
        name="C Crystallizers"
    ),
    C_reheaters=Reheater(
        massecuite_in=None, massecuite_flow_lb_hr=0,
        masse_temp_out_deg_F=130,
        water_temp_in_deg_F=150, water_temp_out_deg_F=135,
        name="C Reheaters"
    ),
    c_magma_brix=90,
    c_magma_remelt_pct=20,
    b_magma_brix=90,
    b_magma_remelt_pct=20,
    syrup_to_grain_pct=2,
    a_mol_to_grain_pct=10,
    b_mol_to_grain_pct=20,
    a_mol_top_off_pct=0,
    b_mol_top_off_pct=0,
    c_mol_top_off_pct=0,
    b_remelt_brix=60,
    c_remelt_brix=60,
    a_mol_dilution_brix=70,
    b_mol_dilution_brix=70,
    injection_water_temp_F=90,
    condenser_leg_temp_drop_F=8
)
pan_floor.neat_display()

V1_demand = juice_heaters.steam_required_lb_per_hr if juice_heaters.steam_type == 1 else 0

from EvaporatorSet import EvaporatorSet, EvaporatorSetSciPy # this is the Object with a better solver
from SteamStream import EvaporatorSteam

# it will be assumed that this set which is 2 quads ran in parrallel, that one large set will be
#    sufficient for modeling purposes
# no juice heater for clarified juice is used
evaporators = EvaporatorSetSciPy(
    juice_in=clarifiers.clarified_juice_stream, supply_steam=EvaporatorSteam(P_psia=exhaust_psia),
    last_effect_pressure_psia=2.4, target_brix_out=syrup.brix, effect_areas_ft2=[40000, 24000, 24000, 24000],
    vapor_bleeds=[V1_demand, 0, 0], dessin_coefficient=18000, liquid_level_ft=2, injection_water_temp_F=90,
    condenser_leg_temp_drop_F=8, name="Evaporator Set"
)
evaporators.adjust_pressure_profile_scipy()
evaporators.neat_display()

# This covers most of everything a fabrication superintendent would need.
# past this point will cover the live steam consumption of the factory, live steam available, and deaerators

from Deaerator import Deaerator
deareator = Deaerator(
    deaerator_psig=10, # NOTE this is psig, not psia
    water_in_deg_F=205,
    water_in_lb_hr=600000, # assumed value, can update upon solving
    vent_pct=1.0
)

deareator.display_properties() # no neat display available

# Total exhaust Consumption
exhaust_consumption_total = (
    juice_heaters.steam_required_lb_per_hr if juice_heaters.steam_type == 0 else 0
    + pan_floor.total_exhaust_steam_lb_hr
    + evaporators.supply_steam.flow_lb_per_hr
    + deareator.steam_flow_lb_hr
    + 30000 # assumed losses ~3-5%
)

print(f"\nExhaust for Heaters: {juice_heaters.steam_required_lb_per_hr if juice_heaters.steam_type == 0 else 0 :,.0f}")
print(f"Exhaust for Evaporators: {evaporators.supply_steam.flow_lb_per_hr:,.0f}")
print(f"Exhaust for Pans: {pan_floor.total_exhaust_steam_lb_hr:,.0f}")
print(f"Assumed Exhaust Losses: {30000:,.0f}")
print(f"Total Exhaust Required: {exhaust_consumption_total:,.0f}\n")

# Live Steam Requirements
from MillTurbines import MillTurbines
from CanePrepTurbines import CanePrepTurbines
from AuxillaryTurbines import AuxillaryTurbines

generated_steam = SteamStream(P=(200 + 14.7), x=1) # 200 psig sat steam
turbine_steam = SteamStream(P=(175 + 14.7), h=generated_steam.h) # 175 psig steam, same enthalpy as generated
tons_fiber_hr = mills.cane_fiber_pct / 100 * mills.cane_tph

# assumes 2 sets of knives
prep_turbines = CanePrepTurbines(
    hp_ton_fiber_hr=[14, 14],
    isentropic_efficiency=[50, 50],
    live_steam_object=turbine_steam,
    exhaust_psia=exhaust_psia,
    tons_fiber_hr=tons_fiber_hr
)
prep_turbines.neat_display()

mill_turbines = MillTurbines(
    hp_ton_fiber_hr=[13, 11, 11, 11, 11, 13],
    isentropic_efficiency=[50] * 6,
    live_steam_object=turbine_steam,
    exhaust_psia=exhaust_psia,
    tons_fiber_hr=tons_fiber_hr
)
mill_turbines.neat_display()

aux_turbines = AuxillaryTurbines(
    group_name="Auxillary Turbines",
    name_list=['ID fan 1', 'ID fan 2', 'ID fan 3', 'ID fan 4', 'water pump'],
    hp_list=  [600,        600,       600,         600,       300],
    isentropic_efficiency=[40] * 5, # smaller less efficient turbines
    live_steam_object=turbine_steam,
    exhaust_psia=exhaust_psia,
)
aux_turbines.neat_display()

# Totalizing the equipment steam required and exhaust available
total_live_steam_for_equipment = (
    mill_turbines.total_inlet_flow_lb_hr
    + prep_turbines.total_inlet_flow_lb_hr
    + aux_turbines.total_inlet_flow_lb_hr
)
exhaust_available_from_turbines = (
    mill_turbines.total_exhaust_available_lb_hr
    + prep_turbines.total_exhaust_available_lb_hr
    + aux_turbines.total_exhaust_available_lb_hr
)
makeup_steam_required = exhaust_consumption_total - exhaust_available_from_turbines

if makeup_steam_required < 0: # ensures no negative makeup gets into the math
    makeup_steam_required = 0

total_live_steam_required = (
    total_live_steam_for_equipment
    + makeup_steam_required
    + 20000 # assumed losses, jets and steam outs and venting
)

print(f"\nLive Steam for Equipment {total_live_steam_for_equipment:,.0f} lb/hr")
print(f"Exhaust available from turbines {exhaust_available_from_turbines:,.0f} lb/hr")
print(f"Make up steam required {makeup_steam_required:,.0f} lb/hr")
print(f"Total Live Steam Required {total_live_steam_required:,.0f} lb/hr")
print(f"lb / hr of steam per ton cane / hr: {total_live_steam_required / mills.cane_tph:.0f}")







