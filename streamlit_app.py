# Streamlit trial app: full factory material & energy balance walkthrough,
# following the same pipeline as main.py:
#   Mill Floor -> Clarification -> Juice Heating -> Pan Floor -> Evaporation
#   -> Steam & Exhaust Summary -> Download
#
# Run with:  streamlit run streamlit_app.py

import io

import matplotlib
matplotlib.use("Agg")  # headless backend, required before pyplot is imported anywhere
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from MillFloor import MillFloor
from Clarification import Clarification
from clarification_diagram import _collect_streams
from excel_export import new_workbook
from SugarStream import SugarStream
from SteamStream import SteamStream, EvaporatorSteam
from JuiceHeater import JuiceHeaterShellTube
from JuiceHeatingStation import JuiceHeatingStation
from Pan import Pan
from Centrifugal import Centrifugal
from Crystallizer_and_Reheater import Crystallizer, Reheater
from ThreeBoilingDoubleMagma import ThreeBoilingDoubleMagma
from FourBoilingDoubleMagma import FourBoilingDoubleMagma
from TwoBoiling import TwoBoiling
from PreEvaporator import PreEvaporator
from EvaporatorSet import sets_to_excel
from multi_effect_solver_vers_2 import solve_evaporator_sets
from Deaerator import Deaerator
from MillTurbines import MillTurbines
from CanePrepTurbines import CanePrepTurbines
from AuxillaryTurbines import AuxillaryTurbines
from Boiler import Boiler
from CoolingTowerSystem import CoolingTowerSystem
from condensate_balance import CondensateBalance, CondensateDemand
from condensate_utils import flash_condensate
from steam_summary_excel import steam_summary_to_excel

st.set_page_config(page_title="Factory Balance Trial", layout="wide")
st.title("Cane Sugar Factory Material & Energy Balance")
st.caption("Trial Streamlit walkthrough: Mill Floor → Clarification → Juice Heating → "
           "Pan Floor → Evaporation → Steam & Exhaust Summary.")

STEAM_TYPES = ["Exhaust", "V1", "V2", "V3", "V4"]


def parse_floats(s):
    if s is None:
        return []
    return [float(v) for v in str(s).replace(";", ",").split(",") if v.strip() != ""]


def vapor_dist_editor(grade, demand, consumers, key, default_pcts=None):
    """Render a '% of V{grade} demand' distribution editor across the given
    consumer names (evaporator sets, plus 'Pre-Evaporator' for grade 1).
    Returns (share_fn, dataframe) — share_fn(consumer_name) -> lb/hr.

    An evaporator set can only supply V{grade} if it has at least `grade`
    effects (effect k's own vapor feeds header V{k}; the last effect never
    bleeds, its vapor goes to the condenser) — see EvaporatorSet.build_effects.
    """
    col = f"% of V{grade} demand"
    st.markdown(f"**V{grade} Vapor Bleed Distribution** — total V{grade} demand "
                f"(heaters + pans): {demand:,.0f} lb/hr")
    if demand <= 0:
        st.caption(f"No V{grade} demand from heaters or pans.")
        return (lambda cname: 0.0), pd.DataFrame(columns=["Consumer", col])
    if not consumers:
        st.warning(f"V{grade} demand of {demand:,.0f} lb/hr exists but nothing can supply it — "
                    + (f"activate the Pre-Evaporator or " if grade == 1 else "")
                    + f"add/edit an evaporator set with at least {grade} effect(s).")
        return (lambda cname: 0.0), pd.DataFrame(columns=["Consumer", col])

    default_pcts = default_pcts or {}
    pcts = [default_pcts.get(c, 0.0) for c in consumers]
    if sum(pcts) <= 0:
        pcts = [100.0 / len(consumers)] * len(consumers)
    df = st.data_editor(
        pd.DataFrame({"Consumer": consumers, col: pcts}),
        hide_index=True, use_container_width=True, num_rows="fixed", key=key,
    )
    pct_sum = df[col].sum()
    if pct_sum <= 0:
        st.warning(f"V{grade} distribution percentages sum to 0 — no V{grade} will be bled off.")
    elif abs(pct_sum - 100) > 0.01:
        st.caption(f"Percentages sum to {pct_sum:.1f}%, not 100% — normalizing proportionally.")

    def share(cname):
        s = df[col].sum()
        if s <= 0:
            return 0.0
        row = df[df["Consumer"] == cname]
        if row.empty:
            return 0.0
        return float(row[col].iloc[0]) / s * demand

    return share, df


def pan_editor(key, defaults):
    df = pd.DataFrame(defaults)
    edited = st.data_editor(
        df, hide_index=True, use_container_width=True, num_rows="fixed", key=key,
        column_config={"Steam Type": st.column_config.SelectboxColumn(options=STEAM_TYPES)},
    )
    pans = {}
    for _, row in edited.iterrows():
        pans[row["Grade"]] = Pan(
            feed_streams=None,
            heating_surface_ft2=float(row["Heating Surface (ft²)"]),
            inches_vacuum=float(row["Vacuum (in Hg)"]),
            supersaturation=float(row["Supersaturation"]),
            head_ft=float(row["Head (ft)"]),
            masse_brix=float(row["Masse Brix"]),
            ml_purity=float(row["ML Purity"]),
            calandria_pressure_psia=float(row["Calandria (psia)"]),
            heat_loss_factor=float(row["Heat Loss Factor"]),
            steam_type=STEAM_TYPES.index(row["Steam Type"]),
            name=f"{row['Grade']} Pans",
        )
    return pans


def cen_editor(key, defaults):
    df = pd.DataFrame(defaults)
    edited = st.data_editor(df, hide_index=True, use_container_width=True, num_rows="fixed", key=key)
    cens = {}
    for _, row in edited.iterrows():
        cens[row["Grade"]] = Centrifugal(
            massecuite=None, massecuite_flow_lb_hr=0,
            target_molasses_brix=float(row["Target ML Brix"]),
            purity_rise=float(row["Purity Rise"]),
            sugar_purity=float(row["Sugar Purity"]),
            sugar_moisture=float(row["Sugar Moisture"]),
            sugar_temp=float(row["Sugar Temp"]),
            molasses_temp=float(row["ML Temp"]),
            name=f"{row['Grade']} Centrifugals",
        )
    return cens


# ============================================================================
# SIDEBAR — MILL FLOOR + CLARIFICATION
# ============================================================================
with st.sidebar:
    st.header("Mill Floor Inputs")
    with st.form("balance_form"):
        st.subheader("Cane & Mills")
        cane_tpd = st.number_input("Cane throughput (TPD)", value=19000.0, step=100.0)
        cane_pol_pct = st.number_input("Cane pol (%)", value=13.5, step=0.1)
        cane_fiber_pct = st.number_input("Cane fiber (%)", value=14.0, step=0.1)
        number_of_mills = st.number_input("Number of mills", value=6, min_value=2, max_value=8, step=1)
        mill_1_fiber_rise_load_fraction = st.number_input(
            "Mill 1 fiber rise load fraction", value=0.35, step=0.01, format="%.2f"
        )

        st.subheader("Imbibition & Juice")
        imbibition_pct_on_cane = st.number_input("Imbibition (% on cane)", value=30.0, step=0.5)
        juice_temp_F = st.number_input("Juice temperature (°F)", value=90.0, step=1.0)
        mix_juice_purity = st.number_input("Mixed juice purity (%)", value=88.0, step=0.1)

        st.subheader("Bagasse")
        bagasse_pol_pct = st.number_input("Bagasse pol (%)", value=2.1, step=0.1)
        last_roll_purity = st.number_input("Last roll juice purity (%)", value=72.0, step=0.5)
        bagasse_moisture_pct = st.number_input("Bagasse moisture (%)", value=49.5, step=0.5)
        bagasse_ash_pct = st.number_input("Bagasse ash (%)", value=5.0, step=0.5)

        st.header("Clarification Inputs")
        filter_wash_water_pct_on_cane = st.number_input("Filter wash water (% on cane)", value=5.0, step=0.5)
        filter_cake_pct_on_cane = st.number_input("Filter cake (% on cane)", value=5.0, step=0.5)
        filter_cake_pol_pct = st.number_input("Filter cake pol (%)", value=2.4, step=0.1)
        clarified_juice_purity = st.number_input("Clarified juice purity (%)", value=88.5, step=0.1)
        limed_juice_cold_temp_f = st.number_input("Limed juice cold temp (°F)", value=95.0, step=1.0)
        limed_juice_hot_temp_f = st.number_input("Limed juice hot temp (°F)", value=220.0, step=1.0)
        clarified_juice_temp_f = st.number_input("Clarified juice temp (°F)", value=205.0, step=1.0)
        lime_lb_per_ton_cane = st.number_input("Lime dose (lb/ton cane)", value=1.3, step=0.1)
        lime_baume = st.number_input("Milk of lime (°Baumé)", value=10.0, step=0.5)
        polymer_conc_ppm = st.number_input("Polymer concentration (ppm)", value=5000.0, step=100.0)
        polymer_lb_per_ton_cane = st.number_input(
            "Polymer dose (lb/ton cane)", value=0.045, step=0.005, format="%.3f"
        )
        clarifier_underflow_pct_cane = st.number_input("Clarifier underflow (% on cane)", value=20.0, step=0.5)

        submitted = st.form_submit_button("Run Balance", use_container_width=True)

if "result" not in st.session_state:
    st.session_state.result = None

if submitted:
    try:
        mills = MillFloor(
            cane_tpd=cane_tpd,
            cane_pol_pct=cane_pol_pct,
            cane_fiber_pct=cane_fiber_pct,
            imbibition_pct_on_cane=imbibition_pct_on_cane,
            bagasse_pol_pct=bagasse_pol_pct,
            last_roll_purity=last_roll_purity,
            bagasse_moisture_pct=bagasse_moisture_pct,
            bagasse_ash_pct=bagasse_ash_pct,
            mix_juice_purity=mix_juice_purity,
            number_of_mills=int(number_of_mills),
            juice_temp_F=juice_temp_F,
            mill_1_fiber_rise_load_fraction=mill_1_fiber_rise_load_fraction,
            name="Mill Floor",
        )

        clar = Clarification(
            mixed_juice_stream=mills.mixed_juice_stream,
            cane_tpd=mills.cane_tpd,
            filter_wash_water_pct_on_cane=filter_wash_water_pct_on_cane,
            filter_cake_pct_on_cane=filter_cake_pct_on_cane,
            filter_cake_pol_pct=filter_cake_pol_pct,
            clarified_juice_purity=clarified_juice_purity,
            limed_juice_cold_temp_f=limed_juice_cold_temp_f,
            limed_juice_hot_temp_f=limed_juice_hot_temp_f,
            clarified_juice_temp_f=clarified_juice_temp_f,
            lime_lb_per_ton_cane=lime_lb_per_ton_cane,
            lime_baume=lime_baume,
            polymer_conc_ppm=polymer_conc_ppm,
            polymer_lb_per_ton_cane=polymer_lb_per_ton_cane,
            clarifier_underflow_pct_cane=clarifier_underflow_pct_cane,
            name="Clarification",
        )

        st.session_state.result = (mills, clar)
    except Exception as exc:
        st.session_state.result = None
        st.error(f"Balance failed to solve: {exc}")

result = st.session_state.result

if result is None:
    st.info("Set your inputs in the sidebar and click **Run Balance** to solve the mill floor and "
            "clarification balance, which unlocks the rest of the plant.")
    st.stop()

mills, clar = result
mj = mills.mixed_juice_stream
bag = mills.bagasse_stream
cj = clar.clarified_juice_stream

st.divider()
fabrication_exhaust_psia = st.number_input(
    "Fabrication exhaust pressure (psia)", value=30.0, step=1.0,
    help="Default steam supply pressure for the juice heaters and the pre-evaporator.",
)

(tab_mill, tab_clar, tab_heat, tab_pan, tab_evap, tab_steam, tab_turb, tab_cool,
 tab_cond, tab_dl) = st.tabs([
    "Mill Floor", "Clarification", "Juice Heating", "Pan Floor",
    "Evaporation", "Exhaust Summary", "Turbines & Boiler", "Cooling Tower",
    "Condensate Balance", "Download",
])

# ============================================================================
# MILL FLOOR TAB
# ============================================================================
with tab_mill:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mill extraction", f"{mills.mill_extraction_pct:.2f}%")
    c2.metric("Mixed juice flow", f"{mj.flow_lb_per_hr:,.0f} lb/hr")
    c3.metric("Mixed juice brix / purity", f"{mj.brix:.2f}% / {mj.purity:.1f}%")
    c4.metric("Bagasse flow", f"{bag.flowrate_lb_hr / 2000 * 24:,.0f} TPD")

    st.subheader("Process Flow Diagram")
    fig = mills.generate_pfd(show=False)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    st.subheader("Stream Table (TPH)")
    rows, in_tot, out_tot = mills._stream_table_rows()
    diff = [i - o for i, o in zip(in_tot, out_tot)]
    cols = ["Stream", "Dir", "Flow (TPH)", "Pol (TPH)", "Brix (TPH)", "Fiber (TPH)", "Water (TPH)"]
    df = pd.DataFrame(rows, columns=cols)
    totals_df = pd.DataFrame(
        [["Total In", "", *in_tot], ["Total Out", "", *out_tot], ["Difference", "", *diff]],
        columns=cols,
    )
    st.dataframe(pd.concat([df, totals_df], ignore_index=True), use_container_width=True, hide_index=True)

    st.subheader("Per-Mill Maceration Balance (TPD)")
    mb_df = pd.DataFrame(mills.mill_balances)
    st.dataframe(mb_df, use_container_width=True, hide_index=True)

    st.subheader("Balance Check")
    bal = mills.balance_check
    bal_df = pd.DataFrame(bal).T.reset_index().rename(columns={"index": "Quantity"})
    st.dataframe(bal_df, use_container_width=True, hide_index=True)

# ============================================================================
# CLARIFICATION TAB
# ============================================================================
with tab_clar:
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Clarified juice flow", f"{cj.flow_lb_per_hr:,.0f} lb/hr")
    c2.metric("Clarified juice brix / purity", f"{cj.brix:.2f}% / {cj.purity:.1f}%")
    c3.metric("Flash vapor", f"{clar.flash_vapor_pct:.3f}%")
    c4.metric("Filter cake pol loss", f"{clar.filter_cake_pol_lb_per_day:,.0f} lb/day")

    st.subheader("Process Flow Diagram")
    fig = clar.generate_pfd(show=False, include_table=False)
    st.pyplot(fig, use_container_width=True)
    plt.close(fig)

    st.subheader("Stream Table (tags match the diagram)")
    stream_cols = ["#", "Stream", "Dir", "lb/hr", "GPM", "Brix lb/hr", "Pol lb/hr",
                   "Brix %", "Pol %", "Purity %", "% on Cane", "°F"]
    st.dataframe(pd.DataFrame(_collect_streams(clar), columns=stream_cols),
                 use_container_width=True, hide_index=True)

    st.subheader("Balance Check")
    bal = clar.balance_check
    bal_df = pd.DataFrame(bal).T.reset_index().rename(columns={"index": "Quantity"})
    st.dataframe(bal_df, use_container_width=True, hide_index=True)

# ============================================================================
# JUICE HEATING TAB
# ============================================================================
heat_ok = False
par_heaters = None
clar_juice_heater = None

with tab_heat:
    st.subheader("V1 / Exhaust Juice Heating Station")
    juice_T_out = clar.limed_juice_hot_temp_f
    cold_juice = clar.limed_juice_cold_stream

    mode = st.radio("Flow arrangement", ["parallel", "series"], horizontal=True)
    heater_defaults = pd.DataFrame([
        {"Group": "V1 Heaters", "Steam Type": "V1", "Steam Pressure (psia)": float(fabrication_exhaust_psia),
         "U (Btu/hr·ft²·°F)": 200.0, "Area (ft²)": 11000.0, "Split %": 75.0},
        {"Group": "Exhaust Heaters", "Steam Type": "Exhaust", "Steam Pressure (psia)": float(fabrication_exhaust_psia),
         "U (Btu/hr·ft²·°F)": 200.0, "Area (ft²)": 5000.0, "Split %": 25.0},
    ])
    heater_df = st.data_editor(
        heater_defaults, hide_index=True, use_container_width=True, num_rows="fixed",
        column_config={
            "Steam Type": st.column_config.SelectboxColumn(options=STEAM_TYPES),
            "Split %": st.column_config.NumberColumn(disabled=(mode != "parallel")),
        },
        key="heater_editor",
    )

    try:
        heater_objs = [
            JuiceHeaterShellTube(
                cold_stream=cold_juice,
                hot_stream=SteamStream(x=1, P=row["Steam Pressure (psia)"]),
                name=row["Group"],
                juice_out_temp_degF=juice_T_out,
                U_btu_per_ft2_degF=row["U (Btu/hr·ft²·°F)"],
                installed_area_ft2=row["Area (ft²)"],
                steam_type=STEAM_TYPES.index(row["Steam Type"]),
            )
            for _, row in heater_df.iterrows()
        ]
        split_pcts = list(heater_df["Split %"]) if mode == "parallel" else None
        par_heaters = JuiceHeatingStation(
            cold_stream=cold_juice, heaters=heater_objs, mode=mode,
            split_pcts=split_pcts,
            name="Parallel Juice Heating Station" if mode == "parallel" else "Series Juice Heating Station",
        )

        c1, c2, c3 = st.columns(3)
        c1.metric("Juice out", f"{par_heaters.juice_out.flow_lb_per_hr:,.0f} lb/hr")
        c2.metric("Total steam", f"{par_heaters.total_steam_lb_hr:,.0f} lb/hr")
        c3.metric("V1 / Exhaust steam", f"{par_heaters.total_V1_steam_lb_hr:,.0f} / "
                                         f"{par_heaters.total_exhaust_steam_lb_hr:,.0f} lb/hr")

        st.subheader("Clarified Juice Heater")
        cj_cols = st.columns(4)
        cjh_temp = cj_cols[0].number_input("Juice out temp (°F)", value=225.0, step=1.0)
        cjh_U = cj_cols[1].number_input("U (Btu/hr·ft²·°F)", value=185.0, step=5.0)
        cjh_area = cj_cols[2].number_input("Area (ft²)", value=6000.0, step=500.0)
        cjh_psia = cj_cols[3].number_input("Steam pressure (psia)", value=float(fabrication_exhaust_psia),
                                            step=1.0, key="cjh_psia")

        clar_juice_colder = SugarStream.copy(cj)
        clar_juice_heater = JuiceHeaterShellTube(
            cold_stream=clar_juice_colder,
            hot_stream=SteamStream(x=1, P=cjh_psia),
            name="Clarified Juice Heater",
            juice_out_temp_degF=cjh_temp,
            U_btu_per_ft2_degF=cjh_U,
            installed_area_ft2=cjh_area,
            steam_type=0,
        )
        cj.temp_deg_F = clar_juice_heater.juice_out_temp_degF  # matches main.py: update in place

        c1, c2 = st.columns(2)
        c1.metric("Clarified juice heater steam", f"{clar_juice_heater.steam_required_lb_per_hr:,.0f} lb/hr")
        c2.metric("Clarified juice out temp", f"{cj.temp_deg_F:.1f} °F")

        heat_ok = True
    except Exception as exc:
        st.error(f"Juice heating failed to solve: {exc}")

# ============================================================================
# PAN FLOOR TAB
# ============================================================================
pan_ok = False
pan_floor = None
syrup_brix = 65.0

with tab_pan:
    st.subheader("Pan Floor")
    scheme = st.radio(
        "Boiling scheme",
        ["FBDM (Four Boiling Double Magma)", "TBDM (Three Boiling Double Magma)", "2B (Two Boiling)"],
        horizontal=True,
    )
    is_fbdm = scheme.startswith("FBDM")
    is_tbdm = scheme.startswith("TBDM")
    is_2b = scheme.startswith("2B")
    scheme_key = "FBDM" if is_fbdm else ("TBDM" if is_tbdm else "2B")

    syrup_brix = st.number_input("Syrup brix (target)", value=65.0, step=0.5)
    syrup_lb_hr = cj.flow_lb_per_hr * cj.brix / syrup_brix
    syrup = SugarStream.copy(cj)
    syrup.flow_lb_per_hr = syrup_lb_hr
    syrup.brix = syrup_brix
    st.caption(f"Syrup feed: {syrup_lb_hr:,.0f} lb/hr @ {syrup_brix:.1f} Bx "
               f"(from clarified juice @ {cj.brix:.2f} Bx)")

    st.markdown("**Advanced pan floor settings**")
    ad1, ad2, ad3, ad4, ad5, ad6 = st.columns(6)
    pf_injection_water_temp_F = ad1.number_input("Injection water temp (°F)", value=90.0, step=1.0,
                                                  key="pf_inj_water")
    pf_condenser_leg_temp_drop_F = ad2.number_input("Condenser leg ΔT (°F)", value=5.0, step=0.5,
                                                     key="pf_cond_leg")
    pf_c_magma_brix = ad3.number_input("C magma brix", value=92.0, step=0.5, key="pf_c_magma_brix")
    pf_c_remelt_brix = ad4.number_input("C remelt brix", value=65.0, step=0.5, key="pf_c_remelt_brix")
    if not is_2b:
        pf_b_magma_brix = ad5.number_input("B magma brix", value=92.0, step=0.5, key="pf_b_magma_brix")
        pf_b_remelt_brix = ad6.number_input("B remelt brix", value=65.0, step=0.5, key="pf_b_remelt_brix")
    else:
        pf_b_magma_brix = pf_b_remelt_brix = None

    st.markdown("**Pans**")
    if is_fbdm:
        pan_defaults = [
            dict(Grade="A1", **{"Heating Surface (ft²)": 16000.0, "Vacuum (in Hg)": 23.5, "Supersaturation": 1.2,
                                 "Head (ft)": 2.0, "Masse Brix": 92.0, "ML Purity": 75.0,
                                 "Calandria (psia)": 21.696, "Heat Loss Factor": 0.02, "Steam Type": "V1"}),
            dict(Grade="A2", **{"Heating Surface (ft²)": 6000.0, "Vacuum (in Hg)": 23.5, "Supersaturation": 1.2,
                                 "Head (ft)": 2.0, "Masse Brix": 92.0, "ML Purity": 70.0,
                                 "Calandria (psia)": 21.696, "Heat Loss Factor": 0.02, "Steam Type": "V1"}),
            dict(Grade="B", **{"Heating Surface (ft²)": 7500.0, "Vacuum (in Hg)": 25.0, "Supersaturation": 1.2,
                                "Head (ft)": 2.0, "Masse Brix": 94.0, "ML Purity": 52.0,
                                "Calandria (psia)": 29.696, "Heat Loss Factor": 0.05, "Steam Type": "Exhaust"}),
            dict(Grade="Grain", **{"Heating Surface (ft²)": 3000.0, "Vacuum (in Hg)": 25.5, "Supersaturation": 1.2,
                                    "Head (ft)": 2.0, "Masse Brix": 88.0, "ML Purity": 45.0,
                                    "Calandria (psia)": 29.696, "Heat Loss Factor": 0.05, "Steam Type": "Exhaust"}),
            dict(Grade="C", **{"Heating Surface (ft²)": 12000.0, "Vacuum (in Hg)": 26.5, "Supersaturation": 1.2,
                                "Head (ft)": 2.0, "Masse Brix": 95.5, "ML Purity": 33.0,
                                "Calandria (psia)": 21.696, "Heat Loss Factor": 0.05, "Steam Type": "V1"}),
        ]
        cen_defaults = [
            dict(Grade="A1", **{"Target ML Brix": 82.0, "Purity Rise": 0.0, "Sugar Purity": 99.7,
                                 "Sugar Moisture": 0.2, "Sugar Temp": 150.0, "ML Temp": 145.0}),
            dict(Grade="A2", **{"Target ML Brix": 82.0, "Purity Rise": 0.0, "Sugar Purity": 99.3,
                                 "Sugar Moisture": 0.2, "Sugar Temp": 150.0, "ML Temp": 145.0}),
            dict(Grade="B", **{"Target ML Brix": 82.0, "Purity Rise": 0.0, "Sugar Purity": 92.0,
                                "Sugar Moisture": 5.0, "Sugar Temp": 150.0, "ML Temp": 145.0}),
            dict(Grade="C", **{"Target ML Brix": 82.0, "Purity Rise": 0.0, "Sugar Purity": 82.0,
                                "Sugar Moisture": 5.0, "Sugar Temp": 150.0, "ML Temp": 145.0}),
        ]
    elif is_tbdm:
        pan_defaults = [
            dict(Grade="A", **{"Heating Surface (ft²)": 22500.0, "Vacuum (in Hg)": 23.5, "Supersaturation": 1.2,
                                "Head (ft)": 2.0, "Masse Brix": 92.0, "ML Purity": 73.0,
                                "Calandria (psia)": 21.696, "Heat Loss Factor": 0.02, "Steam Type": "V1"}),
            dict(Grade="B", **{"Heating Surface (ft²)": 7500.0, "Vacuum (in Hg)": 25.0, "Supersaturation": 1.2,
                                "Head (ft)": 2.0, "Masse Brix": 94.0, "ML Purity": 53.0,
                                "Calandria (psia)": 29.696, "Heat Loss Factor": 0.05, "Steam Type": "Exhaust"}),
            dict(Grade="Grain", **{"Heating Surface (ft²)": 3000.0, "Vacuum (in Hg)": 25.5, "Supersaturation": 1.2,
                                    "Head (ft)": 2.0, "Masse Brix": 88.0, "ML Purity": 45.0,
                                    "Calandria (psia)": 29.696, "Heat Loss Factor": 0.05, "Steam Type": "Exhaust"}),
            dict(Grade="C", **{"Heating Surface (ft²)": 12000.0, "Vacuum (in Hg)": 26.5, "Supersaturation": 1.2,
                                "Head (ft)": 2.0, "Masse Brix": 95.5, "ML Purity": 33.0,
                                "Calandria (psia)": 21.696, "Heat Loss Factor": 0.05, "Steam Type": "V1"}),
        ]
        cen_defaults = [
            dict(Grade="A", **{"Target ML Brix": 82.0, "Purity Rise": 0.0, "Sugar Purity": 99.7,
                                "Sugar Moisture": 0.2, "Sugar Temp": 150.0, "ML Temp": 145.0}),
            dict(Grade="B", **{"Target ML Brix": 82.0, "Purity Rise": 0.0, "Sugar Purity": 92.0,
                                "Sugar Moisture": 5.0, "Sugar Temp": 150.0, "ML Temp": 145.0}),
            dict(Grade="C", **{"Target ML Brix": 82.0, "Purity Rise": 0.0, "Sugar Purity": 82.0,
                                "Sugar Moisture": 5.0, "Sugar Temp": 150.0, "ML Temp": 145.0}),
        ]
    else:  # Two Boiling — no B pans/centrifugals
        pan_defaults = [
            dict(Grade="A", **{"Heating Surface (ft²)": 22500.0, "Vacuum (in Hg)": 23.5, "Supersaturation": 1.2,
                                "Head (ft)": 2.0, "Masse Brix": 92.0, "ML Purity": 55.0,
                                "Calandria (psia)": 21.696, "Heat Loss Factor": 0.02, "Steam Type": "V1"}),
            dict(Grade="Grain", **{"Heating Surface (ft²)": 3000.0, "Vacuum (in Hg)": 25.5, "Supersaturation": 1.2,
                                    "Head (ft)": 2.0, "Masse Brix": 88.0, "ML Purity": 45.0,
                                    "Calandria (psia)": 29.696, "Heat Loss Factor": 0.05, "Steam Type": "Exhaust"}),
            dict(Grade="C", **{"Heating Surface (ft²)": 12000.0, "Vacuum (in Hg)": 26.5, "Supersaturation": 1.2,
                                "Head (ft)": 2.0, "Masse Brix": 95.5, "ML Purity": 30.0,
                                "Calandria (psia)": 21.696, "Heat Loss Factor": 0.05, "Steam Type": "V1"}),
        ]
        cen_defaults = [
            dict(Grade="A", **{"Target ML Brix": 78.0, "Purity Rise": 0.0, "Sugar Purity": 99.4,
                                "Sugar Moisture": 0.3, "Sugar Temp": 150.0, "ML Temp": 145.0}),
            dict(Grade="C", **{"Target ML Brix": 78.0, "Purity Rise": 0.0, "Sugar Purity": 78.0,
                                "Sugar Moisture": 5.0, "Sugar Temp": 150.0, "ML Temp": 145.0}),
        ]

    pans = pan_editor(f"pan_editor_{scheme_key}", pan_defaults)
    st.markdown("**Centrifugals**")
    cens = cen_editor(f"cen_editor_{scheme_key}", cen_defaults)

    st.markdown("**C Crystallizer / Reheater** (low-grade cooling train)")
    cc1, cc2, cc3 = st.columns(3)
    cryst_temp_out = cc1.number_input("Crystallizer masse out (°F)", value=120.0, step=1.0)
    cryst_ml_purity_out = cc2.number_input("Crystallizer ML purity out (%)", value=30.0, step=1.0)
    reheat_temp_out = cc3.number_input("Reheater masse out (°F)", value=140.0, step=1.0)
    st.caption("Cooling water fixed 85→105°F, reheat water fixed 150→135°F.")

    C_crystallizers = Crystallizer(
        massecuite_in=None, massecuite_flow_lb_hr=0, masse_temp_out_deg_F=cryst_temp_out,
        ml_purity_out=cryst_ml_purity_out, water_temp_in_deg_F=85, water_temp_out_deg_F=105,
        name="C Crystallizers",
    )
    C_reheaters = Reheater(
        massecuite_in=None, massecuite_flow_lb_hr=0, masse_temp_out_deg_F=reheat_temp_out,
        water_temp_in_deg_F=150, water_temp_out_deg_F=135, name="C Reheaters",
    )

    st.markdown("**Split fractions**")
    try:
        if is_fbdm:
            s1, s2, s3, s4 = st.columns(4)
            syrup_to_A1 = s1.number_input("Syrup to A1 pans (%)", value=75.0)
            syrup_to_A2 = s2.number_input("Syrup to A2 pans (%)", value=20.0)
            a1_to_A2 = s3.number_input("A1 mol to A2 (%)", value=80.0)
            a1_to_grain = s4.number_input("A1 mol to grain (%)", value=3.0)
            s5, s6, s7, s8 = st.columns(4)
            a2_to_grain = s5.number_input("A2 mol to grain (%)", value=0.0)
            b_to_grain = s6.number_input("B mol to grain (%)", value=10.0)
            b_A1_footing = s7.number_input("B magma A1 footing (%)", value=40.0)
            b_A2_footing = s8.number_input("B magma A2 footing (%)", value=40.0)
            s9, s10 = st.columns(2)
            c_B_footing = s9.number_input("C magma B footing (%)", value=80.0)
            iterations = int(s10.number_input("Solver iterations", value=15, step=1, key="pf_fbdm_iterations"))

            pan_floor = FourBoilingDoubleMagma(
                syrup=syrup,
                A1_pans=pans["A1"], A2_pans=pans["A2"], B_pans=pans["B"], C_pans=pans["C"],
                grain_pans=pans["Grain"],
                A1_centrifugals=cens["A1"], A2_centrifugals=cens["A2"], B_centrifugals=cens["B"],
                C_centrifugals=cens["C"],
                C_crystallizers=C_crystallizers, C_reheaters=C_reheaters,
                syrup_to_A1_pans_pct=syrup_to_A1, syrup_to_A2_pans_pct=syrup_to_A2,
                a1_mol_to_A2_pct=a1_to_A2, a1_mol_to_grain_pct=a1_to_grain, a2_mol_to_grain_pct=a2_to_grain,
                b_mol_to_grain_pct=b_to_grain, b_magma_A1_footing_pct=b_A1_footing,
                b_magma_A2_footing_pct=b_A2_footing, c_magma_B_footing_pct=c_B_footing,
                b_magma_brix=pf_b_magma_brix, c_magma_brix=pf_c_magma_brix,
                b_remelt_brix=pf_b_remelt_brix, c_remelt_brix=pf_c_remelt_brix,
                injection_water_temp_F=pf_injection_water_temp_F,
                condenser_leg_temp_drop_F=pf_condenser_leg_temp_drop_F,
                iterations=iterations,
            )
        elif is_tbdm:
            s1, s2, s3, s4 = st.columns(4)
            c_remelt = s1.number_input("C magma remelt (%)", value=20.0)
            b_remelt = s2.number_input("B magma remelt (%)", value=20.0)
            syrup_grain = s3.number_input("Syrup to grain (%)", value=1.0)
            a_to_grain = s4.number_input("A mol to grain (%)", value=3.0)
            s5, s6 = st.columns(2)
            b_to_grain = s5.number_input("B mol to grain (%)", value=10.0)
            a_top_off = s6.number_input("A mol top-off (%)", value=0.0)
            iterations = 20

            pan_floor = ThreeBoilingDoubleMagma(
                syrup=syrup,
                A_pans=pans["A"], B_pans=pans["B"], C_pans=pans["C"], grain_pans=pans["Grain"],
                A_centrifugals=cens["A"], B_centrifugals=cens["B"], C_centrifugals=cens["C"],
                C_crystallizers=C_crystallizers, C_reheaters=C_reheaters,
                c_magma_remelt_pct=c_remelt, b_magma_remelt_pct=b_remelt, syrup_to_grain_pct=syrup_grain,
                a_mol_to_grain_pct=a_to_grain, b_mol_to_grain_pct=b_to_grain, a_mol_top_off_pct=a_top_off,
                b_magma_brix=pf_b_magma_brix, c_magma_brix=pf_c_magma_brix,
                b_remelt_brix=pf_b_remelt_brix, c_remelt_brix=pf_c_remelt_brix,
                injection_water_temp_F=pf_injection_water_temp_F,
                condenser_leg_temp_drop_F=pf_condenser_leg_temp_drop_F,
                iterations=iterations,
            )
        else:  # Two Boiling
            s1, s2, s3, s4 = st.columns(4)
            c_remelt = s1.number_input("C magma remelt (%)", value=20.0)
            syrup_grain = s2.number_input("Syrup to grain (%)", value=1.0)
            syrup_to_C = s3.number_input("Syrup to C pans (%)", value=5.0)
            a_to_grain = s4.number_input("A mol to grain (%)", value=3.0)
            s5, s6 = st.columns(2)
            a_top_off = s5.number_input("A mol top-off (%)", value=30.0)
            iterations = int(s6.number_input("Solver iterations", value=20, step=1, key="pf_2b_iterations"))

            pan_floor = TwoBoiling(
                syrup=syrup,
                A_pans=pans["A"], C_pans=pans["C"], grain_pans=pans["Grain"],
                A_centrifugals=cens["A"], C_centrifugals=cens["C"],
                C_crystallizers=C_crystallizers, C_reheaters=C_reheaters,
                c_magma_remelt_pct=c_remelt, syrup_to_grain_pct=syrup_grain, syrup_to_C_pct=syrup_to_C,
                a_mol_to_grain_pct=a_to_grain, a_mol_top_off_pct=a_top_off,
                c_magma_brix=pf_c_magma_brix, c_remelt_brix=pf_c_remelt_brix,
                injection_water_temp_F=pf_injection_water_temp_F,
                condenser_leg_temp_drop_F=pf_condenser_leg_temp_drop_F,
                iterations=iterations,
            )

        st.success(f"Pan floor solved — V1 steam {pan_floor.total_V1_steam_lb_hr:,.0f} lb/hr, "
                   f"exhaust steam {pan_floor.total_exhaust_steam_lb_hr:,.0f} lb/hr")
        pan_ok = True
    except Exception as exc:
        st.error(f"Pan floor failed to solve: {exc}")

# ============================================================================
# EVAPORATION TAB — Pre + N sets, each independently on/off
# ============================================================================
evap_ok = False
pre_3 = None
evap_station = []
v1_demand = v2_demand = v3_demand = v4_demand = 0.0
v1_delivered = v2_delivered = v3_delivered = v4_delivered = 0.0

with tab_evap:
    st.subheader("Evaporation Station")
    if not (heat_ok and pan_ok):
        st.warning("Solve Juice Heating and Pan Floor first (see their tabs for errors) — "
                   "the V1 vapor demand comes from both.")
    else:
        st.markdown("**Pre-Evaporator**")
        pe1, pe2, pe3, pe4 = st.columns(4)
        pre_active = pe1.checkbox("Pre-Evaporator active", value=True)
        pre_area = pe2.number_input("Pre area (ft²)", value=35000.0, step=1000.0, disabled=not pre_active)
        pre_dessin = pe3.number_input("Pre Dessin coefficient", value=18000.0, step=500.0, disabled=not pre_active)
        pre_level = pe4.number_input("Pre liquid level (ft)", value=2.0, step=0.5, disabled=not pre_active)

        st.markdown("**Evaporator Sets** — add/remove rows, each row is one set. Effect *k*'s own vapor "
                    "feeds header V*k* (effect 1 → V1, effect 2 → V2, ...); the last effect never bleeds "
                    "(its vapor goes to the condenser), so an N-effect set can supply V1..V(N-1).")
        set_defaults = pd.DataFrame([
            {"Active": True, "Name": "Set 1 (4-eff 25k ft²)",
             "Effect Areas (ft², comma-sep)": "25000,25000,25000,25000",
             "Supply Steam (psia)": float(fabrication_exhaust_psia), "Last Effect (psia)": 2.4,
             "Dessin Coeff": 18000.0, "Liquid Level (ft)": 2.0},
            {"Active": True, "Name": "Set 2 (4-eff 12k ft²)",
             "Effect Areas (ft², comma-sep)": "12000,12000,12000,12000",
             "Supply Steam (psia)": float(fabrication_exhaust_psia), "Last Effect (psia)": 2.4,
             "Dessin Coeff": 18000.0, "Liquid Level (ft)": 2.0},
            {"Active": True, "Name": "Set 3 (3-eff 11-9k ft²)",
             "Effect Areas (ft², comma-sep)": "11000,9000,9000",
             "Supply Steam (psia)": 20.0, "Last Effect (psia)": 2.4,
             "Dessin Coeff": 18000.0, "Liquid Level (ft)": 2.0},
        ])
        sets_df = st.data_editor(
            set_defaults, hide_index=True, use_container_width=True, num_rows="dynamic", key="evap_set_editor",
            column_config={"Active": st.column_config.CheckboxColumn()},
        )

        st.markdown("**Station-wide defaults**")
        d1, d2, d3, d4, d5 = st.columns(5)
        target_brix_out = d1.number_input("Target syrup brix", value=float(syrup_brix), step=0.5)
        default_dessin = d2.number_input("Default Dessin coeff", value=18000.0, step=500.0)
        default_level = d3.number_input("Default liquid level (ft)", value=2.0, step=0.5)
        n_iterations = int(d4.number_input("U-ratio balancing iterations", value=10, step=1))
        dampening = d5.number_input("Dampening", value=0.2, step=0.05, format="%.2f")
        d6, d7 = st.columns(2)
        evap_injection_water_temp_F = d6.number_input(
            "Injection water temp (°F)", value=float(pf_injection_water_temp_F), step=1.0,
            help="Matches the Pan Floor tab's value by default — condenser makeup water temp.",
        )
        evap_condenser_leg_temp_drop_F = d7.number_input(
            "Condenser leg ΔT (°F)", value=float(pf_condenser_leg_temp_drop_F), step=0.5,
        )

        active_sets = sets_df[sets_df["Active"]].reset_index(drop=True)

        # Effect count per active set — needed up front to know which sets are
        # even eligible to supply V2/V3/V4 (a set needs >= grade effects).
        # Lenient here (bad input just drops the set from eligibility); the
        # real validation with a clear error happens in the solve step below.
        n_eff_by_name = {}
        for _, row in active_sets.iterrows():
            try:
                n_eff_by_name[row["Name"]] = len(parse_floats(row["Effect Areas (ft², comma-sep)"]))
            except Exception:
                n_eff_by_name[row["Name"]] = 0

        v1_consumers = (["Pre-Evaporator"] if pre_active else []) + \
            [n for n in active_sets["Name"] if n_eff_by_name.get(n, 0) >= 1]
        v2_consumers = [n for n in active_sets["Name"] if n_eff_by_name.get(n, 0) >= 2]
        v3_consumers = [n for n in active_sets["Name"] if n_eff_by_name.get(n, 0) >= 3]
        v4_consumers = [n for n in active_sets["Name"] if n_eff_by_name.get(n, 0) >= 4]

        v1_demand = par_heaters.total_V1_steam_lb_hr + pan_floor.total_V1_steam_lb_hr
        v2_demand = par_heaters.total_V2_steam_lb_hr + pan_floor.total_V2_steam_lb_hr
        v3_demand = par_heaters.total_V3_steam_lb_hr + pan_floor.total_V3_steam_lb_hr
        v4_demand = par_heaters.total_V4_steam_lb_hr + pan_floor.total_V4_steam_lb_hr

        st.markdown("**Vapor Bleed Distribution** — only eligible consumers are listed for each grade "
                    "(effect *k* of a set can only supply V*k*); this splits each grade's total demand "
                    "(heaters + pans) across the Pre-Evaporator (V1 only) and the matching effect of "
                    "each evaporator set.")
        v1_default_pcts = {"Pre-Evaporator": 80.0}
        for cname in v1_consumers:
            if "Set 1" in cname:
                v1_default_pcts[cname] = 13.0
            elif "Set 2" in cname:
                v1_default_pcts[cname] = 7.0
        v1_share, v1_dist_df = vapor_dist_editor(1, v1_demand, v1_consumers, "v1_dist_editor", v1_default_pcts)
        v2_share, v2_dist_df = vapor_dist_editor(2, v2_demand, v2_consumers, "v2_dist_editor")
        v3_share, v3_dist_df = vapor_dist_editor(3, v3_demand, v3_consumers, "v3_dist_editor")
        v4_share, v4_dist_df = vapor_dist_editor(4, v4_demand, v4_consumers, "v4_dist_editor")
        share_by_grade = {1: v1_share, 2: v2_share, 3: v3_share, 4: v4_share}

        try:
            if pre_active:
                pre_bleed = v1_share("Pre-Evaporator")
                pre_3 = PreEvaporator(
                    juice_in=SugarStream.copy(cj),
                    supply_steam=EvaporatorSteam(P_psia=fabrication_exhaust_psia),
                    vapor_bleed_lb_per_hr=pre_bleed,
                    area_ft2=pre_area,
                    liquid_level_ft=pre_level,
                    dessin_coefficient=pre_dessin,
                )
                juice_to_sets = SugarStream.copy(pre_3.juice_out)
            else:
                pre_3 = None
                juice_to_sets = SugarStream.copy(cj)

            set_configs = []
            for _, row in active_sets.iterrows():
                areas = parse_floats(row["Effect Areas (ft², comma-sep)"])
                n_eff = len(areas)
                if n_eff < 1:
                    raise ValueError(f"{row['Name']}: at least one effect area required")
                # bleeds[k] (0-indexed) is drawn off effect k+1, feeding header V(k+1).
                # The last effect never bleeds (its vapor goes to the condenser).
                bleeds = [share_by_grade[k + 1](row["Name"]) if (k + 1) in share_by_grade else 0.0
                          for k in range(n_eff - 1)]
                set_configs.append({
                    "name": row["Name"],
                    "effect_areas_ft2": areas,
                    "supply_steam_psia": row["Supply Steam (psia)"],
                    "last_effect_psia": row["Last Effect (psia)"],
                    "vapor_bleeds": bleeds,
                    "dessin_coefficient": row["Dessin Coeff"],
                    "liquid_level_ft": row["Liquid Level (ft)"],
                })

            if set_configs:
                evap_station = solve_evaporator_sets(
                    juice_brix=juice_to_sets.brix,
                    juice_purity=juice_to_sets.purity,
                    juice_flow_lb_per_hr=juice_to_sets.flow_lb_per_hr,
                    juice_temp_deg_F=juice_to_sets.temp_deg_F,
                    juice_pressure_psia=40,
                    target_brix_out=target_brix_out,
                    dessin_coefficient=default_dessin,
                    liquid_level_ft=default_level,
                    injection_water_temp_F=evap_injection_water_temp_F,
                    condenser_leg_temp_drop_F=evap_condenser_leg_temp_drop_F,
                    n_iterations=n_iterations,
                    dampening=dampening,
                    set_configs=set_configs,
                    verbose=False,
                )
            else:
                evap_station = []
                st.warning("No evaporator sets active — station not solved.")

            v1_delivered = sum(v1_share(c) for c in v1_consumers)
            v2_delivered = sum(v2_share(c) for c in v2_consumers)
            v3_delivered = sum(v3_share(c) for c in v3_consumers)
            v4_delivered = sum(v4_share(c) for c in v4_consumers)
            evap_ok = True
        except Exception as exc:
            st.error(f"Evaporation failed to solve: {exc}")
            pre_3 = None
            evap_station = []

        if evap_ok:
            st.divider()
            vapor_summary_df = pd.DataFrame(
                [["V1", v1_demand, v1_delivered], ["V2", v2_demand, v2_delivered],
                 ["V3", v3_demand, v3_delivered], ["V4", v4_demand, v4_delivered]],
                columns=["Grade", "Demand (lb/hr)", "Delivered (lb/hr)"],
            )
            st.dataframe(vapor_summary_df, hide_index=True, use_container_width=True)

            if pre_3 is not None:
                st.markdown(f"**Pre-Evaporator** — {pre_3.vapor_bleed_lb_per_hr:,.0f} lb/hr bleed, "
                            f"{pre_3.exhaust_required_lb_per_hr:,.0f} lb/hr exhaust, "
                            f"U ratio {pre_3.U_ratio:.3f}")
                fig = pre_3.generate_pfd(show=False)
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

            for evap in evap_station:
                syrup_out = evap.evaporator_list[-1].juice_side_out
                st.markdown(f"**{evap.name}** — steam {evap.supply_steam.flow_lb_per_hr:,.0f} lb/hr, "
                            f"syrup out {syrup_out.flow_lb_per_hr:,.0f} lb/hr @ {syrup_out.brix:.1f} Bx, "
                            f"U ratio {evap.U_ratio_avg:.3f}")
                fig = evap.generate_pfd(show=False, pre_evap=pre_3)
                st.pyplot(fig, use_container_width=True)
                plt.close(fig)

            if evap_station:
                summary_rows = [
                    (evap.name, evap.supply_steam.flow_lb_per_hr,
                     evap.evaporator_list[-1].juice_side_out.flow_lb_per_hr,
                     evap.evaporator_list[-1].juice_side_out.brix, evap.U_ratio_avg,
                     evap.clean_condensate, evap.dirty_condensate)
                    for evap in evap_station
                ]
                st.dataframe(
                    pd.DataFrame(summary_rows, columns=["Set", "Steam (lb/hr)", "Syrup Out (lb/hr)",
                                                         "Syrup Brix", "U Ratio", "Clean Condensate",
                                                         "Dirty Condensate"]),
                    use_container_width=True, hide_index=True,
                )

# ============================================================================
# STEAM & EXHAUST SUMMARY TAB
# ============================================================================
steam_ok = False
exh_dict = {}
total_exhaust_required = 0.0
da = None

with tab_steam:
    st.subheader("Steam & Exhaust Summary")
    if not evap_ok:
        st.info("Solve Evaporation first (see its tab) to compute the exhaust steam summary.")
    else:
        st.markdown("**Deaerator**")
        dz1, dz2, dz3, dz4 = st.columns(4)
        da_psig = dz1.number_input("Deaerator pressure (psig)", value=10.0, step=1.0)
        da_water_temp = dz2.number_input("Water in temp (°F)", value=200.0, step=5.0)
        da_water_flow = dz3.number_input("Water in flow (lb/hr)", value=800000.0, step=10000.0)
        da_vent_pct = dz4.number_input("Vent (%)", value=4.0, step=0.5)
        da = Deaerator(deaerator_psig=da_psig, water_in_deg_F=da_water_temp,
                        water_in_lb_hr=da_water_flow, vent_pct=da_vent_pct)

        exhaust_for_Pre = pre_3.supply_steam.flow_lb_per_hr if pre_3 is not None else 0.0
        exhaust_for_evaporators = sum(evap.supply_steam.flow_lb_per_hr for evap in evap_station)
        exhaust_for_pans = pan_floor.total_exhaust_steam_lb_hr
        exhaust_for_heaters = par_heaters.total_exhaust_steam_lb_hr + clar_juice_heater.steam_required_lb_per_hr
        exhaust_for_da = da.steam_flow_lb_hr
        subtotal_exh = (exhaust_for_Pre + exhaust_for_evaporators + exhaust_for_pans
                         + exhaust_for_heaters + exhaust_for_da)
        exh_losses_pct = st.number_input("Exhaust losses (% of subtotal)", value=5.0, step=0.5)
        total_exhaust_required = subtotal_exh * (1 + exh_losses_pct / 100)

        exh_dict = {
            "Exhaust for Pre": exhaust_for_Pre,
            "Exhaust for Evaporators": exhaust_for_evaporators,
            "Exhaust for Pans": exhaust_for_pans,
            "Exhaust for Heaters": exhaust_for_heaters,
            "Exhaust for Deaerator": exhaust_for_da,
            "Exhaust Losses": subtotal_exh * exh_losses_pct / 100,
            "Total Exhaust Required": total_exhaust_required,
        }
        st.dataframe(pd.DataFrame(exh_dict.items(), columns=["Item", "lb/hr"]),
                     hide_index=True, use_container_width=True)

        st.markdown("**Vapor Bleed Demand vs. Delivered** (set on the Evaporation tab)")
        vapor_check_df = pd.DataFrame(
            [["V1", v1_demand, v1_delivered], ["V2", v2_demand, v2_delivered],
             ["V3", v3_demand, v3_delivered], ["V4", v4_demand, v4_delivered]],
            columns=["Grade", "Demand (lb/hr)", "Delivered (lb/hr)"],
        )
        st.dataframe(vapor_check_df, hide_index=True, use_container_width=True)

        st.caption("See the Turbines & Boiler tab for live steam demand, exhaust availability, and "
                   "makeup steam, which build on the exhaust total computed here.")
        steam_ok = True

# ============================================================================
# TURBINES & BOILER TAB
# ============================================================================
turb_ok = False
knf_trbs = mill_trbs = misc_trbs = None
blrs = None
live_steam_dict = {}
exhaust_available = 0.0
makeup_steam = 0.0

with tab_turb:
    st.subheader("Turbine Steam Demand & Boiler Room")
    if not steam_ok:
        st.warning("Solve the Exhaust Summary tab first — makeup steam needs the total exhaust required.")
    else:
        tons_fiber_hr = mills.cane_fiber_pct / 100 * mills.cane_tph
        st.caption(f"Fiber rate from Mill Floor: {tons_fiber_hr:,.1f} ton fiber/hr")

        st.markdown("**Live Steam Generation** — the boiler header condition used as the enthalpy "
                    "source for every turbine group below (throttled to each group's own inlet "
                    "pressure, matching SMSC_Balance.py's approach).")
        lg1, lg2, lg3 = st.columns(3)
        live_gen_psig = lg1.number_input("Live steam generated (psig)", value=185.0, step=5.0)
        live_gen_superheat = lg2.number_input("Superheat (°F above sat., 0 = saturated)", value=0.0, step=5.0)
        live_gen_quality = lg3.number_input("Quality (used if superheat = 0)", value=1.0, step=0.01,
                                             min_value=0.0, max_value=1.0, format="%.2f")
        live_gen_psia = live_gen_psig + 14.696
        live_steam_sat = SteamStream(P=live_gen_psia, x=1)
        if live_gen_superheat > 0:
            live_steam_gen = SteamStream(P=live_gen_psia, T=live_steam_sat.T + live_gen_superheat)
        else:
            live_steam_gen = SteamStream(P=live_gen_psia, x=live_gen_quality)

        def _group_steam(psig):
            return SteamStream(P=psig + 14.696, h=live_steam_gen.h)

        try:
            st.markdown("**Cane Prep (Knife) Turbines**")
            kg1, kg2 = st.columns(2)
            knf_live_psig = kg1.number_input("Knife live steam (psig)", value=165.0, step=5.0, key="knf_live")
            knf_exh_psig = kg2.number_input("Knife exhaust (psig)", value=16.0, step=1.0, key="knf_exh")
            knf_defaults = pd.DataFrame([
                {"Name": "Knife 1", "HP per Ton Fiber/hr": 16.0, "Isentropic Eff (%)": 50.0},
                {"Name": "Knife 2", "HP per Ton Fiber/hr": 16.0, "Isentropic Eff (%)": 50.0},
                {"Name": "Knife 3", "HP per Ton Fiber/hr": 16.0, "Isentropic Eff (%)": 50.0},
            ])
            knf_df = st.data_editor(knf_defaults, hide_index=True, use_container_width=True,
                                     num_rows="dynamic", key="knf_editor")
            knf_trbs = CanePrepTurbines(
                name_list=list(knf_df["Name"]),
                hp_ton_fiber_hr=list(knf_df["HP per Ton Fiber/hr"]),
                isentropic_efficiency=list(knf_df["Isentropic Eff (%)"]),
                live_steam_object=_group_steam(knf_live_psig),
                exhaust_psia=knf_exh_psig + 14.696,
                tons_fiber_hr=tons_fiber_hr,
            )

            st.markdown("**Mill Turbines**")
            mg1, mg2 = st.columns(2)
            mill_live_psig = mg1.number_input("Mill live steam (psig)", value=170.0, step=5.0, key="mill_live")
            mill_exh_psig = mg2.number_input("Mill exhaust (psig)", value=15.0, step=1.0, key="mill_exh")
            mill_hp_defaults = [18.0, 16.0, 16.0, 16.0, 16.0, 18.0]
            mill_defaults = pd.DataFrame([
                {"HP per Ton Fiber/hr": mill_hp_defaults[i] if i < len(mill_hp_defaults) else 16.0,
                 "Isentropic Eff (%)": 50.0}
                for i in range(mills.number_of_mills)
            ])
            mill_df = st.data_editor(mill_defaults, hide_index=True, use_container_width=True,
                                      num_rows="dynamic", key="mill_trb_editor")
            mill_trbs = MillTurbines(
                hp_ton_fiber_hr=list(mill_df["HP per Ton Fiber/hr"]),
                isentropic_efficiency=list(mill_df["Isentropic Eff (%)"]),
                live_steam_object=_group_steam(mill_live_psig),
                exhaust_psia=mill_exh_psig + 14.696,
                tons_fiber_hr=tons_fiber_hr,
            )

            st.markdown("**Auxiliary Turbines** (fans, pumps, misc.)")
            ag1, ag2, ag3 = st.columns(3)
            aux_group_name = ag1.text_input("Group name", value="Fan and Pump Turbines")
            aux_live_psig = ag2.number_input("Aux live steam (psig)", value=170.0, step=5.0, key="aux_live")
            aux_exh_psig = ag3.number_input("Aux exhaust (psig)", value=16.0, step=1.0, key="aux_exh")
            aux_defaults = pd.DataFrame([
                {"Name": "ID 123", "HP": 750.0, "Isentropic Eff (%)": 50.0},
                {"Name": "ID 4", "HP": 235.0, "Isentropic Eff (%)": 50.0},
                {"Name": "ID 5", "HP": 400.0, "Isentropic Eff (%)": 50.0},
                {"Name": "ID 6", "HP": 795.0, "Isentropic Eff (%)": 50.0},
                {"Name": "ID 7", "HP": 1200.0, "Isentropic Eff (%)": 50.0},
                {"Name": "FD 7", "HP": 233.0, "Isentropic Eff (%)": 50.0},
                {"Name": "ID 8", "HP": 1300.0, "Isentropic Eff (%)": 50.0},
                {"Name": "FD 8", "HP": 350.0, "Isentropic Eff (%)": 50.0},
                {"Name": "BFW 1", "HP": 400.0, "Isentropic Eff (%)": 50.0},
                {"Name": "BFW 2", "HP": 400.0, "Isentropic Eff (%)": 50.0},
                {"Name": "BFW 3", "HP": 400.0, "Isentropic Eff (%)": 50.0},
                {"Name": "JCE 1", "HP": 400.0, "Isentropic Eff (%)": 50.0},
            ])
            aux_df = st.data_editor(aux_defaults, hide_index=True, use_container_width=True,
                                     num_rows="dynamic", key="aux_trb_editor")
            misc_trbs = AuxillaryTurbines(
                group_name=aux_group_name,
                name_list=list(aux_df["Name"]),
                hp_list=list(aux_df["HP"]),
                isentropic_efficiency=list(aux_df["Isentropic Eff (%)"]),
                live_steam_object=_group_steam(aux_live_psig),
                exhaust_psia=aux_exh_psig + 14.696,
            )

            st.markdown("**Losses & Jets**")
            lj1, lj2 = st.columns(2)
            live_steam_jets_lb_hr = lj1.number_input("Live steam for jets (lb/hr)", value=25000.0, step=1000.0)
            live_steam_loss_pct = lj2.number_input("Live steam losses (% of subtotal)", value=2.0, step=0.5)

            live_steam_subtotal = (knf_trbs.total_inlet_flow_lb_hr + mill_trbs.total_inlet_flow_lb_hr
                                    + misc_trbs.total_inlet_flow_lb_hr + live_steam_jets_lb_hr)
            live_steam_loss_lb_hr = live_steam_subtotal * live_steam_loss_pct / 100
            live_steam_total_lb_hr = live_steam_subtotal + live_steam_loss_lb_hr
            exhaust_available = (knf_trbs.total_exhaust_available_lb_hr + mill_trbs.total_exhaust_available_lb_hr
                                  + misc_trbs.total_exhaust_available_lb_hr)
            makeup_steam = max(total_exhaust_required - exhaust_available, 0.0)

            live_steam_dict = {
                "Cane Prep Turbines": knf_trbs.total_inlet_flow_lb_hr,
                "Mill Turbines": mill_trbs.total_inlet_flow_lb_hr,
                "Fan and Pump Turbines": misc_trbs.total_inlet_flow_lb_hr,
                "Steam Jets": live_steam_jets_lb_hr,
                "Live Steam Losses": live_steam_loss_lb_hr,
                "Total Live Steam": live_steam_total_lb_hr,
            }
            st.dataframe(pd.DataFrame(live_steam_dict.items(), columns=["Item", "lb/hr"]),
                         hide_index=True, use_container_width=True)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Live Steam Demand", f"{live_steam_total_lb_hr:,.0f} lb/hr")
            c2.metric("Exhaust Required", f"{total_exhaust_required:,.0f} lb/hr")
            c3.metric("Exhaust Available from Turbines", f"{exhaust_available:,.0f} lb/hr")
            c4.metric("Makeup Required", f"{makeup_steam:,.0f} lb/hr")

            st.markdown("**Boiler Room**")
            b1, b2, b3, b4 = st.columns(4)
            blr_efficiency = b1.number_input("Boiler efficiency (%)", value=60.0, step=1.0)
            blr_pressure_psig = b2.number_input("Boiler pressure (psig)", value=float(live_gen_psig), step=5.0)
            blr_superheat = b3.number_input("Boiler superheat (°F)", value=float(live_gen_superheat), step=5.0)
            blr_capacity = b4.number_input("Boiler capacity (lb/hr, 0 = unlimited)", value=900000.0, step=10000.0)
            b5, b6 = st.columns(2)
            use_da_fw_temp = b5.checkbox("Feedwater temp = Deaerator water out", value=True)
            manual_fw_temp = b6.number_input("Feedwater temp (°F, used if unchecked)", value=230.0, step=5.0,
                                              disabled=use_da_fw_temp)
            fw_temp = da.water_out.T if (use_da_fw_temp and da is not None) else manual_fw_temp

            blrs = Boiler(
                bagasse=mills.bagasse_stream,
                efficiency=blr_efficiency,
                pressure_psig=blr_pressure_psig,
                deg_superheat=blr_superheat,
                feed_water_temp=fw_temp,
                capacity=blr_capacity,
                name="All Boilers",
            )
            c1, c2 = st.columns(2)
            c1.metric("Steam Available from Bagasse", f"{blrs.steam_availabe_lb_hr:,.0f} lb/hr")
            c2.metric("Live Steam Demand vs. Available",
                      f"{live_steam_total_lb_hr:,.0f} / {blrs.steam_availabe_lb_hr:,.0f} lb/hr")

            fig = knf_trbs.generate_pfd(show=False)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
            fig = mill_trbs.generate_pfd(show=False)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)
            fig = misc_trbs.generate_pfd(show=False)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

            turb_ok = True
        except Exception as exc:
            st.error(f"Turbines/Boiler failed to solve: {exc}")

# ============================================================================
# COOLING TOWER TAB
# ============================================================================
cool_ok = False
ctwrs = None

with tab_cool:
    st.subheader("Cooling Tower System")
    if not (pan_ok and evap_ok):
        st.warning("Solve Pan Floor and Evaporation first — the cooling tower collects every "
                   "condenser from both.")
    else:
        ct1, ct2, ct3, ct4 = st.columns(4)
        ct_cool_water_temp = ct1.number_input("Cool water temp (°F)", value=85.0, step=1.0)
        ct_pct_blowdown = ct2.number_input("Blowdown (%)", value=10.0, step=1.0)
        ct_makeup_water_temp = ct3.number_input("Makeup water temp (°F)", value=70.0, step=1.0)
        ct_iterations = int(ct4.number_input("Solver iterations", value=20, step=1, key="ct_iterations"))

        try:
            condenser_list = list(pan_floor.pan_condensers)
            for evap in evap_station:
                condenser_list.append(evap.condenser)

            ctwrs = CoolingTowerSystem(
                condensers=condenser_list,
                cool_water_temp_F=ct_cool_water_temp,
                percent_blowdown=ct_pct_blowdown,
                makeup_water_temp_F=ct_makeup_water_temp,
                iterations=ct_iterations,
                name="Cooling Tower System",
            )

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Vapor Condensed", f"{ctwrs.total_vapor_lb_hr:,.0f} lb/hr")
            c2.metric("Injection Water Demand", f"{ctwrs.total_injection_water_lb_hr:,.0f} lb/hr")
            c3.metric("Delivered Water Temp", f"{ctwrs.delivered_water_temp_F:.1f} °F")
            c4.metric("Makeup Required", f"{ctwrs.makeup_lb_hr:,.0f} lb/hr")

            c1, c2, c3 = st.columns(3)
            c1.metric("Evaporation Loss", f"{ctwrs.evaporated_lb_hr:,.0f} lb/hr")
            c2.metric("Blowdown", f"{ctwrs.blowdown_lb_hr:,.0f} lb/hr")
            c3.metric("Surplus", f"{ctwrs.surplus_lb_hr:,.0f} lb/hr")

            st.subheader("Process Flow Diagram")
            fig = ctwrs.generate_pfd(show=False)
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

            st.subheader("Balance Check")
            bal_df = pd.DataFrame([ctwrs.balance_check])
            st.dataframe(bal_df, use_container_width=True, hide_index=True)

            cool_ok = True
        except Exception as exc:
            st.error(f"Cooling tower failed to solve: {exc}")

# ============================================================================
# CONDENSATE BALANCE TAB
# ============================================================================
cond_ok = False
condensate_balance = None

with tab_cond:
    st.subheader("Condensate Balance")
    if not (heat_ok and pan_ok and evap_ok and steam_ok and cool_ok):
        st.warning("Solve Juice Heating, Pan Floor, Evaporation, Exhaust Summary, and Cooling Tower "
                   "first — condensate supply and water demand both draw from those sections.")
    else:
        try:
            clean_condensate_dict = {
                "Pre-Evaporator": pre_3.clean_condensate if pre_3 is not None else 0.0,
                "Evaporator Sets (Effect 1s)": sum(evap.clean_condensate for evap in evap_station),
                "Pan Floor - Exhaust Pans": pan_floor.clean_condensate,
                "Juice Heaters - Exhaust Station": par_heaters.clean_condensate,
                "Clarified Juice Heater (Exhaust)": flash_condensate(
                    clar_juice_heater.steam_required_lb_per_hr, clar_juice_heater.hot_stream.T),
            }
            dirty_condensate_dict = {
                "Evaporator Sets (Effects 2+)": sum(evap.dirty_condensate for evap in evap_station),
                "Pan Floor - V1-V4 Pans": pan_floor.dirty_condensate,
                "Juice Heaters - V1-V4 Station": par_heaters.dirty_condensate,
            }

            st.markdown("**Available Condensate**")
            avail_df = pd.DataFrame(
                list(clean_condensate_dict.items()) + list(dirty_condensate_dict.items()),
                columns=["Source", "lb/hr"],
            )
            avail_df.insert(1, "Type", ["Clean"] * len(clean_condensate_dict) + ["Dirty"] * len(dirty_condensate_dict))
            st.dataframe(avail_df, hide_index=True, use_container_width=True)

            # Wash water differs by boiling scheme — collect whichever centrifugals exist.
            if is_fbdm:
                cent_wash_water_lb_hr = (pan_floor.A1_centrifugals.wash_water_lb_hr
                                          + pan_floor.A2_centrifugals.wash_water_lb_hr
                                          + pan_floor.B_centrifugals.wash_water_lb_hr
                                          + pan_floor.C_centrifugals.wash_water_lb_hr)
            elif is_tbdm:
                cent_wash_water_lb_hr = (pan_floor.A_centrifugals.wash_water_lb_hr
                                          + pan_floor.B_centrifugals.wash_water_lb_hr
                                          + pan_floor.C_centrifugals.wash_water_lb_hr)
            else:
                cent_wash_water_lb_hr = (pan_floor.A_centrifugals.wash_water_lb_hr
                                          + pan_floor.C_centrifugals.wash_water_lb_hr)
            pan_dilution_water_lb_hr = pan_floor.total_water.flow_lb_per_hr - cent_wash_water_lb_hr

            st.markdown("**Water Demand — target temperatures**")
            wt1, wt2, wt3 = st.columns(3)
            imbibition_target_temp = wt1.number_input("Imbibition target temp (°F)", value=150.0, step=5.0)
            wash_water_target_temp = wt2.number_input("Wash water target temp (°F)", value=180.0, step=5.0)
            dilution_water_target_temp = wt3.number_input("Dilution water target temp (°F)", value=150.0, step=5.0)
            wt4, wt5 = st.columns(2)
            filter_water_target_temp = wt4.number_input("Filter wash water target temp (°F)", value=180.0, step=5.0)
            filter_water_method = wt5.selectbox("Filter wash water method", ["blended", "cooled"], index=0)

            gt1, gt2 = st.columns(2)
            well_water_temp_F = gt1.number_input(
                "Well water temp (°F)", value=float(ctwrs.makeup_water_temp_F) if ctwrs.makeup_water_temp_F
                else 70.0, step=1.0,
            )
            combined_condensate_temp_F = gt2.number_input("Combined condensate temp (°F)", value=210.0, step=5.0)

            filter_wash_water_lb_hr = clar.filter_wash_water_lb_hr

            condensate_demands = [
                CondensateDemand("Boiler Feed Water", flow_lb_hr=da.water_in_lb_hr, temp_F=da.water_in_deg_F,
                                  method="blended",
                                  note="Recommend usage of clean condensate, make up with minimal dirty "
                                       "condensate or well water"),
                CondensateDemand("Imbibition", flow_lb_hr=mills.imbibition_lb_hr,
                                  temp_F=imbibition_target_temp, method="blended"),
                CondensateDemand("Wash Water - Centrifugals", flow_lb_hr=cent_wash_water_lb_hr,
                                  temp_F=wash_water_target_temp, method="cooled"),
                CondensateDemand("Dilution Water - Pans/Molasses/Remelt", flow_lb_hr=pan_dilution_water_lb_hr,
                                  temp_F=dilution_water_target_temp, method="blended"),
                CondensateDemand("Mud Filter Wash Water", flow_lb_hr=filter_wash_water_lb_hr,
                                  temp_F=filter_water_target_temp, method=filter_water_method),
            ]

            condensate_balance = CondensateBalance(
                clean_condensate_dict, dirty_condensate_dict, condensate_demands,
                well_water_temp_F=well_water_temp_F,
                combined_condensate_temp_F=combined_condensate_temp_F,
                name="Condensate Balance",
            )

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Condensate Available", f"{condensate_balance.total_condensate_available_lb_hr:,.0f} lb/hr")
            c2.metric("Total Water Demand", f"{condensate_balance.total_water_demand_lb_hr:,.0f} lb/hr")
            c3.metric("Condensate Required", f"{condensate_balance.total_condensate_required_lb_hr:,.0f} lb/hr")
            c4.metric("Well Water Required", f"{condensate_balance.total_well_water_required_lb_hr:,.0f} lb/hr")

            st.markdown("**Demand Detail**")
            demand_rows = [
                (d.name, d.flow_lb_hr, d.temp_F, d.method, d.condensate_flow_lb_hr,
                 d.well_water_flow_lb_hr, d.condensate_pct, d.warning)
                for d in condensate_balance.demands
            ]
            st.dataframe(
                pd.DataFrame(demand_rows, columns=["Demand", "Flow (lb/hr)", "Target Temp (°F)", "Method",
                                                    "Condensate (lb/hr)", "Well Water (lb/hr)",
                                                    "Condensate %", "Warning"]),
                hide_index=True, use_container_width=True,
            )

            cond_ok = True
        except Exception as exc:
            st.error(f"Condensate balance failed to solve: {exc}")

# ============================================================================
# DOWNLOAD TAB
# ============================================================================
with tab_dl:
    st.write("Export everything solved so far to a styled Excel workbook.")
    if st.button("Build workbook", use_container_width=True):
        wb = new_workbook()
        mills.to_excel(wb)
        clar.to_excel(wb)
        if heat_ok:
            par_heaters.to_excel(wb)
            clar_juice_heater.to_excel(wb)
        if pan_ok:
            pan_floor.to_excel(wb)
        if evap_ok:
            if pre_3 is not None:
                pre_3.to_excel(wb)
            if evap_station:
                sets_to_excel(evap_station, workbook=wb)
        if steam_ok:
            da.to_excel(wb)
        if turb_ok:
            knf_trbs.to_excel(wb)
            mill_trbs.to_excel(wb)
            misc_trbs.to_excel(wb)
            blrs.to_excel(wb)
            steam_summary_to_excel(
                wb, live_steam_dict, exh_dict,
                exhaust_available_lb_hr=exhaust_available,
                makeup_steam_lb_hr=makeup_steam,
                steam_available_lb_hr=blrs.steam_availabe_lb_hr,
            )
        if cool_ok:
            ctwrs.to_excel(wb)
        if cond_ok:
            condensate_balance.to_excel(wb)
        buf = io.BytesIO()
        wb.save(buf)
        st.session_state["workbook_bytes"] = buf.getvalue()

    st.caption(
        "Included when solved: Mill Floor, Clarification, Juice Heating, Pan Floor, "
        "Pre-Evaporator + Evaporator Sets, Deaerator, Turbines (Knife/Mill/Auxiliary), "
        "Boiler, Steam Summary, Cooling Tower, Condensate Balance — the same sections "
        "main.py and SMSC_Balance.py write to their workbooks."
    )

    if "workbook_bytes" in st.session_state:
        st.download_button(
            "Download Excel workbook",
            data=st.session_state["workbook_bytes"],
            file_name="factory_balance.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
