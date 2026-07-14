from MillFloor import MillFloor
from excel_export import new_workbook

smsc_mills = MillFloor(cane_tpd=20000, cane_pol_pct=13.0, cane_fiber_pct=14, imbibition_pct_on_cane=25, 
                       bagasse_pol_pct=2, last_roll_purity=70, bagasse_ash_pct=5, bagasse_moisture_pct=50, mix_juice_purity=89,
                       number_of_mills=5, juice_temp_F=90, mill_1_fiber_rise_load_fraction=0.35, name="SMSC Mills")
smsc_mills.neat_display()
wb = new_workbook()
smsc_mills.to_excel(wb)
wb.save(filename='example_mills_5.xlsx')