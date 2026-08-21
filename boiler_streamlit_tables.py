# Streamlit table builders for the Boiler, mirroring Boiler.to_excel()'s
# sections (parameters, feed water / steam, bagasse fuel, performance).

import pandas as pd


def boiler_parameters_table(blr) -> pd.DataFrame:
    pressure_psig = blr.psia - 14.696
    rows = [
        ("Efficiency (%)", blr.efficiency),
        ("Pressure (psig)", pressure_psig),
        ("Pressure (psia)", blr.psia),
        ("Feed water temp (°F)", blr.feed_wat_temp),
        ("Superheat (°F above sat)", blr.deg_sh),
        ("Rated capacity (lb/hr)", blr.capacity),
    ]
    df = pd.DataFrame(rows, columns=["Parameter", "Value"])
    df["Value"] = df["Value"].map(lambda v: f"{v:,.2f}")
    return df


def boiler_streams_table(blr) -> pd.DataFrame:
    fw = blr.feed_water_stream
    steam = blr.steam_stream
    condition = "Superheated" if blr.deg_sh > 0 else "Saturated"
    rows = [
        ("Feed Water", f"{fw.T:,.2f}", f"{fw.h:,.2f}", ""),
        ("Steam Out", f"{steam.T:,.2f}", f"{steam.h:,.2f}", condition),
    ]
    return pd.DataFrame(rows, columns=["Stream", "Temp (°F)", "Enthalpy (BTU/lb)", "Condition"])


def boiler_fuel_table(blr) -> pd.DataFrame:
    bg = blr.bagasse
    rows = [
        ("Flowrate (lb/hr)", bg.flowrate_lb_hr),
        ("Fiber (%)", bg.fiber_pct),
        ("Moisture (%)", bg.moisture_pct),
        ("Brix (%)", bg.brix_pct),
        ("Pol (%)", bg.pol_pct),
        ("Ash (%)", bg.ash_pct),
        ("GCV (BTU/lb)", bg.gcv),
    ]
    df = pd.DataFrame(rows, columns=["Fuel Property", "Value"])
    df["Value"] = df["Value"].map(lambda v: f"{v:,.2f}")
    return df


def boiler_performance_table(blr) -> pd.DataFrame:
    rows = [
        ("Heat to make 1 lb steam (BTU/lb)", f"{blr.btu_for_1_lb:,.2f}"),
        ("Steam/Bagasse ratio (lb/lb)", f"{blr.steam_available_per_lb_bagasse:,.4f}"),
        ("Steam available from bagasse (lb/hr)", f"{blr.steam_availabe_lb_hr:,.2f}"),
    ]
    return pd.DataFrame(rows, columns=["Metric", "Value"])
