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
from PreEvaporator import PreEvaporator
from EvaporatorSet import sets_to_excel
from multi_effect_solver_vers_2 import solve_evaporator_sets
from Deaerator import Deaerator

st.set_page_config(page_title="Factory Balance Trial", layout="wide")
st.title("Cane Sugar Factory Material & Energy Balance")
st.caption("Trial Streamlit walkthrough: Mill Floor → Clarification → Juice Heating → "
           "Pan Floor → Evaporation → Steam & Exhaust Summary.")

STEAM_TYPES = ["Exhaust", "V1", "V2", "V3", "V4"]


def parse_floats(s):
    if s is None:
        return []
    return [float(v) for v in str(s).replace(";", ",").split(",") if v.strip() != ""]


def build_bleeds(v1_amt, extra_list, n_eff):
    needed = max(n_eff - 1, 0)
    vals = [v1_amt] + list(extra_list)
    if len(vals) < needed:
        vals += [0.0] * (needed - len(vals))
    return vals[:needed]


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

tab_mill, tab_clar, tab_heat, tab_pan, tab_evap, tab_steam, tab_dl = st.tabs([
    "Mill Floor", "Clarification", "Juice Heating", "Pan Floor",
    "Evaporation", "Steam Summary", "Download",
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
        ["FBDM (Four Boiling Double Magma)", "TBDM (Three Boiling Double Magma)"],
        horizontal=True,
    )
    is_fbdm = scheme.startswith("FBDM")

    syrup_brix = st.number_input("Syrup brix (target)", value=65.0, step=0.5)
    syrup_lb_hr = cj.flow_lb_per_hr * cj.brix / syrup_brix
    syrup = SugarStream.copy(cj)
    syrup.flow_lb_per_hr = syrup_lb_hr
    syrup.brix = syrup_brix
    st.caption(f"Syrup feed: {syrup_lb_hr:,.0f} lb/hr @ {syrup_brix:.1f} Bx "
               f"(from clarified juice @ {cj.brix:.2f} Bx)")

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
    else:
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

    pans = pan_editor(f"pan_editor_{is_fbdm}", pan_defaults)
    st.markdown("**Centrifugals**")
    cens = cen_editor(f"cen_editor_{is_fbdm}", cen_defaults)

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
            iterations = int(s10.number_input("Solver iterations", value=15, step=1))

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
                iterations=iterations,
            )
        else:
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
v1_demand = 0.0
v1_delivered = 0.0

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

        st.markdown("**Evaporator Sets** — add/remove rows, each row is one set")
        set_defaults = pd.DataFrame([
            {"Active": True, "Name": "Set 1 (4-eff 25k ft²)",
             "Effect Areas (ft², comma-sep)": "25000,25000,25000,25000",
             "Supply Steam (psia)": float(fabrication_exhaust_psia), "Last Effect (psia)": 2.4,
             "Dessin Coeff": 18000.0, "Liquid Level (ft)": 2.0, "Extra Bleeds after Eff.1 (lb/hr)": ""},
            {"Active": True, "Name": "Set 2 (4-eff 12k ft²)",
             "Effect Areas (ft², comma-sep)": "12000,12000,12000,12000",
             "Supply Steam (psia)": float(fabrication_exhaust_psia), "Last Effect (psia)": 2.4,
             "Dessin Coeff": 18000.0, "Liquid Level (ft)": 2.0, "Extra Bleeds after Eff.1 (lb/hr)": ""},
            {"Active": True, "Name": "Set 3 (3-eff 11-9k ft²)",
             "Effect Areas (ft², comma-sep)": "11000,9000,9000",
             "Supply Steam (psia)": 20.0, "Last Effect (psia)": 2.4,
             "Dessin Coeff": 18000.0, "Liquid Level (ft)": 2.0, "Extra Bleeds after Eff.1 (lb/hr)": ""},
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

        active_sets = sets_df[sets_df["Active"]].reset_index(drop=True)
        consumers = (["Pre-Evaporator"] if pre_active else []) + list(active_sets["Name"])

        st.markdown("**V1 Vapor Bleed Distribution** — only active consumers are listed; "
                    "this splits total V1 demand (heaters + pans) across the Pre and each set's first effect.")
        if not consumers:
            st.warning("No V1 consumers active (Pre and all sets are off).")
            v1_dist_df = pd.DataFrame(columns=["Consumer", "% of V1 demand"])
        else:
            default_pcts = []
            for cname in consumers:
                if cname == "Pre-Evaporator":
                    default_pcts.append(80.0)
                elif "Set 1" in cname:
                    default_pcts.append(13.0)
                elif "Set 2" in cname:
                    default_pcts.append(7.0)
                else:
                    default_pcts.append(0.0)
            v1_dist_df = st.data_editor(
                pd.DataFrame({"Consumer": consumers, "% of V1 demand": default_pcts}),
                hide_index=True, use_container_width=True, num_rows="fixed", key="v1_dist_editor",
            )
            pct_sum = v1_dist_df["% of V1 demand"].sum()
            if pct_sum <= 0:
                st.warning("V1 distribution percentages sum to 0 — no V1 will be bled off.")
            elif abs(pct_sum - 100) > 0.01:
                st.caption(f"Percentages sum to {pct_sum:.1f}%, not 100% — normalizing proportionally.")

        v1_demand = par_heaters.total_V1_steam_lb_hr + pan_floor.total_V1_steam_lb_hr

        def v1_share(cname):
            if v1_dist_df.empty:
                return 0.0
            pct_sum = v1_dist_df["% of V1 demand"].sum()
            if pct_sum <= 0:
                return 0.0
            row = v1_dist_df[v1_dist_df["Consumer"] == cname]
            if row.empty:
                return 0.0
            return float(row["% of V1 demand"].iloc[0]) / pct_sum * v1_demand

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
                extra = parse_floats(row["Extra Bleeds after Eff.1 (lb/hr)"])
                bleeds = build_bleeds(v1_share(row["Name"]), extra, n_eff)
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
                    n_iterations=n_iterations,
                    dampening=dampening,
                    set_configs=set_configs,
                    verbose=False,
                )
            else:
                evap_station = []
                st.warning("No evaporator sets active — station not solved.")

            v1_delivered = (v1_share("Pre-Evaporator") if pre_active else 0.0) + sum(
                v1_share(row["Name"]) for _, row in active_sets.iterrows()
            )
            evap_ok = True
        except Exception as exc:
            st.error(f"Evaporation failed to solve: {exc}")
            pre_3 = None
            evap_station = []

        if evap_ok:
            st.divider()
            c1, c2 = st.columns(2)
            c1.metric("Total V1 Demand (heaters + pans)", f"{v1_demand:,.0f} lb/hr")
            c2.metric("V1 Delivered (Pre + set bleeds)", f"{v1_delivered:,.0f} lb/hr")

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

        c1, c2 = st.columns(2)
        c1.metric("Total V1 Demand", f"{v1_demand:,.0f} lb/hr")
        c2.metric("V1 Delivered (Pre + set bleeds)", f"{v1_delivered:,.0f} lb/hr")

        st.caption("Turbines, boiler, cooling tower, and condensate balance are not yet in this trial "
                   "— they'd be the natural next phase, chaining off this exhaust/V1 summary.")

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
        buf = io.BytesIO()
        wb.save(buf)
        st.session_state["workbook_bytes"] = buf.getvalue()

    if "workbook_bytes" in st.session_state:
        st.download_button(
            "Download Excel workbook",
            data=st.session_state["workbook_bytes"],
            file_name="factory_balance.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
