# Shared Excel station writers for pan-floor balances (Three/Four Boiling).
#
# Each helper writes one bordered In/Out table through a SheetWriter, with
# the same columns as neat_display: Flow, Solids, Pol, Water, Brix, Purity,
# ft³/hr — plus Total In / Total Out / Net rows that mirror the console
# output exactly.

HDRS = ["Stream", "Dir", "Flow (lb/hr)", "Solids (lb/hr)", "Pol (lb/hr)",
        "Water (lb/hr)", "Brix %", "Purity %", "ft³/hr"]
FMTS = ["@", "@", "#,##0", "#,##0", "#,##0", "#,##0", "0.0", "0.0", "#,##0"]

STEAM_TYPE_LABELS = {0: "Exhaust", 1: "V1", 2: "V2", 3: "V3", 4: "V4"}


def srow(label, dir_, s):
    """Table row from a SugarStream."""
    sol = s.solids_flow
    return (label, dir_, s.flow_lb_per_hr, sol, s.pol_flow,
            s.flow_lb_per_hr - sol, s.brix, s.purity, s.cu_ft_hr)


def wrow(label, dir_, flow):
    """Table row for a pure-water stream."""
    return (label, dir_, flow, 0, 0, flow, "", "", "")


def totals_rows(in_f, in_s, in_p, in_w, out_f, out_s, out_p, out_w):
    return [
        ("Total In",       "", in_f,  in_s,  in_p,  in_w,  "", "", ""),
        ("Total Out",      "", out_f, out_s, out_p, out_w, "", "", ""),
        ("Net (In - Out)", "", in_f - out_f, in_s - out_s,
                               in_p - out_p, in_w - out_w, "", "", ""),
    ]


def pan_table(sw, pan, feed_names):
    rows = [srow(n, "In", f) for n, f in zip(feed_names, pan.feed_streams)]
    ff, fs = pan.feed_flow_lb_hr, pan.feed_solids_lb_hr
    fp   = sum(f.pol_flow for f in pan.feed_streams)
    mf   = pan.massecuite_flow_lb_hr
    evap = pan.water_evaporated_lb_hr
    rows.append(("Massecuite Out", "Out", mf, fs, fp, mf - fs,
                 pan.masse_brix, pan.masse_purity, mf / pan.massecuite.density))
    rows.append(wrow("Evaporated Water", "Out", evap))
    sw.table(HDRS, rows, fmts=FMTS,
             totals=totals_rows(ff, fs, fp, ff - fs,
                                mf + evap, fs, fp, mf - fs + evap))
    sw.row("Calandria steam type", STEAM_TYPE_LABELS.get(pan.steam_type, str(pan.steam_type)), "")
    sw.row("Calandria pressure", pan.calandria_pressure_psia, "psia", fmt="0.00")
    sw.row("Calandria steam flow", pan.steam_flow_lb_hr, "lb/hr", fmt="#,##0")


def cen_table(sw, cen):
    ms, mp = cen.massecuite_solids_lb_hr, cen.pol_in_lb_hr
    mf, ww = cen.massecuite_flow_lb_hr, cen.wash_water_lb_hr
    s_out, m_out = cen.sugar_stream, cen.molasses_stream
    rows = [
        ("Massecuite", "In", mf, ms, mp, mf - ms,
         cen.massecuite.masse_brix, cen.massecuite.masse_purity,
         mf / cen.massecuite.density),
        wrow("Wash Water", "In", ww),
        srow("Sugar Out", "Out", s_out),
        srow("Molasses Out", "Out", m_out),
    ]
    out_f = s_out.flow_lb_per_hr + m_out.flow_lb_per_hr
    out_s = s_out.solids_flow + m_out.solids_flow
    out_p = s_out.pol_flow + m_out.pol_flow
    sw.table(HDRS, rows, fmts=FMTS,
             totals=totals_rows(mf + ww, ms, mp, mf - ms + ww,
                                out_f, out_s, out_p, out_f - out_s))


def dil_table(sw, undiluted, diluted, label):
    water = diluted.flow_lb_per_hr - undiluted.flow_lb_per_hr
    rows = [
        srow(f"{label} (undiluted)", "In", undiluted),
        wrow("Dilution Water", "In", water),
        srow(f"{label} (diluted)", "Out", diluted),
    ]
    sw.table(HDRS, rows, fmts=FMTS,
             totals=totals_rows(
                 undiluted.flow_lb_per_hr + water, undiluted.solids_flow,
                 undiluted.pol_flow,
                 undiluted.flow_lb_per_hr - undiluted.solids_flow + water,
                 diluted.flow_lb_per_hr, diluted.solids_flow,
                 diluted.pol_flow,
                 diluted.flow_lb_per_hr - diluted.solids_flow))


def condenser_table(sw, condensers, water_in_F):
    """One barometric condenser per pan: condensers = [(name, Condenser)]."""
    hdrs = ["Condenser", "Vapor (lb/hr)", "Sat T (°F)", "h_fg (BTU/lb)",
            "Heat (MM BTU/hr)", "Inj Water (lb/hr)", "Inj Water (GPM)",
            "Water Out (°F)", "Total Out (lb/hr)"]
    fmts = ["@", "#,##0", "0.0", "0.0", "0.000", "#,##0", "#,##0", "0.0", "#,##0"]
    rows = []
    tv = th = tw = tg = tt = 0.0
    for name, c in condensers:
        inj = c.injection_water_flow_lb_hr
        gpm = inj / 500.4
        rows.append((name, c.vapor_flow_lb_hr, c.vapor_sat_temp_F,
                     c.vapor_h_fg_btu_lb, c.heat_load_btu_hr / 1e6,
                     inj, gpm, c.water_outlet_temp_F, c.total_outlet_flow_lb_hr))
        tv += c.vapor_flow_lb_hr
        th += c.heat_load_btu_hr / 1e6
        tw += inj
        tg += gpm
        tt += c.total_outlet_flow_lb_hr
    sw.table(hdrs, rows, fmts=fmts,
             totals=[("Total", tv, "", "", th, tw, tg, "", tt)])
    sw.row("Injection water supply temp", water_in_F, "°F", fmt="0.0")


def heatx_table(sw, unit, water_label):
    """Crystallizer/reheater — non-contact water, mass conserved."""
    m_in, m_out = unit.massecuite_in, unit.massecuite_out
    flow = unit.massecuite_flow_lb_hr
    sol  = flow * m_in.masse_brix / 100
    pol  = flow * m_in.masse_purity * m_in.masse_brix / 10000
    rows = [
        (f"Massecuite In  (T={unit.masse_temp_in_deg_F:.1f} °F)", "In",
         flow, sol, pol, flow - sol, m_in.masse_brix, m_in.masse_purity,
         flow / m_in.density),
        (f"Massecuite Out  (T={unit.masse_temp_out_deg_F:.1f} °F)", "Out",
         flow, sol, pol, flow - sol, m_out.masse_brix, m_out.masse_purity,
         flow / m_out.density),
    ]
    sw.table(HDRS, rows, fmts=FMTS)
    sw.row("ML purity in -> out",
           f"{m_in.ml_purity:.1f} -> {m_out.ml_purity:.1f}", "%")
    sw.row("Crystal content in -> out",
           f"{m_in.crystal_content:.1f} -> {m_out.crystal_content:.1f}", "%")
    sw.row("Duty", unit.duty_btu_hr, "BTU/hr", fmt="#,##0")
    sw.row(water_label, unit.water_lb_hr,
           f"lb/hr  ({unit.water_gpm:,.0f} gpm, "
           f"{unit.water_temp_in_deg_F:.0f} -> {unit.water_temp_out_deg_F:.0f} °F)",
           fmt="#,##0")
