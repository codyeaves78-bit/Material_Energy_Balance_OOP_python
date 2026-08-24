from EvaporatorSet import EvaporatorSet, EvaporatorSetSciPy
import time
from SugarStream import SugarStream
from SteamStream import EvaporatorSteam
from PreEvaporator import PreEvaporator
from evaporator_functions import convert_psig_to_psia, convert_inHg_vacuum_to_psia

juice = SugarStream(brix=14, purity=88, flow_lb_per_hr=1000000, temp_deg_F=225, pressure_psia=40)
exhaust = EvaporatorSteam(P_psia=30)
areas = [25000, 25000, 15000, 15000, 10000]
vapor_bleeds = [100000, 100000, 50000]

t1 = time.time()
evaporators = EvaporatorSet(
    juice_in=juice,
    supply_steam=exhaust,
    effect_areas_ft2=areas,
    vapor_bleeds=vapor_bleeds,    
    name="Original Set",
)
evaporators.adjust_pressure_profile()
t2 = time.time()
evaporator_solve_time = t2 - t1

evaporators.neat_display()

t3=time.time()
evaporators_scipy = EvaporatorSetSciPy(
    juice_in=juice,
    effect_areas_ft2=areas,
    vapor_bleeds=vapor_bleeds,    
    supply_steam=exhaust,
    name="SciPy Set"
)
evaporators_scipy.adjust_pressure_profile_scipy()
t4 = time.time()
evaporator_scipy_solve_time = t4 - t3

evaporators_scipy.neat_display()

print(f"Evaporators time to solve {evaporator_solve_time*1000} ms")
print(f"SciPy Evaporators time to solve {evaporator_scipy_solve_time*1000} ms")
