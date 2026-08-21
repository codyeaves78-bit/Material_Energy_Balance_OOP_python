# Streamlit table builders for CoolingTowerSystem, mirroring the sections
# written by CoolingTowerSystem.to_excel() (system streams, condenser
# inventory, hot water return / tower / system balance).

import pandas as pd

from cooling_tower_diagram import _collect_streams


def cooling_tower_streams_table(cts) -> pd.DataFrame:
    rows = _collect_streams(cts)
    df = pd.DataFrame(rows, columns=["#", "Stream", "lb/hr", "GPM", "°F"])
    for col in ["lb/hr", "GPM", "°F"]:
        df[col] = df[col].map(lambda v: f"{v:,.2f}" if isinstance(v, (int, float)) else v)
    return df


def cooling_tower_condenser_table(cts) -> pd.DataFrame:
    rows = []
    tv = th = tw = tg = tt = 0.0
    for name, c in cts.condensers:
        inj = c.injection_water_flow_lb_hr
        gpm = inj / 500.4
        rows.append((name, c.vapor_flow_lb_hr, c.vapor_sat_temp_F, c.vapor_h_fg_btu_lb,
                     c.heat_load_btu_hr / 1e6, inj, gpm, c.water_outlet_temp_F,
                     c.total_outlet_flow_lb_hr))
        tv += c.vapor_flow_lb_hr
        th += c.heat_load_btu_hr / 1e6
        tw += inj
        tg += gpm
        tt += c.total_outlet_flow_lb_hr
    rows.append(("Total", tv, None, None, th, tw, tg, None, tt))
    df = pd.DataFrame(rows, columns=["Condenser", "Vapor (lb/hr)", "Sat T (°F)", "h_fg (BTU/lb)",
                                      "Heat (MM BTU/hr)", "Inj Water (lb/hr)", "Inj Water (GPM)",
                                      "Water Out (°F)", "Total Out (lb/hr)"])
    for col in df.columns[1:]:
        df[col] = df[col].map(lambda v: "" if pd.isna(v) else f"{v:,.3f}")
    return df


def cooling_tower_balance_table(cts) -> pd.DataFrame:
    bal = cts.balance_check
    gpm = cts._GPM
    rows = [
        ("Injection water, all condensers (lb/hr)", cts.total_injection_water_lb_hr),
        ("Vapor condensed, all condensers (lb/hr)", cts.total_vapor_lb_hr),
        ("Total hot water return (lb/hr)", cts.hot_water_return_lb_hr),
        ("Total hot water return (GPM)", cts.hot_water_return_lb_hr / gpm),
        ("Mixed return temperature (°F)", cts.hot_water_return_temp_F),
        ("Cool water temperature (°F)", cts.cool_water_temp_F),
        ("Blowdown (lb/hr)", cts.blowdown_lb_hr),
        ("Blowdown (GPM)", cts.blowdown_lb_hr / gpm),
        ("Evaporated to atmosphere (lb/hr)", cts.evaporated_lb_hr),
        ("Cool water from tower (lb/hr)", cts.cool_water_from_tower_lb_hr),
        ("Cool water from tower (GPM)", cts.cool_water_from_tower_lb_hr / gpm),
        ("Makeup water required (lb/hr)", cts.makeup_lb_hr),
        ("Makeup water required (GPM)", cts.makeup_lb_hr / gpm),
        ("Makeup water temperature (°F)", cts.makeup_temp_F),
        ("Delivered injection water temp (°F)", cts.delivered_water_temp_F),
        ("Surplus / overflow (lb/hr)", cts.surplus_lb_hr),
        ("Balance check — water in: vapor + makeup (lb/hr)", bal["in_lb_hr"]),
        ("Balance check — water out: evap + BD + surplus (lb/hr)", bal["out_lb_hr"]),
        ("Balance check — net (In - Out) (lb/hr)", bal["diff_lb_hr"]),
    ]
    df = pd.DataFrame(rows, columns=["Metric", "Value"])
    df["Value"] = df["Value"].map(lambda v: f"{v:,.2f}")
    return df
