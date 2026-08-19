from EvaporatorSet import EvaporatorSet
from SugarStream import SugarStream
from SteamStream import EvaporatorSteam
from excel_export import new_workbook

my_set = EvaporatorSet(
    juice_in=SugarStream(brix=13, purity=90, flow_lb_per_hr=1000000, temp_deg_F=225, pressure_psia=40),
    supply_steam=EvaporatorSteam(30),
    last_effect_pressure_psia=2.4,
    target_brix_out=65,
    effect_areas_ft2=[25000, 25000, 25000, 25000],
    vapor_bleeds=[40000, 30000],
    dessin_coefficient=180000,
    liquid_level_ft=2,
    injection_water_temp_F=90,
    condenser_leg_temp_drop_F=5,
    name='My Test Set'
)

my_set.adjust_pressure_profile()
my_set.neat_display()
my_set.generate_pfd()

wb = new_workbook()
my_set.to_excel(wb)
excel_name = 'jimmy_test_example.xlsx'
wb.save(filename=excel_name)
print(f"Excel Export save successful. Filename = '{excel_name}'")
