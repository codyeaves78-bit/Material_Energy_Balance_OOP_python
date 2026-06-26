from Pan import Pan
from Centrifugal import Centrifugal
from SugarStream import SugarStream
from boiling_house_balance import display_balance
from time import time

def make_magma(sugar_stream: SugarStream, mingler_brix: float) -> SugarStream:
    magma = SugarStream.copy(sugar_stream)
    solids = magma.solids_flow
    magma.brix = mingler_brix
    magma.flow_lb_per_hr = solids / magma.brix * 100
    return magma # helper function

def make_remelt(magma=SugarStream(), remelt_brix=65):
    remelt = SugarStream.copy(magma)
    brix_flow = magma.solids_flow
    new_flow = brix_flow * 100 / remelt_brix
    new_brix = brix_flow / new_flow * 100
    remelt.flow_lb_per_hr = new_flow
    remelt.brix = new_brix
    return remelt

# create syrup
syrup = SugarStream(brix=65, purity=90, flow_lb_per_hr=100000, temp_deg_F=140, pressure_psia=14.7, level_ft=0)

# create dummy magma streams to start loop
c_magma_B_pans = SugarStream(brix=92, purity=85, flow_lb_per_hr=0, temp_deg_F=130)
b_magma_A_pans = SugarStream(brix=92, purity=92, flow_lb_per_hr=0, temp_deg_F=130)

# Set some syrup and A & B molasses distribution parameters
syrup_to_grain_pct = 5
syrup_to_A_pans_pct = 100 - syrup_to_grain_pct
syrup_to_A_pans = SugarStream.copy(syrup)
syrup_to_A_pans.flow_lb_per_hr = syrup_to_A_pans_pct / 100 * syrup.flow_lb_per_hr

syrup_to_grain = SugarStream.copy(syrup)
a_mol_to_grain_pct = 10
a_mol_top_off_pct = 20
a_mol_B_pans_pct = 100 - a_mol_top_off_pct - a_mol_to_grain_pct

b_mol_to_grain_pct = 10
b_mol_C_pans_pct = 100 - b_mol_to_grain_pct

# Define quantity of magma to be remelted
c_magma_rmlt_pct = 50
b_magma_rmlt_pct = 50

c_magma_foot = 100 - c_magma_rmlt_pct
b_magma_foot = 100 - b_magma_rmlt_pct

# Solve A pans, set up b magma with zero flow for initial solve, same for top off A molasses

top_off_a_mol = SugarStream(brix=70, purity=70, flow_lb_per_hr=0, temp_deg_F=140)


# Start loop
start_time = time() * 1000

for i in range(20):
        
    A_pans = Pan(
        feed_streams=[syrup_to_A_pans, b_magma_A_pans, top_off_a_mol],
        heating_surface_ft2=20000,
        inches_vacuum=23.5,
        supersaturation=1.2,
        head_ft=2,
        masse_brix=92,
        cry_yld_pct_brix=60,
        steam_type="V1",
        heat_loss_factor=0.05,
        calandria_steam_temp_F=235,
        name='A Pans'
        )

    A_centrifugals = Centrifugal(
        massecuite=A_pans.massecuite,
        massecuite_flow_lb_hr=A_pans.massecuite_flow_lb_hr,
        target_molasses_brix=83,
        purity_rise=2,
        sugar_purity=99.7,
        sugar_moisture=0.17,
        name="A Machines",
        sugar_temp=140,
        molasses_temp=150
    )

    A_centrifugals.molasses_stream.temp_deg_F = 150 # adjust temp to reflect measured conditions

    top_off_a_mol = SugarStream.copy(A_centrifugals.molasses_stream)
    top_off_a_mol.flow_lb_per_hr = a_mol_top_off_pct / 100 * top_off_a_mol.flow_lb_per_hr

    a_mol_B_pans = SugarStream.copy(A_centrifugals.molasses_stream)
    a_mol_B_pans.flow_lb_per_hr = a_mol_B_pans_pct / 100 * a_mol_B_pans.flow_lb_per_hr

    # Solve B pans, make dummy c magma stream


    B_pans = Pan(
        feed_streams=[c_magma_B_pans, a_mol_B_pans],
        heating_surface_ft2=15000,
        inches_vacuum=25, 
        supersaturation=1.2, 
        head_ft=2,
        masse_brix=94,
        cry_yld_pct_brix=40,
        steam_type="Exhaust",
        calandria_steam_temp_F=255,
        name="B Pans"
    )

    B_centrifugals = Centrifugal(
        massecuite=B_pans.massecuite,
        massecuite_flow_lb_hr=B_pans.massecuite_flow_lb_hr,
        target_molasses_brix=83,
        purity_rise=2,
        sugar_purity=92,
        sugar_moisture=5 ,
        name="B Machines",
        sugar_temp=140,
        molasses_temp=140
        )

    # make grain
    b_mol_grain = SugarStream.copy(B_centrifugals.molasses_stream)
    b_mol_grain.flow_lb_per_hr = b_mol_to_grain_pct / 100 * b_mol_grain.flow_lb_per_hr

    a_mol_grain = SugarStream.copy(A_centrifugals.molasses_stream)
    a_mol_grain.flow_lb_per_hr = a_mol_to_grain_pct / 100 * a_mol_grain.flow_lb_per_hr


    syrup_to_grain.flow_lb_per_hr = syrup_to_grain_pct / 100 * syrup_to_grain.flow_lb_per_hr

    grain_pans = Pan(
        feed_streams=[syrup_to_grain, a_mol_grain, b_mol_grain],
        heating_surface_ft2=6000,
        inches_vacuum=25,
        supersaturation=1.2,
        head_ft=2,
        masse_brix=88,
        cry_yld_pct_brix=20,
        steam_type="Exhaust",
        calandria_steam_temp_F=255,
        heat_loss_factor=0.05,
        name='Grain Pans for C'
    )

    grain_massecuite = SugarStream(
        brix=grain_pans.masse_brix,
        purity=grain_pans.masse_purity,
        flow_lb_per_hr=grain_pans.massecuite_flow_lb_hr,
        temp_deg_F=grain_pans.massecuite.massecuite_temp,
        pressure_psia=14.7,
        level_ft=0
    ) # got to feed Pan object a SugarStream

    # Make C Pans
    b_mol_C_pans = SugarStream.copy(B_centrifugals.molasses_stream)
    b_mol_C_pans.flow_lb_per_hr = b_mol_C_pans_pct / 100 * b_mol_C_pans.flow_lb_per_hr

    C_pans = Pan(
        [grain_massecuite, b_mol_C_pans],
        heating_surface_ft2=12000,
        inches_vacuum=26.5,
        supersaturation=1.2,
        head_ft=2,
        masse_brix=96,
        cry_yld_pct_brix=30,
        steam_type="V1",
        calandria_steam_temp_F=235,
        heat_loss_factor=0.05,
        name="C Pans"
    )

    C_machines = Centrifugal(
        massecuite=C_pans.massecuite,
        massecuite_flow_lb_hr=C_pans.massecuite_flow_lb_hr,
        target_molasses_brix=82,
        purity_rise=2,
        sugar_moisture=5,
        sugar_purity=82,
        sugar_temp=140,
        molasses_temp=150,
        name="C Machines"
    )

    # Update B and C magma
    b_magma = make_magma(B_centrifugals.sugar_stream, mingler_brix=92)
    c_magma = make_magma(C_machines.sugar_stream, mingler_brix=92)

    # Update footings for remelt
    b_magma_A_pans = SugarStream.copy(b_magma)
    b_magma_A_pans.flow_lb_per_hr = (100 - b_magma_rmlt_pct) / 100 * b_magma_A_pans.flow_lb_per_hr

    c_magma_B_pans = SugarStream.copy(c_magma)
    c_magma_B_pans.flow_lb_per_hr = (100 - c_magma_rmlt_pct) / 100 * c_magma_B_pans.flow_lb_per_hr

    # Remelt
    b_magma_to_rmlt = SugarStream.copy(b_magma)
    b_magma_to_rmlt.flow_lb_per_hr = (b_magma_rmlt_pct) / 100 * b_magma_to_rmlt.flow_lb_per_hr
    b_remelt = make_remelt(b_magma_to_rmlt, remelt_brix=65)

    c_magma_to_rmlt = SugarStream.copy(c_magma)
    c_magma_to_rmlt.flow_lb_per_hr = (c_magma_rmlt_pct) / 100 * c_magma_to_rmlt.flow_lb_per_hr
    c_remelt = make_remelt(c_magma_to_rmlt, remelt_brix=65)

    # Now update syrup as delivered to pans
    syrup_as_fed = SugarStream.copy(syrup)
    total_flows = syrup.flow_lb_per_hr + c_remelt.flow_lb_per_hr + b_remelt.flow_lb_per_hr
    total_solids = syrup.solids_flow + c_remelt.solids_flow + b_remelt.solids_flow
    total_pols = syrup.pol_flow + b_remelt.pol_flow + c_remelt.pol_flow
    syrup_as_fed.flow_lb_per_hr = total_flows
    syrup_as_fed.brix = total_solids / total_flows * 100
    syrup_as_fed.purity = total_pols / total_solids * 100

    # Update flows
    syrup_to_A_pans = SugarStream.copy(syrup_as_fed)
    syrup_to_A_pans.flow_lb_per_hr = syrup_to_A_pans_pct / 100 * syrup_to_A_pans.flow_lb_per_hr

    syrup_to_grain = SugarStream.copy(syrup_as_fed) # Flow gets updated right before Grain pans

    # convergence checker
    print(syrup_as_fed.flow_lb_per_hr) # when this stops changing


# End Loop

end_time = time() * 1000

time_to_solve = end_time - start_time

print(f"time to solve {time_to_solve:.0f} ms")

display_balance(
    syrup=syrup,
    A_centrifugals=A_centrifugals,
    B_centrifugals=B_centrifugals,
    C_machines=C_machines,
    A_pans=A_pans,
    B_pans=B_pans,
    grain_pans=grain_pans,
    C_pans=C_pans,
)



