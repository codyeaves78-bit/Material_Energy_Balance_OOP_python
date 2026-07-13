# steam_summary_excel: writes the plant-wide live steam / exhaust steam
# summary onto one styled sheet, from the same label -> lb/hr dicts main.py
# already builds and prints (live_steam_dict, exh_dict).

from excel_export import SheetWriter


def steam_summary_to_excel(workbook, live_steam_dict, exh_dict,
                            exhaust_available_lb_hr=None,
                            makeup_steam_lb_hr=None,
                            steam_available_lb_hr=None,
                            sheet_name="Steam Summary"):
    """Write live steam demand and exhaust steam demand tables to their own
    sheet. Pass exhaust_available_lb_hr / makeup_steam_lb_hr to also include
    the exhaust availability vs. makeup balance. Pass
    boiler_steam_available_lb_hr (call this after solving the Boiler) to
    also include live steam availability vs. demand.

    live_steam_dict, exh_dict : {label: lb/hr}
    """
    total_live = list(live_steam_dict.values())[-1]
    total_exh  = list(exh_dict.values())[-1]

    sw = SheetWriter(workbook, sheet_name, ncols=2)
    sw.title(sheet_name,
             f"Live steam = {total_live:,.0f} lb/hr | Exhaust = {total_exh:,.0f} lb/hr")

    sw.section("LIVE STEAM DEMAND")
    for label, value in live_steam_dict.items():
        sw.row(label, value, "lb/hr", fmt="#,##0")

    sw.section("EXHAUST STEAM DEMAND")
    for label, value in exh_dict.items():
        sw.row(label, value, "lb/hr", fmt="#,##0")

    if exhaust_available_lb_hr is not None or makeup_steam_lb_hr is not None:
        sw.section("EXHAUST BALANCE")
        if exhaust_available_lb_hr is not None:
            sw.row("Exhaust available from turbines", exhaust_available_lb_hr, "lb/hr", fmt="#,##0")
        if makeup_steam_lb_hr is not None:
            sw.row("Makeup required", makeup_steam_lb_hr, "lb/hr", fmt="#,##0")

    if steam_available_lb_hr is not None:
        sw.section("LIVE STEAM AVAILABILITY")
        sw.row("Live steam available from bagasse",steam_available_lb_hr, "lb/hr", fmt="#,##0")
        sw.row("Live steam demand", total_live, "lb/hr", fmt="#,##0")
        sw.row("Surplus / (Deficit)", steam_available_lb_hr - total_live, "lb/hr", fmt="#,##0")

    return sw.finish()
