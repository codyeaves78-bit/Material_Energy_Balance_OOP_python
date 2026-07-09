# This is an example usage for setting up your solver

import sys

class _Tee:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.file = open(filename, 'w', encoding='utf-8')
    def write(self, message):
        self.terminal.write(message)
        self.file.write(message)
    def flush(self):
        self.terminal.flush()
        self.file.flush()

sys.stdout = _Tee('output.txt') # The output file name

# import all neccesary items

from excel_export import new_workbook
from MillFloor import MillFloor
from Clarification import Clarification
from SugarStream import SugarStream
from SteamStream import SteamStream, EvaporatorSteam
from Massecuite import Massecuite
from JuiceHeater import JuiceHeaterShellTube
from Evaporator import Evaporator
from EvaporatorSet import EvaporatorSet, sets_to_excel
from multi_effect_solver_vers_2 import solve_evaporator_sets
from Condenser import Condenser
from Pan import Pan
from Centrifugal import Centrifugal
from ThreeBoilingDoubleMagma import ThreeBoilingDoubleMagma
from FourBoilingDoubleMagma import FourBoilingDoubleMagma
from Deaerator import Deaerator
from Turbine import Turbine
from MillTurbines import MillTurbines
from CanePrepTurbines import CanePrepTurbines
from AuxillaryTurbines import AuxillaryTurbines
from Boiler import Boiler
from time import time
from PreEvaporator import PreEvaporator
from CoolingTowerSystem import CoolingTowerSystem
from JuiceHeatingStation import JuiceHeatingStation
from Crystallizer_and_Reheater import Crystallizer, Reheater


start_time = time() * 1000 # in ms

# Print a header
print(f"{'='*60}")
print("ST MARY SUGAR MATERIAL AND ENERGY BALANCE - PYTHON")
print(f"{'='*60}")
print(f'\n\n')

# create a workbook
wb = new_workbook()

# Global Variables
fabrication_exhaust_psia = 30 # global variable

# First solve the mill floor material balance
st_mary_mills = MillFloor(
    cane_tpd=19000,
    cane_pol_pct=13.5,
    cane_fiber_pct=14,
    imbibition_pct_on_cane=30,
    bagasse_pol_pct=2.1,
    last_roll_purity=72,
    bagasse_moisture_pct=49.5,
    bagasse_ash_pct=5,
    mix_juice_purity=88,
    number_of_mills=6,
    juice_temp_F=90,
    mill_1_fiber_rise_load_fraction=0.35,
    name="Mill Floor"
)

st_mary_mills.neat_display()
st_mary_mills.display_mill_balances() # for maceration flows
st_mary_mills.to_excel(wb)

# now plug in numbers from mill floor into clarification balance

st_mary_clar = Clarification(
    mixed_juice_stream=st_mary_mills.mixed_juice_stream,
    cane_tpd=st_mary_mills.cane_tpd,
    filter_wash_water_pct_on_cane=5,
    filter_cake_pct_on_cane=5.0,
    filter_cake_pol_pct=2.4,
    clarified_juice_purity=88.5,
    limed_juice_cold_temp_f=95,
    limed_juice_hot_temp_f=220,
    clarified_juice_temp_f=205,
    lime_lb_per_ton_cane=1.3,
    lime_baume=10,
    polymer_conc_ppm=5000,
    polymer_lb_per_ton_cane=0.045,
    clarifier_underflow_pct_cane=20,
    name="Clarification"
)

st_mary_clar.neat_display()
st_mary_clar.to_excel(wb)

# Juice Heater Section
juice_T_out = st_mary_clar.limed_juice_hot_temp_f
cold_juice = st_mary_clar.limed_juice_cold_stream

# build template heaters
v1_heaters = JuiceHeaterShellTube(
    cold_stream=cold_juice, 
    hot_stream=SteamStream(x=1, P=fabrication_exhaust_psia), 
    name='V1 Heaters', 
    juice_out_temp_degF=juice_T_out,
    U_btu_per_ft2_degF=200,
    installed_area_ft2=11000
)

exh_heaters = JuiceHeaterShellTube(
    cold_stream=cold_juice,
    hot_stream=SteamStream(x=1, P=fabrication_exhaust_psia),
    juice_out_temp_degF=juice_T_out,
    U_btu_per_ft2_degF=200,
    installed_area_ft2=5000
)

par_heaters = JuiceHeatingStation(
    cold_stream=cold_juice,
    heaters=[v1_heaters, exh_heaters],
    mode='parallel',
    split_pcts=[75, 25], # 75% of the juice goes to the v1_heaters
    name='Parallel Juice Heating Station'
)

par_heaters.neat_display()
par_heaters.to_excel(wb)

# Now for the Clarified Juice Heater
# Note that a shell and tube heater for calculations is the same, will update this later on
clar_juice_colder = SugarStream.copy(st_mary_clar.clarified_juice_stream) # so my temp update won't effect this heaters calculations

clar_juice_heater = JuiceHeaterShellTube(
    cold_stream=clar_juice_colder, 
    hot_stream=SteamStream(x=1, P=fabrication_exhaust_psia), # uses exhaust steam
    name="Clarified Juice Heater",
    juice_out_temp_degF=225,
    U_btu_per_ft2_degF=185,
    installed_area_ft2=6000
)
clar_juice_heater.neat_display()
clar_juice_heater.to_excel(wb)

st_mary_clar.clarified_juice_stream.temp_deg_F = clar_juice_heater.juice_out_temp_degF

# Now make syrup for the pan floor
syrup_brix = 65 # User defined

# Simple mass balance
syrup_lb_hr = (st_mary_clar.clarified_juice_stream.flow_lb_per_hr 
               * st_mary_clar.clarified_juice_stream.brix / syrup_brix)

syrup = SugarStream.copy(st_mary_clar.clarified_juice_stream)
syrup.flow_lb_per_hr = syrup_lb_hr
syrup.brix = syrup_brix

# Now solve pan floor
# User decides which scheme to use
boiling_scheme = 'FBDM' # use TBDM for three boiling double magma, FBDM for four boiling double magma
# Using the Three Boiling Double Magma class

if boiling_scheme == 'TBDM':
    pan_floor = ThreeBoilingDoubleMagma(
        syrup=syrup,
        A_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=22500,
            inches_vacuum=23.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=92,
            ml_purity=73,
            calandria_pressure_psia=21.696,   # V1 (7 psig)
            heat_loss_factor=0.02, name='A Pans'),
        B_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=7500,
            inches_vacuum=25,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=94,
            ml_purity=53,
            calandria_pressure_psia=29.696,   # Exhaust (15 psig)
            heat_loss_factor=0.05, name='B Pans'),
        grain_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=3000,
            inches_vacuum=25.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=88,
            ml_purity=45,
            calandria_pressure_psia=29.696,   # Exhaust (15 psig)
            heat_loss_factor=0.05, name='Grain Pans'),
        C_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=12000,
            inches_vacuum=26.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=95.5,
            ml_purity=33,
            calandria_pressure_psia=21.696,   # V1 (7 psig)
            heat_loss_factor=0.05, name='C Pans'),
        A_centrifugals=Centrifugal(
            massecuite=None, massecuite_flow_lb_hr=0, 
            target_molasses_brix=82, purity_rise=0, 
            sugar_moisture=0.2, sugar_purity=99.7, 
            sugar_temp=150, molasses_temp=145, name="A Centrifugals"),
        B_centrifugals=Centrifugal(
            massecuite=None, massecuite_flow_lb_hr=0, 
            target_molasses_brix=82, purity_rise=0, 
            sugar_moisture=5, sugar_purity=92, 
            sugar_temp=150, molasses_temp=145, name="B Centrifugals"),
        C_centrifugals=Centrifugal(
            massecuite=None, massecuite_flow_lb_hr=0, 
            target_molasses_brix=82, purity_rise=0,
            sugar_moisture=5, sugar_purity=82, 
            sugar_temp=150, molasses_temp=145, name="C Centrifugals"),
        C_crystallizers=Crystallizer(massecuite_in=None, massecuite_flow_lb_hr=0,
                                     masse_temp_out_deg_F=120, ml_purity_out=30,
                                     water_temp_in_deg_F=85, water_temp_out_deg_F=105,
                                     name="C Crystallizers"),
        C_reheaters=Reheater(massecuite_in=None, massecuite_flow_lb_hr=0,
                             masse_temp_out_deg_F=140,
                             water_temp_in_deg_F=150, water_temp_out_deg_F=135,
                             name="C Reheaters"),
        b_magma_remelt_pct=20,
        c_magma_remelt_pct=20,
        a_mol_to_grain_pct=3,
        b_mol_to_grain_pct=10,
        syrup_to_grain_pct=1,
        a_mol_top_off_pct=0
    )

# for Four Boiling
if boiling_scheme == 'FBDM':
    pan_floor = FourBoilingDoubleMagma(
        syrup=syrup,
        A1_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=16000,
            inches_vacuum=23.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=92,
            ml_purity=75,
            calandria_pressure_psia=21.696,
            heat_loss_factor=0.02, name='A1 Pans'),
        A2_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=6000,
            inches_vacuum=23.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=92,
            ml_purity=70,
            calandria_pressure_psia=21.696,
            heat_loss_factor=0.02, name='A2 Pans'),
        B_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=7500,
            inches_vacuum=25,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=94,
            ml_purity=52,
            calandria_pressure_psia=29.696,
            heat_loss_factor=0.05, name='B Pans'),
        grain_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=3000,
            inches_vacuum=25.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=88,
            ml_purity=45,
            calandria_pressure_psia=29.696,
            heat_loss_factor=0.05, name='Grain Pans'),
        C_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=12000,
            inches_vacuum=26.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=95.5,
            ml_purity=33,
            calandria_pressure_psia=21.696,
            heat_loss_factor=0.05, name='C Pans'),
        A1_centrifugals=Centrifugal(
            massecuite=None, massecuite_flow_lb_hr=0,
            target_molasses_brix=82, purity_rise=0,
            sugar_moisture=0.2, sugar_purity=99.7,
            sugar_temp=150, molasses_temp=145, name="A1 Centrifugals"),
        A2_centrifugals=Centrifugal(
            massecuite=None, massecuite_flow_lb_hr=0,
            target_molasses_brix=82, purity_rise=0,
            sugar_moisture=0.2, sugar_purity=99.3,
            sugar_temp=150, molasses_temp=145, name="A2 Centrifugals"),
        B_centrifugals=Centrifugal(
            massecuite=None, massecuite_flow_lb_hr=0,
            target_molasses_brix=82, purity_rise=0,
            sugar_moisture=5, sugar_purity=92,
            sugar_temp=150, molasses_temp=145, name="B Centrifugals"),
        C_centrifugals=Centrifugal(
            massecuite=None, massecuite_flow_lb_hr=0,
            target_molasses_brix=82, purity_rise=0,
            sugar_moisture=5, sugar_purity=82,
            sugar_temp=150, molasses_temp=145, name="C Centrifugals"),
        C_crystallizers=Crystallizer(
            massecuite_in=None, massecuite_flow_lb_hr=0,
            masse_temp_out_deg_F=120, ml_purity_out=30,
            water_temp_in_deg_F=85, water_temp_out_deg_F=105,
            name="C Crystallizers"),
        C_reheaters=Reheater(
            massecuite_in=None, massecuite_flow_lb_hr=0,
            masse_temp_out_deg_F=140,
            water_temp_in_deg_F=150, water_temp_out_deg_F=135,
            name="C Reheaters"),
        syrup_to_A1_pans_pct=75,
        syrup_to_A2_pans_pct=20, # remainder goes to grain pans
        a1_mol_to_A2_pct=80,
        a1_mol_to_grain_pct=3,
        a2_mol_to_grain_pct=0,
        b_mol_to_grain_pct=10,
        b_magma_A1_footing_pct=40,
        b_magma_A2_footing_pct=40, # remaining goes to remelt
        c_magma_B_footing_pct=80, # remaining goes to remelt
        iterations=15,
    )

pan_floor.neat_display()
pan_floor.to_excel(wb)

# Now solve Evaporation since steam demands are known

# Clarified Juice Heater juice as supply to Pre 3
juice_to_pre = st_mary_clar.clarified_juice_stream

# Vapor bleeds distribution
# Pre will take the lionshare of bleeding, followed by S1E1, S2E1
# V2 is not done in this balance, but if you desire, distribute according to heating surfaces
v1_distr = [80, 13, 7] # Pre3, S1E1, S2E1
v1_demand = (
    par_heaters.heaters[0].steam_required_lb_per_hr # V1 Heaters
    + pan_floor.A1_pans.steam_flow_lb_hr            # A1 Pans
    + pan_floor.A2_pans.steam_flow_lb_hr            # A2 Pans
    + pan_floor.C_pans.steam_flow_lb_hr             # C Pans
)
v1_flows = [perc * v1_demand / 100 for perc in v1_distr] # stopped working here

pre_3 = PreEvaporator(
    juice_in=st_mary_clar.clarified_juice_stream,
    supply_steam=EvaporatorSteam(P_psia=fabrication_exhaust_psia),
    vapor_bleed_lb_per_hr=primary_heaters.steam_required_lb_per_hr
)


# Define vapor demands
v1_demand = (
     
    + pan_floor.A_pans.steam_flow_lb_hr 
    + pan_floor.C_pans.steam_flow_lb_hr
)

# Estimate distribution of vapors
v1_set1 = v1_demand * 0.65 # 65 % from set 1
v1_set2 = v1_demand - v1_set1 # pause here

evap_station = solve_evaporator_sets(  # This returns a list
        # ── Clarified juice feed ───────────────────────────────────────────
        juice_brix=st_mary_clar.clarified_juice_stream.brix,
        juice_purity=st_mary_clar.clarified_juice_stream.purity,
        juice_flow_lb_per_hr=st_mary_clar.clarified_juice_stream.flow_lb_per_hr,
        juice_temp_deg_F=st_mary_clar.clarified_juice_stream.temp_deg_F,
        juice_pressure_psia=40, # User input

        # ── Global defaults (override per set in set_configs if needed) ────
        target_brix_out=syrup.brix,
        dessin_coefficient=18000, # User input
        liquid_level_ft=2, # User input

        # ── Iteration control ──────────────────────────────────────────────
        n_iterations=10, # default 10
        dampening=0.2, # default 0.2

        # ── Set configurations ─────────────────────────────────────────────
        # Each dict needs: effect_areas_ft2, supply_steam_psia, last_effect_psia
        # Optional per-set overrides: vapor_bleeds, target_brix_out,
        #                             dessin_coefficient, liquid_level_ft, name
        set_configs=[
            {
                "name": "Set 1 (4-eff 25k ft²)", # User input
                "effect_areas_ft2": [25000, 25000, 25000, 25000], # User input
                "supply_steam_psia": fabrication_exhaust_psia, #  User input, use global exhaust pressure or a pressure lower to simulate control valve
                "last_effect_psia": 2.4, #~25" vac # User input
                "vapor_bleeds": [v1_set1], # User input
            },
            {
                "name": "Set 2 (4-eff 12k ft²)", # User input
                "effect_areas_ft2": [12000, 12000, 12000, 12000], # User input
                "supply_steam_psia": fabrication_exhaust_psia, # User input, use global exhaust pressure or a pressure lower to simulate control valve
                "last_effect_psia": 2.4, # User input
                "vapor_bleeds": [v1_set2], # User input
            },
            {
                "name": "Set 3 (3-eff 11-9k ft²)", # User input
                "effect_areas_ft2": [11000, 9000, 9000], # User input
                "supply_steam_psia": 20, # User input, use global exhaust pressure or a pressure lower to simulate control valve
                "last_effect_psia": 2.4, # User input
                "vapor_bleeds": [0] # User input
            },
        ],
        verbose=False, # Set True if you want iteration details, False if you just want final results
    ) # Note that this whole function shows all evaporator information

 

# Energy Balance Section
# Deaerator, assume a standard steam production value
da = Deaerator(deaerator_psig=10, water_in_deg_F=200, water_in_lb_hr=800_000, vent_pct=4)

exhaust_for_evaporators = sum([evap.supply_steam.flow_lb_per_hr for evap in evap_station])
exhaust_for_pans = pan_floor.B_pans.steam_flow_lb_hr + pan_floor.grain_pans.steam_flow_lb_hr
exhaust_for_heaters = secondary_heaters.steam_required_lb_per_hr + clar_juice_heater.steam_required_lb_per_hr
exhaust_for_da = da.steam_flow_lb_hr
subtotal_exh = exhaust_for_evaporators + exhaust_for_pans + exhaust_for_heaters + exhaust_for_da
exh_losses_pct = 5 # percent of subtotal User Input
total_exhaust = subtotal_exh + exh_losses_pct / 100 * subtotal_exh

exh_dict = {
    'Exhaust for Evaporators': exhaust_for_evaporators,
    'Exhausr for Pans': exhaust_for_pans,
    'Exhaust for Heaters': exhaust_for_heaters,
    'Exhaust for Deaerator': exhaust_for_da,
    'Exhaust Losses': subtotal_exh * exh_losses_pct / 100,
    'Total Exhaust': total_exhaust,
}

print(f"\n")
for key, item in exh_dict.items():
    print(f"{key}: {item:,.0f} lb/hr")
print(f"\n")

# Now steam demand from turbines
# Cane Preparation
knife_live_steam = SteamStream(P=180, x=1) # about 165 psig
knife_exhaust_psia = 30 # about 15 psig
knife_turbine_eff = 50 # issentropic efficiency
knife_hp_ton_fiber_hr = 14 # hp per ton of fiber per hr
number_of_knives = 3 # User Input

ton_fiber_hr = st_mary_mills.cane_fiber_pct / 100 * st_mary_mills.cane_tph
knife_hp_demand = ton_fiber_hr * knife_hp_ton_fiber_hr

knife_turbine_list = []
for i in range(number_of_knives):
    name = f"Knife Number {i+1}"
    trb = Turbine(
        inlet_steam=knife_live_steam, 
        outlet_pressure_psia=knife_exhaust_psia, 
        isentropic_efficiency=knife_turbine_eff / 100, # in decimal form
        hp_demand=knife_hp_demand,
        name=name
        )
    knife_turbine_list.append(trb)
    trb.neat_display()
    
live_steam_subtotal = sum([trb.steam_flow_lb_hr for trb in knife_turbine_list])
exhaust_available = sum([trb.exhaust_available for trb in knife_turbine_list])

# Mill Floor Turbines
mill_live_steam = SteamStream(P=175, x=1) # about 160 psig
mill_exhaust_psia = 30 # about 15 psig
hp_fib_hr_mill_1 = 16 # first mill hp per ton fiber per hr
hp_fib_hr_mill_last = 16 # last mill hp per ton fiber per hr
hp_fib_hr_int_mill = 14 # intermediate mill hp per ton fiber per hr
mill_turbine_eff = 50 # isentropic efficiency for mill turbine

n_mills = st_mary_mills.number_of_mills

mill_turbine_list = []
for i in range(n_mills):
    name = f"Mill Number {i+1}"
    if i == 0:
        hp_mill_n = hp_fib_hr_mill_1 * ton_fiber_hr
    elif i == n_mills - 1:
        hp_mill_n = hp_fib_hr_mill_last * ton_fiber_hr
    else:
        hp_mill_n = hp_fib_hr_int_mill * ton_fiber_hr
    trb = Turbine(
        inlet_steam=mill_live_steam, 
        outlet_pressure_psia=mill_exhaust_psia, 
        isentropic_efficiency=mill_turbine_eff / 100, # in decimal form
        hp_demand=hp_mill_n,
        name=name
        )
    mill_turbine_list.append(trb)
    trb.neat_display()

live_steam_subtotal += sum([trb.steam_flow_lb_hr for trb in mill_turbine_list])
exhaust_available += sum([trb.exhaust_available for trb in mill_turbine_list])

# Misc Turbines
misc_live_steam = SteamStream(P=175, x=1) # about 160 psig
misc_exhaust_psia = 30 # about 15 psig

id_fan_123 = Turbine(
    inlet_steam=misc_live_steam, 
    outlet_pressure_psia=misc_exhaust_psia, 
    isentropic_efficiency=50 / 100, # in decimal form
    hp_demand=750,
    name='123 ID Fan'
    )
id_fan_123.neat_display()
live_steam_subtotal += id_fan_123.steam_flow_lb_hr
exhaust_available += id_fan_123.exhaust_available

id_fan_4 = Turbine(
    inlet_steam=misc_live_steam, 
    outlet_pressure_psia=misc_exhaust_psia, 
    isentropic_efficiency=50 / 100, # in decimal form
    hp_demand=235,
    name='4 ID Fan'
    )
id_fan_4.neat_display()
live_steam_subtotal += id_fan_4.steam_flow_lb_hr
exhaust_available += id_fan_4.exhaust_available

id_fan_5 = Turbine(
    inlet_steam=misc_live_steam, 
    outlet_pressure_psia=misc_exhaust_psia, 
    isentropic_efficiency=50 / 100, # in decimal form
    hp_demand=400,
    name='5 ID Fan'
    )
id_fan_5.neat_display()
live_steam_subtotal += id_fan_5.steam_flow_lb_hr
exhaust_available += id_fan_5.exhaust_available

id_fan_6 = Turbine(
    inlet_steam=misc_live_steam, 
    outlet_pressure_psia=misc_exhaust_psia, 
    isentropic_efficiency=50 / 100, # in decimal form
    hp_demand=795,
    name='6 ID Fan'
    )
id_fan_6.neat_display()
live_steam_subtotal += id_fan_6.steam_flow_lb_hr
exhaust_available += id_fan_6.exhaust_available

fd_fan_7 = Turbine(
    inlet_steam=misc_live_steam, 
    outlet_pressure_psia=misc_exhaust_psia, 
    isentropic_efficiency=50 / 100, # in decimal form
    hp_demand=233,
    name='7 FD Fan'
    )
fd_fan_7.neat_display()
live_steam_subtotal += fd_fan_7.steam_flow_lb_hr
exhaust_available += fd_fan_7.exhaust_available

id_fan_7 = Turbine(
    inlet_steam=misc_live_steam, 
    outlet_pressure_psia=misc_exhaust_psia, 
    isentropic_efficiency=50 / 100, # in decimal form
    hp_demand=1200,
    name='7 ID Fan'
    )
id_fan_7.neat_display()
live_steam_subtotal += id_fan_7.steam_flow_lb_hr
exhaust_available += id_fan_7.exhaust_available

fd_fan_8 = Turbine(
    inlet_steam=misc_live_steam, 
    outlet_pressure_psia=misc_exhaust_psia, 
    isentropic_efficiency=50 / 100, # in decimal form
    hp_demand=350,
    name='8 FD Fan'
    )
fd_fan_8.neat_display()
live_steam_subtotal += fd_fan_8.steam_flow_lb_hr
exhaust_available += fd_fan_8.exhaust_available

id_fan_8 = Turbine(
    inlet_steam=misc_live_steam, 
    outlet_pressure_psia=misc_exhaust_psia, 
    isentropic_efficiency=50 / 100, # in decimal form
    hp_demand=1300,
    name='8 ID Fan'
    )
id_fan_8.neat_display()
live_steam_subtotal += id_fan_8.steam_flow_lb_hr
exhaust_available += id_fan_8.exhaust_available

bfw_pump_1 = Turbine(
    inlet_steam=misc_live_steam, 
    outlet_pressure_psia=misc_exhaust_psia, 
    isentropic_efficiency=50 / 100, # in decimal form
    hp_demand=400,
    name='Boiler Feed Water Pump 1'
    )
bfw_pump_1.neat_display()
live_steam_subtotal += bfw_pump_1.steam_flow_lb_hr
exhaust_available += bfw_pump_1.exhaust_available

bfw_pump_2 = Turbine(
    inlet_steam=misc_live_steam, 
    outlet_pressure_psia=misc_exhaust_psia, 
    isentropic_efficiency=50 / 100, # in decimal form
    hp_demand=400,
    name='Boiler Feed Water Pump 2'
    )
bfw_pump_2.neat_display()
live_steam_subtotal += bfw_pump_2.steam_flow_lb_hr
exhaust_available += bfw_pump_2.exhaust_available

juice_pump = Turbine(
    inlet_steam=misc_live_steam, 
    outlet_pressure_psia=misc_exhaust_psia, 
    isentropic_efficiency=50 / 100, # in decimal form
    hp_demand=400,
    name='Limed Juice Pump'
    )
juice_pump.neat_display()
live_steam_subtotal += juice_pump.steam_flow_lb_hr
exhaust_available += juice_pump.exhaust_available

# Losses and steam jets
live_steam_jets_lb_hr = 25000 # lb/hr
live_steam_subtotal += live_steam_jets_lb_hr

live_steam_loss_pct = 5 # percent of subtotal
live_steam_loss_lb_hr = live_steam_subtotal * live_steam_loss_pct / 100

# total
live_steam_total_lb_hr = live_steam_subtotal + live_steam_loss_lb_hr

# required Makeup
makeup_steam = total_exhaust - exhaust_available if total_exhaust > exhaust_available else 0

print(f"\nSteam Summary")
print(f"Total Live Steam Demand:           {live_steam_total_lb_hr:,.0f} lb/hr")
print(f"Exhaust Required:                  {total_exhaust:,.0f} lb/hr")
print(f"Exhaust Available from turbines:   {exhaust_available:,.0f} lb/hr")
print(f"Makeup Required:                   {makeup_steam:,.0f} lb/hr")

# Now for steam available from boilerroom
blrs = Boiler(
    bagasse=st_mary_mills.bagasse_stream,
    efficiency=60,
    pressure_psig=185,
    deg_superheat=0,
    feed_water_temp=da.water_out.T,
    capacity=900_000,
    name="All Boilers"
)

blrs.neat_display()

end_time = time() * 1000 # in ms
solve_time = end_time - start_time
print(f"\n\nTime to solve factory balance {solve_time:,.2f} ms")

