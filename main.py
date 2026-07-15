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

sys.stdout = _Tee('output.txt')  # The output file name

# import all neccesary items

from excel_export import new_workbook, SheetWriter
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
from steam_summary_excel import steam_summary_to_excel
from condensate_balance import CondensateBalance, CondensateDemand
from condensate_utils import flash_condensate


start_time = time() * 1000  # in ms

# Print a header
print(f"{'='*60}")
print("ST MARY SUGAR MATERIAL AND ENERGY BALANCE - PYTHON")
print(f"{'='*60}")
print(f'\n\n')

# create a workbook
wb = new_workbook()

# Global Variables
fabrication_exhaust_psia = 30  # global variable

# ============================================================
# MILL FLOOR
# ============================================================
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
    name="Mill Floor",
)

st_mary_mills.neat_display()
st_mary_mills.display_mill_balances()  # for maceration flows
st_mary_mills.to_excel(wb)

# ============================================================
# CLARIFICATION
# ============================================================
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
    name="Clarification",
)

st_mary_clar.neat_display()
st_mary_clar.to_excel(wb)

# ============================================================
# JUICE HEATERS
# ============================================================
juice_T_out = st_mary_clar.limed_juice_hot_temp_f
cold_juice = st_mary_clar.limed_juice_cold_stream

# build template heaters
v1_heaters = JuiceHeaterShellTube(
    cold_stream=cold_juice,
    hot_stream=SteamStream(x=1, P=fabrication_exhaust_psia),
    name='V1 Heaters',
    juice_out_temp_degF=juice_T_out,
    U_btu_per_ft2_degF=200,
    installed_area_ft2=11000,
    steam_type=1,  # V1
)

exh_heaters = JuiceHeaterShellTube(
    cold_stream=cold_juice,
    hot_stream=SteamStream(x=1, P=fabrication_exhaust_psia),
    name='Exhaust Heaters',
    juice_out_temp_degF=juice_T_out,
    U_btu_per_ft2_degF=200,
    installed_area_ft2=5000,
    steam_type=0,  # Exhaust
)

par_heaters = JuiceHeatingStation(
    cold_stream=cold_juice,
    heaters=[v1_heaters, exh_heaters],
    mode='parallel',
    split_pcts=[75, 25],  # 75% of the juice goes to the v1_heaters
    name='Parallel Juice Heating Station',
)

par_heaters.neat_display()
par_heaters.to_excel(wb)

# Now for the Clarified Juice Heater
# Note that a shell and tube heater for calculations is the same, will update this later on
clar_juice_colder = SugarStream.copy(st_mary_clar.clarified_juice_stream)  # so my temp update won't effect this heaters calculations

clar_juice_heater = JuiceHeaterShellTube(
    cold_stream=clar_juice_colder,
    hot_stream=SteamStream(x=1, P=fabrication_exhaust_psia),  # uses exhaust steam
    name="Clarified Juice Heater",
    juice_out_temp_degF=225,
    U_btu_per_ft2_degF=185,
    installed_area_ft2=6000,
)
clar_juice_heater.neat_display()
clar_juice_heater.to_excel(wb)

st_mary_clar.clarified_juice_stream.temp_deg_F = clar_juice_heater.juice_out_temp_degF

# ============================================================
# PAN FLOOR
# ============================================================
# Now make syrup for the pan floor
syrup_brix = 65  # User defined

# Simple mass balance
syrup_lb_hr = (st_mary_clar.clarified_juice_stream.flow_lb_per_hr
               * st_mary_clar.clarified_juice_stream.brix / syrup_brix)

syrup = SugarStream.copy(st_mary_clar.clarified_juice_stream)
syrup.flow_lb_per_hr = syrup_lb_hr  # type: ignore
syrup.brix = syrup_brix

# Now solve pan floor
# User decides which scheme to use
boiling_scheme = 'FBDM'  # use TBDM for three boiling double magma, FBDM for four boiling double magma
# Using the Three Boiling Double Magma class

if boiling_scheme == 'TBDM':
    pan_floor = ThreeBoilingDoubleMagma(
        syrup=syrup,
        A_pans=Pan(feed_streams=None, heating_surface_ft2=22500, inches_vacuum=23.5, supersaturation=1.2,
            head_ft=2, masse_brix=92, ml_purity=73, calandria_pressure_psia=21.696, steam_type=1,  # V1 (7 psig)
            heat_loss_factor=0.02, name='A Pans'),
        B_pans=Pan(feed_streams=None, heating_surface_ft2=7500, inches_vacuum=25, supersaturation=1.2,
            head_ft=2, masse_brix=94, ml_purity=53, calandria_pressure_psia=29.696, steam_type=0,  # Exhaust (15 psig)
            heat_loss_factor=0.05, name='B Pans'),
        grain_pans=Pan(feed_streams=None, heating_surface_ft2=3000, inches_vacuum=25.5, supersaturation=1.2,
            head_ft=2, masse_brix=88, ml_purity=45, calandria_pressure_psia=29.696, steam_type=0,  # Exhaust (15 psig)
            heat_loss_factor=0.05, name='Grain Pans'),
        C_pans=Pan(feed_streams=None, heating_surface_ft2=12000, inches_vacuum=26.5, supersaturation=1.2,
            head_ft=2, masse_brix=95.5, ml_purity=33, calandria_pressure_psia=21.696, steam_type=1,  # V1 (7 psig)
            heat_loss_factor=0.05, name='C Pans'),
        A_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82,
            purity_rise=0, sugar_moisture=0.2, sugar_purity=99.7, sugar_temp=150, molasses_temp=145,
            name="A Centrifugals"),
        B_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82,
            purity_rise=0, sugar_moisture=5, sugar_purity=92, sugar_temp=150, molasses_temp=145,
            name="B Centrifugals"),
        C_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82,
            purity_rise=0, sugar_moisture=5, sugar_purity=82, sugar_temp=150, molasses_temp=145,
            name="C Centrifugals"),
        C_crystallizers=Crystallizer(massecuite_in=None, massecuite_flow_lb_hr=0, masse_temp_out_deg_F=120,  # type: ignore
            ml_purity_out=30, water_temp_in_deg_F=85, water_temp_out_deg_F=105, name="C Crystallizers"),
        C_reheaters=Reheater(massecuite_in=None, massecuite_flow_lb_hr=0, masse_temp_out_deg_F=140,  # type: ignore
            water_temp_in_deg_F=150, water_temp_out_deg_F=135, name="C Reheaters"),
        b_magma_remelt_pct=20,
        c_magma_remelt_pct=20,
        a_mol_to_grain_pct=3,
        b_mol_to_grain_pct=10,
        syrup_to_grain_pct=1,
        a_mol_top_off_pct=0,
    )

# for Four Boiling
if boiling_scheme == 'FBDM':
    pan_floor = FourBoilingDoubleMagma(
        syrup=syrup,
        A1_pans=Pan(feed_streams=None, heating_surface_ft2=16000, inches_vacuum=23.5, supersaturation=1.2,
            head_ft=2, masse_brix=92, ml_purity=75, calandria_pressure_psia=21.696, steam_type=1,  # V1
            heat_loss_factor=0.02, name='A1 Pans'),
        A2_pans=Pan(feed_streams=None, heating_surface_ft2=6000, inches_vacuum=23.5, supersaturation=1.2,
            head_ft=2, masse_brix=92, ml_purity=70, calandria_pressure_psia=21.696, steam_type=1,  # V1
            heat_loss_factor=0.02, name='A2 Pans'),
        B_pans=Pan(feed_streams=None, heating_surface_ft2=7500, inches_vacuum=25, supersaturation=1.2,
            head_ft=2, masse_brix=94, ml_purity=52, calandria_pressure_psia=29.696, steam_type=0,  # Exhaust
            heat_loss_factor=0.05, name='B Pans'),
        grain_pans=Pan(feed_streams=None, heating_surface_ft2=3000, inches_vacuum=25.5, supersaturation=1.2,
            head_ft=2, masse_brix=88, ml_purity=45, calandria_pressure_psia=29.696, steam_type=0,  # Exhaust
            heat_loss_factor=0.05, name='Grain Pans'),
        C_pans=Pan(feed_streams=None, heating_surface_ft2=12000, inches_vacuum=26.5, supersaturation=1.2,
            head_ft=2, masse_brix=95.5, ml_purity=33, calandria_pressure_psia=21.696, steam_type=1,  # V1
            heat_loss_factor=0.05, name='C Pans'),
        A1_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82,
            purity_rise=0, sugar_moisture=0.2, sugar_purity=99.7, sugar_temp=150, molasses_temp=145,
            name="A1 Centrifugals"),
        A2_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82,
            purity_rise=0, sugar_moisture=0.2, sugar_purity=99.3, sugar_temp=150, molasses_temp=145,
            name="A2 Centrifugals"),
        B_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82,
            purity_rise=0, sugar_moisture=5, sugar_purity=92, sugar_temp=150, molasses_temp=145,
            name="B Centrifugals"),
        C_centrifugals=Centrifugal(massecuite=None, massecuite_flow_lb_hr=0, target_molasses_brix=82,
            purity_rise=0, sugar_moisture=5, sugar_purity=82, sugar_temp=150, molasses_temp=145,
            name="C Centrifugals"),
        C_crystallizers=Crystallizer(massecuite_in=None, massecuite_flow_lb_hr=0, masse_temp_out_deg_F=120,
            ml_purity_out=30, water_temp_in_deg_F=85, water_temp_out_deg_F=105, name="C Crystallizers"),
        C_reheaters=Reheater(massecuite_in=None, massecuite_flow_lb_hr=0, masse_temp_out_deg_F=140,
            water_temp_in_deg_F=150, water_temp_out_deg_F=135, name="C Reheaters"),
        syrup_to_A1_pans_pct=75,
        syrup_to_A2_pans_pct=20,  # remainder goes to grain pans
        a1_mol_to_A2_pct=80,
        a1_mol_to_grain_pct=3,
        a2_mol_to_grain_pct=0,
        b_mol_to_grain_pct=10,
        b_magma_A1_footing_pct=40,
        b_magma_A2_footing_pct=40,  # remaining goes to remelt
        c_magma_B_footing_pct=80,  # remaining goes to remelt
        iterations=15,
    )

pan_floor.neat_display()  # type: ignore
pan_floor.to_excel(wb)  # pyright: ignore[reportPossiblyUnboundVariable]

# ============================================================
# EVAPORATION
# ============================================================
# Now solve Evaporation since steam demands are known

# Clarified Juice Heater juice as supply to Pre 3
juice_to_pre = SugarStream.copy(st_mary_clar.clarified_juice_stream)

# Vapor bleeds distribution
# Pre will take the lionshare of bleeding, followed by S1E1, S2E1
# V2 is not done in this balance, but if you desire, distribute according to heating surfaces
v1_distr = [80, 13, 7]  # Pre3, S1E1, S2E1 — must add up to 100
v1_demand = (
    par_heaters.total_V1_steam_lb_hr                # V1 Heaters
    + pan_floor.total_V1_steam_lb_hr                # V1 in pans
)
v1_flows = [perc * v1_demand / 100 for perc in v1_distr]  # [pre v1, s1e1 v1, s2e1 v1]

pre_3 = PreEvaporator(
    juice_in=juice_to_pre,
    supply_steam=EvaporatorSteam(P_psia=fabrication_exhaust_psia),
    vapor_bleed_lb_per_hr=v1_flows[0],  # refers to Pre 3 v1 bleed
    area_ft2=35000,
)
pre_3.to_excel(wb)

juice_to_sets = SugarStream.copy(pre_3.juice_out)

evap_station = solve_evaporator_sets(  # This returns a list
    # ── Clarified juice feed ───────────────────────────────────────────
    juice_brix=juice_to_sets.brix,
    juice_purity=juice_to_sets.purity,
    juice_flow_lb_per_hr=juice_to_sets.flow_lb_per_hr,
    juice_temp_deg_F=juice_to_sets.temp_deg_F,
    juice_pressure_psia=40,

    # ── Global defaults (override per set in set_configs if needed) ────
    target_brix_out=syrup.brix,
    dessin_coefficient=18000,
    liquid_level_ft=2,

    # ── Iteration control ──────────────────────────────────────────────
    n_iterations=10,  # default 10
    dampening=0.2,  # default 0.2

    # ── Set configurations ─────────────────────────────────────────────
    # Each dict needs: effect_areas_ft2, supply_steam_psia, last_effect_psia
    # Optional per-set overrides: vapor_bleeds, target_brix_out,
    #                             dessin_coefficient, liquid_level_ft, name
    set_configs=[
        {
            "name": "Set 1 (4-eff 25k ft²)",
            "effect_areas_ft2": [25000, 25000, 25000, 25000],
            "supply_steam_psia": fabrication_exhaust_psia,
            "last_effect_psia": 2.4,  # ~25" vac
            "vapor_bleeds": [v1_flows[1]],
        },
        {
            "name": "Set 2 (4-eff 12k ft²)",
            "effect_areas_ft2": [12000, 12000, 12000, 12000],
            "supply_steam_psia": fabrication_exhaust_psia,
            "last_effect_psia": 2.4,
            "vapor_bleeds": [v1_flows[2]],
        },
        {
            "name": "Set 3 (3-eff 11-9k ft²)",
            "effect_areas_ft2": [11000, 9000, 9000],
            "supply_steam_psia": 20,
            "last_effect_psia": 2.4,
            "vapor_bleeds": [0],
        },
    ],
    verbose=False,  # Set True if you want iteration details, False if you just want final results
)  # Note that this whole function shows all evaporator information

sets_to_excel(evap_station, workbook=wb)

# ============================================================
# ENERGY BALANCE - EXHAUST STEAM SUMMARY
# ============================================================
# Deaerator, assume a standard steam production value
da = Deaerator(deaerator_psig=10, water_in_deg_F=200, water_in_lb_hr=800_000, vent_pct=4)
da.to_excel(wb)

exhaust_for_Pre = pre_3.supply_steam.flow_lb_per_hr
exhaust_for_evaporators = sum([evap.supply_steam.flow_lb_per_hr for evap in evap_station])
exhaust_for_pans = pan_floor.total_exhaust_steam_lb_hr
exhaust_for_heaters = (
    par_heaters.total_exhaust_steam_lb_hr
    + clar_juice_heater.steam_required_lb_per_hr
)
exhaust_for_da = da.steam_flow_lb_hr
subtotal_exh = exhaust_for_Pre + exhaust_for_evaporators + exhaust_for_pans + exhaust_for_heaters + exhaust_for_da
exh_losses_pct = 5  # percent of subtotal User Input
total_exhaust_required = subtotal_exh + exh_losses_pct / 100 * subtotal_exh

exh_dict = {
    'Exhaust for Pre': exhaust_for_Pre,
    'Exhaust for Evaporators': exhaust_for_evaporators,
    'Exhaust for Pans': exhaust_for_pans,
    'Exhaust for Heaters': exhaust_for_heaters,
    'Exhaust for Deaerator': exhaust_for_da,
    'Exhaust Losses': subtotal_exh * exh_losses_pct / 100,
    'Total Exhaust Required': total_exhaust_required,
}


print(f"\n")
for key, item in exh_dict.items():
    print(f"{key}: {item:,.0f} lb/hr")
print(f"\n")

# ============================================================
# TURBINE STEAM DEMAND
# ============================================================
# Cane Preparation
tons_fiber_hr = st_mary_mills.cane_fiber_pct / 100 * st_mary_mills.cane_tph

knf_trbs = CanePrepTurbines(
    name_list            =['Knife 1', 'Knife 2', 'Knife 3'],
    hp_ton_fiber_hr      =[16,        16,        16],
    isentropic_efficiency=[50,        50,        50],
    live_steam_object=SteamStream(P=180, x=1),  # 165 psig
    exhaust_psia=30,  # 15 psig
    tons_fiber_hr=tons_fiber_hr,
)

live_steam_subtotal = knf_trbs.total_inlet_flow_lb_hr
exhaust_available = knf_trbs.total_exhaust_available_lb_hr
knf_trbs.to_excel(wb)
knf_trbs.neat_display()

# Mill Floor Turbines
mill_trbs = MillTurbines(
    hp_ton_fiber_hr      =[18, 16, 16, 16, 16, 18],
    isentropic_efficiency=[50, 50, 50, 50, 50, 50],
    live_steam_object=SteamStream(P=180, x=1),  # 165 psig
    exhaust_psia=30,
    tons_fiber_hr=tons_fiber_hr,
)

live_steam_subtotal += mill_trbs.total_inlet_flow_lb_hr
exhaust_available   += mill_trbs.total_exhaust_available_lb_hr
mill_trbs.to_excel(wb)
mill_trbs.neat_display()

# Misc Turbines
misc_trbs = AuxillaryTurbines(
    group_name='Fan and pump Turbines',
    name_list            =['ID 123', 'ID 4', 'ID 5', 'ID 6', 'ID 7', 'FD 7', 'ID 8', 'FD 8', 'BFW 1', 'BFW 2', 'BFW 3', 'JCE 1'],
    hp_list              =[750,      235,    400,    795,    1200,   233,    1300,   350,    400,     400,     400,     400],
    isentropic_efficiency=[50,       50,     50,     50,     50,     50,     50,     50,     50,      50,      50,      50],
    live_steam_object=SteamStream(P=180, x=1),  # 165 psig
    exhaust_psia=30,
)
live_steam_subtotal += misc_trbs.total_inlet_flow_lb_hr
exhaust_available += misc_trbs.total_exhaust_available_lb_hr
misc_trbs.to_excel(wb)
misc_trbs.neat_display()

# Losses and steam jets
live_steam_jets_lb_hr = 25000  # lb/hr Manual Input
live_steam_subtotal += live_steam_jets_lb_hr

live_steam_loss_pct = 2  # percent of subtotal
live_steam_loss_lb_hr = live_steam_subtotal * live_steam_loss_pct / 100

# total
live_steam_total_lb_hr = live_steam_subtotal + live_steam_loss_lb_hr

# required Makeup
makeup_steam = total_exhaust_required - exhaust_available if total_exhaust_required > exhaust_available else 0

live_steam_dict = {
    'Cane Prep Turbines': knf_trbs.total_inlet_flow_lb_hr,
    'Mill Turbines': mill_trbs.total_inlet_flow_lb_hr,
    'Fan and Pump Turbines': misc_trbs.total_inlet_flow_lb_hr,
    'Steam Jets': live_steam_jets_lb_hr,
    'Live Steam Losses': live_steam_loss_lb_hr,
    'Total Live Steam': live_steam_total_lb_hr,
}

print(f"\nSteam Summary")
print(f"Total Live Steam Demand:           {live_steam_total_lb_hr:,.0f} lb/hr")
print(f"Exhaust Required:                  {total_exhaust_required:,.0f} lb/hr")
print(f"Exhaust Available from turbines:   {exhaust_available:,.0f} lb/hr")
print(f"Makeup Required:                   {makeup_steam:,.0f} lb/hr")

# ============================================================
# BOILER ROOM
# ============================================================
blrs = Boiler(
    bagasse=st_mary_mills.bagasse_stream,
    efficiency=60,
    pressure_psig=185,
    deg_superheat=0,
    feed_water_temp=da.water_out.T,
    capacity=900_000,
    name="All Boilers",
)

blrs.neat_display()
blrs.to_excel(wb)

steam_summary_to_excel(
    wb, live_steam_dict, exh_dict,
    exhaust_available_lb_hr=exhaust_available,
    makeup_steam_lb_hr=makeup_steam,
    steam_available_lb_hr=blrs.steam_availabe_lb_hr,
)

# ============================================================
# COOLING TOWER
# ============================================================
condenser_list = pan_floor.pan_condensers
for evap in evap_station:
    condenser_list.append(evap.condenser)

ctwrs = CoolingTowerSystem(
    condensers=condenser_list,
    cool_water_temp_F=85,
    percent_blowdown=10,
    makeup_water_temp_F=70,
    iterations=20,
    name='Cooling Tower System',
)
ctwrs.neat_display()
ctwrs.to_excel(wb)

# ============================================================
# CONDENSATE BALANCE
# ============================================================
# Available condensate (clean exhaust vs. dirty V1-V4 / inter-effect vapor)
# vs. water demand locations. Supply and demand are reported independently
# for you to reconcile yourself.
clean_condensate_dict = {
    'Pre-Evaporator':                  pre_3.clean_condensate,
    'Evaporator Sets (Effect 1s)':      sum(evap.clean_condensate for evap in evap_station),
    'Pan Floor - Exhaust Pans':         pan_floor.clean_condensate,
    'Juice Heaters - Exhaust Station':  par_heaters.clean_condensate,
    'Clarified Juice Heater (Exhaust)': flash_condensate(clar_juice_heater.steam_required_lb_per_hr,
                                                          clar_juice_heater.hot_stream.T),
}
dirty_condensate_dict = {
    'Evaporator Sets (Effects 2+)': sum(evap.dirty_condensate for evap in evap_station),
    'Pan Floor - V1-V4 Pans':       pan_floor.dirty_condensate,
    'Juice Heaters - V1-V4 Station': par_heaters.dirty_condensate,
}

# Pan floor wash/dilution water split — total_water lumps centrifugal wash +
# magma minglers + remelt/molasses dilution together, so back out wash water
# (centrifugal names differ between the two boiling schemes).
if boiling_scheme == 'TBDM':
    pan_wash_water_lb_hr = (pan_floor.A_centrifugals.wash_water_lb_hr
                            + pan_floor.B_centrifugals.wash_water_lb_hr
                            + pan_floor.C_centrifugals.wash_water_lb_hr)
else:
    pan_wash_water_lb_hr = (pan_floor.A1_centrifugals.wash_water_lb_hr
                            + pan_floor.A2_centrifugals.wash_water_lb_hr
                            + pan_floor.B_centrifugals.wash_water_lb_hr
                            + pan_floor.C_centrifugals.wash_water_lb_hr)
pan_dilution_water_lb_hr = pan_floor.total_water.flow_lb_per_hr - pan_wash_water_lb_hr

condensate_demands = [
    CondensateDemand('Boiler Feed Water', flow_lb_hr=da.water_in_lb_hr, temp_F=da.water_in_deg_F,
        method='blended',
        note="Recommend usage of clean condensate, make up with minimal dirty condensate or well water"),
    CondensateDemand('Imbibition', flow_lb_hr=st_mary_mills.imbibition_lb_hr, temp_F=150,
        method='blended'),  # target temp - User Input
    CondensateDemand('Wash Water - Pans', flow_lb_hr=pan_wash_water_lb_hr, temp_F=180,
        method='cooled'),  # target temp - User Input
    CondensateDemand('Dilution Water - Pans/Molasses/Remelt', flow_lb_hr=pan_dilution_water_lb_hr,
        temp_F=150, method='blended'),  # target temp - User Input
]

condensate_balance = CondensateBalance(
    clean_condensate_dict, dirty_condensate_dict, condensate_demands,
    well_water_temp_F=ctwrs.makeup_water_temp_F,
    combined_condensate_temp_F=210,  # User Input - override with a measured value if known
    name='Condensate Balance',
)
condensate_balance.neat_display()
condensate_balance.to_excel(wb)

# ============================================================
# WRAP-UP
# ============================================================
end_time = time() * 1000  # in ms
solve_time = end_time - start_time
print(f"\n\nTime to solve factory balance {solve_time:,.2f} ms")

excel_name = 'main_balance.xlsx'
wb.save(filename=excel_name)
print(f"Excel Export save successful. Filename = '{excel_name}'")