# This is an example usage for setting up your solver

# import all neccesary items

from MillFloor import MillFloor
from Clarification import Clarification
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
from ThreeBoilingDoubleMagma import ThreeBoilingDoubleMagma

# First solve the mill floor material balance
st_mary_mills = MillFloor(
    cane_tpd=17000,
    cane_pol_pct=13.5,
    cane_fiber_pct=14,
    imbibition_pct_on_cane=25,
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

primary_heaters = JuiceHeaterShellTube(
    cold_stream=st_mary_clar.limed_juice_cold_stream,
    hot_stream=SteamStream(x=1, P=21), # can update after solving evaporators
    name="Primary Heaters",
    juice_out_temp_degF=175,
    U_btu_per_ft2_degF=220,
    installed_area_ft2=8000
)

primary_heaters.neat_display()

secondary_heaters = JuiceHeaterShellTube(
    cold_stream=primary_heaters.juice_out,
    hot_stream=SteamStream(x=1, P=30), # using exhaust steam
    juice_out_temp_degF=st_mary_clar.limed_juice_hot_temp_f, # defined earlier
    U_btu_per_ft2_degF=220,
    installed_area_ft2=8000,
    name="Secondary Heaters"
)

secondary_heaters.neat_display()

# Now make syrup for the pan floor

syrup_brix = 65 # User defined

# Simple mass balance
syrup_lb_hr = (st_mary_clar.clarified_juice_stream.flow_lb_per_hr 
               * st_mary_clar.clarified_juice_stream.brix / syrup_brix)

syrup = SugarStream.copy(st_mary_clar.clarified_juice_stream)
syrup.flow_lb_per_hr = syrup_lb_hr
syrup.brix = syrup_brix

# Now solve pan floor
# Using the Three Boiling Double Magma class
pan_floor = ThreeBoilingDoubleMagma(
        syrup=syrup,
        A_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=22500,
            inches_vacuum=23.5,
            supersaturation=1.2,
            head_ft=1,
            masse_brix=92,
            ml_purity=74,
            calandria_pressure_psia=21.696,   # V1 (7 psig)
            heat_loss_factor=0.02, name='A Pans'),
        B_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=7500,
            inches_vacuum=25,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=94,
            ml_purity=48,
            calandria_pressure_psia=29.696,   # Exhaust (15 psig)
            heat_loss_factor=0.05, name='B Pans'),
        grain_pans=Pan(
            feed_streams=None,
            heating_surface_ft2=3000,
            inches_vacuum=25.5,
            supersaturation=1.2,
            head_ft=2,
            masse_brix=88,
            ml_purity=39,
            calandria_pressure_psia=29.696,   # Exhaust (15 psig)
            heat_loss_factor=0.05, name='grain Pans'),
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
        A_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=70, purity_rise=0, 
                                   sugar_moisture=0.2, sugar_purity=99.7, sugar_temp=150, molasses_temp=145, name="A Centrifugals"),
        B_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=70, purity_rise=0, 
                                   sugar_moisture=5, sugar_purity=92, sugar_temp=150, molasses_temp=145, name="B Centrifugals"),
        C_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=83, purity_rise=0, 
                                   sugar_moisture=5, sugar_purity=82, sugar_temp=150, molasses_temp=145, name="C Centrifugals"),
        b_magma_remelt_pct=20,
        c_magma_remelt_pct=20,
        a_mol_to_grain_pct=3,
        b_mol_to_grain_pct=10,
        syrup_to_grain_pct=1,
        a_mol_top_off_pct=0
    )

# Now solve Evaporation since steam demands are known
# No pre or clear juice heater in this balance

# Define vapor demands
v1_demand = (
    primary_heaters.steam_required_lb_per_hr 
    + pan_floor.A_pans.steam_flow_lb_hr 
    + pan_floor.C_pans.steam_flow_lb_hr
)

# Estimate distribution of vapors
v1_set1 = v1_demand * 0.65 # 65 % from set 1
v1_set2 = v1_demand - v1_set1 # pause here

evap_station = solve_evaporator_sets(
        # ── Clarified juice feed ───────────────────────────────────────────
        juice_brix=st_mary_clar.clarified_juice_stream.brix,
        juice_purity=st_mary_clar.clarified_juice_stream.purity,
        juice_flow_lb_per_hr=st_mary_clar.clarified_juice_stream.flow_lb_per_hr,
        juice_temp_deg_F=st_mary_clar.clarified_juice_stream.temp_deg_F,
        juice_pressure_psia=40, # User input

        # ── Global defaults (override per set in set_configs if needed) ────
        target_brix_out=syrup.brix,
        dessin_coefficient=18000, # input
        liquid_level_ft=2, # input

        # ── Iteration control ──────────────────────────────────────────────
        n_iterations=10,
        dampening=0.2,

        # ── Set configurations ─────────────────────────────────────────────
        # Each dict needs: effect_areas_ft2, supply_steam_psia, last_effect_psia
        # Optional per-set overrides: vapor_bleeds, target_brix_out,
        #                             dessin_coefficient, liquid_level_ft, name
        set_configs=[
            {
                "name": "Set 1 (4-eff 25k ft²)",
                "effect_areas_ft2": [25000, 25000, 25000, 25000],
                "supply_steam_psia": 30, # ~15psig
                "last_effect_psia": 2.4, #~25" vac
                "vapor_bleeds": [primary_heaters.steam_required_lb_per_hr],
            },
            {
                "name": "Set 2 (4-eff 12k ft²)",
                "effect_areas_ft2": [12000, 12000, 12000, 12000],
                "supply_steam_psia": 30,
                "last_effect_psia": 2.4,
                "vapor_bleeds": [50000, 20000],
            },
            {
                "name": "Set 3 (3-eff 11-9k ft²)",
                "effect_areas_ft2": [11000, 9000, 9000],
                "supply_steam_psia": 20,
                "last_effect_psia": 2.4,
                "vapor_bleeds": [50000]
            },
        ],
    )

pan_floor.display_balance()