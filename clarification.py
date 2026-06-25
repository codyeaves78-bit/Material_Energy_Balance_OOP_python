def specific_gravity(brix):
    """Specific gravity of a sugar solution at 68°F."""
    return (
        62.2511
        + 0.24081      * brix
        + 0.0007902404 * brix**2
        + 0.00000423954 * brix**3
        - 0.00000001657193 * brix**4
    ) / 62.4


def get_cp(brix):
    """Specific heat capacity of a sugar solution (BTU/lb·°F)."""
    return 0.9964 - 0.005656 * brix


def clarification_material_balance(
    mixed_juice_lb_per_hr: float,
    mixed_juice_brix_pct: float,
    mixed_juice_purity_pct: float,
    cane_tpd: float,   
    
    filter_wash_water_pct_on_cane: float,
    filter_cake_pct_on_cane: float,
    filter_cake_pol_pct: float,
    
    clarified_juice_purity: float,
    mixed_juice_temp_f: float = 80.0,
    limed_juice_cold_temp_f: float = 85.0, 
    limed_juice_hot_temp_f: float = 220.0,
    clarified_juice_temp_f: float = 205.0,
    lime_lb_per_ton_cane: float = 1.3, # lb per ton of cane
    lime_baume : float = 10,
    polymer_lb_per_ton_cane: float = .045, # lb per ton of cane
    polymer_conc_ppm: float = 5000, # generally between 5000 and 20000 ppm
    clarifier_underflow_pct_cane: float = 20, # 15 to 25 % usually
) -> dict:
    """
    Solve the clarification section material balance without iteration.

    Approach — uses external brix/pol balances as the starting point so no
    recycle loop needs to be solved:

      1. External pol balance (MJ in = CJ out + FC out) → CJ pol lb/hr.
      2. CJ brix lb/hr from CJ pol / clarified_juice_purity.
      3. External brix balance → FC brix lb/hr = MJ brix − CJ brix.
      4. FC purity from FC brix/pol; underflow assumed same purity as FC, brix = MJ brix.
      5. Filtrate from filter mass balance: UF + wash − FC.
      6. Limed juice = fixed external inputs + filtrate (one pass, no iteration).
      7. CJ flow from overall mass balance: fixed + wash − FC − flash vapor.

    Flash vapors are from the heat balance (Cp = get_cp(lj_brix), Hfg = 970 BTU/lb)
    sufficient to cool limed juice from limed_juice_hot_temp_f to 212 °F.

    Parameters
    ----------
    mixed_juice_lb_per_hr           : Mixed juice flow from mill (lb/hr).
    mixed_juice_brix_pct            : Mixed juice Brix (%).
    mixed_juice_purity_pct          : Mixed juice purity (%).
    cane_tpd                        : Cane throughput (short TPD).
    filter_wash_water_pct_on_cane   : Wash water applied to rotary filter (% on cane).
    filter_cake_pct_on_cane         : Filter cake discharge rate (% on cane).
    filter_cake_pol_pct             : Pol % in filter cake (factory-measured).
    clarified_juice_purity          : Target clarified juice purity (%).
    mixed_juice_temp_f              : Mixed juice temperature (°F).
    limed_juice_hot_temp_f          : Limed juice temperature after heaters (°F).
    clarified_juice_temp_f          : Clarified juice temperature leaving clarifier (°F).
    lime_lb_per_ton_cane            : Lime addition (lb per short ton of cane).
    lime_baume                      : Milk-of-lime concentration as Baumé (≈ mass %).
    polymer_lb_per_ton_cane         : Polymer dose (lb per short ton of cane).
    polymer_conc_ppm                : Polymer solution concentration (ppm by mass).
    clarifier_underflow_pct_cane    : Clarifier underflow as % of cane.

    Returns
    -------
    dict
        "streams"  — dict keyed by stream name, each with:
                     direction, lb_per_hr, gpm, brix_pct, pol_pct, purity_pct,
                     sg, brix_lb_per_hr, pol_lb_per_hr, pct_on_cane, temp_f
        "balance"  — dict with "in", "out", "difference" sub-dicts
                     (lb_per_hr, brix_lb_per_hr, pol_lb_per_hr)
        "flash_vapor_pct"            — flash vapor as % of limed juice
        "filter_cake_pol_lb_per_day" — pol lost to filter cake (lb/day)
    """
    FLASH_TEMP_F = 212.0
    HFG          = 970.0    # BTU/lb  (latent heat at 212°F)

    cane_lb_hr = cane_tpd * 2000 / 24

    # ── Fixed external inputs (lb/hr) — independent of filtrate recycle ────────
    lime_lb_hr       = cane_tpd * lime_lb_per_ton_cane / 24
    lime_water_lb_hr = lime_lb_hr / (lime_baume / 100) - lime_lb_hr  # Baumé treated as mass % — valid approximation at low concentrations
    polymer_lb_hr    = cane_tpd * polymer_lb_per_ton_cane / 24
    poly_water_lb_hr = polymer_lb_hr * 10**6 / polymer_conc_ppm - polymer_lb_hr
    wash_water_lb_hr = cane_lb_hr * filter_wash_water_pct_on_cane / 100
    fc_lb_hr         = cane_lb_hr * filter_cake_pct_on_cane / 100
    mol_lb_hr      = lime_lb_hr + lime_water_lb_hr
    poly_sol_lb_hr = polymer_lb_hr + poly_water_lb_hr
    fixed_lb_hr    = mixed_juice_lb_per_hr + mol_lb_hr + poly_sol_lb_hr

    # ── MJ brix/pol (lb/hr) ──────────────────────────────────────────────────
    mj_pol_pct    = mixed_juice_brix_pct * mixed_juice_purity_pct / 100
    mj_brix_lb_hr = mixed_juice_lb_per_hr * mixed_juice_brix_pct / 100
    mj_pol_lb_hr  = mixed_juice_lb_per_hr * mj_pol_pct / 100
 
    fc_pol_lb_hr  = fc_lb_hr * filter_cake_pol_pct / 100

    # ── CJ brix/pol (lb/hr) — from external pol and brix balances ────────────
    cj_pol_lb_hr  = mj_pol_lb_hr - fc_pol_lb_hr
    cj_brix_lb_hr = cj_pol_lb_hr * 100 / clarified_juice_purity

    # ── Filter cake brix — residual from external brix balance ───────────────
    fc_brix_lb_hr = mj_brix_lb_hr - cj_brix_lb_hr
    fc_purity     = fc_pol_lb_hr / fc_brix_lb_hr * 100
    fc_brix_pct   = fc_brix_lb_hr / fc_lb_hr * 100

    # ── Clarifier underflow — same purity as filter cake; brix assumed = MJ ─
    uf_purity     = fc_purity
    uf_brix_pct   = mixed_juice_brix_pct
    uf_pol_pct    = uf_brix_pct / 100 * uf_purity
    uf_lb_hr      = clarifier_underflow_pct_cane / 100 * cane_lb_hr
    uf_pol_lb_hr  = uf_lb_hr * uf_pol_pct / 100
    uf_brix_lb_hr = uf_lb_hr * uf_brix_pct / 100

    # ── Rotary filter — filtrate = underflow + wash − cake ───────────────────
    filtrate_lb_hr      = wash_water_lb_hr + uf_lb_hr - fc_lb_hr
    filtrate_pol_lb_hr  = uf_pol_lb_hr - fc_pol_lb_hr
    filtrate_brix_lb_hr = uf_brix_lb_hr - fc_brix_lb_hr
    filtrate_brix_pct = filtrate_brix_lb_hr / filtrate_lb_hr * 100
    filtrate_pol_pct  = filtrate_pol_lb_hr  / filtrate_lb_hr * 100
    filtrate_purity   = filtrate_pol_lb_hr  / filtrate_brix_lb_hr * 100

    # ── Limed juice — fixed external inputs + filtrate recycle ───────────────
    lj_lb_hr      = fixed_lb_hr + filtrate_lb_hr
    lj_brix_lb_hr = mj_brix_lb_hr + filtrate_brix_lb_hr
    lj_pol_lb_hr  = mj_pol_lb_hr  + filtrate_pol_lb_hr
    lj_brix_pct   = lj_brix_lb_hr / lj_lb_hr * 100
    lj_pol_pct    = lj_pol_lb_hr  / lj_lb_hr * 100
    
    # ── Flash Tank ────────────────────────────────────────────────────────────
    flash_vapor_lb_hr = lj_lb_hr * (limed_juice_hot_temp_f - 212) * get_cp(lj_brix_pct) / 970 if limed_juice_hot_temp_f > 212 else 0
    flash_vapor_pct   = flash_vapor_lb_hr / lj_lb_hr * 100
    fj_lb_hr          = lj_lb_hr - flash_vapor_lb_hr
    fj_brix_lb_hr     = lj_brix_lb_hr          # solids don't flash
    fj_pol_lb_hr      = lj_pol_lb_hr
    fj_brix_pct       = fj_brix_lb_hr / fj_lb_hr * 100
    fj_pol_pct        = fj_pol_lb_hr  / fj_lb_hr * 100

    # Complete clarified juice flows
    cj_lb_hr = fixed_lb_hr + wash_water_lb_hr - fc_lb_hr - flash_vapor_lb_hr
    cj_pol_pct = cj_pol_lb_hr / cj_lb_hr * 100
    cj_brix_pct = cj_brix_lb_hr / cj_lb_hr * 100

    # ── Pack Streams ──────────────────────────────────────────────────────────
    def _gpm(lb_hr, sg):
        return lb_hr / (sg * 8.34 * 60)

    raw = [
        # (name, direction, lb_hr, brix_pct, pol_pct, temp_f)
        ("Mixed Juice",         "In",       mixed_juice_lb_per_hr, mixed_juice_brix_pct, mj_pol_pct,    mixed_juice_temp_f),
        ("Lime",                "In",       lime_lb_hr,            0.0,                  0.0,           None),
        ("Water for Lime",      "In",       lime_water_lb_hr,      0.0,                  0.0,           None),
        ("Polymer",             "In",       polymer_lb_hr,         0.0,                  0.0,           None),
        ("Polymer Water",       "In",       poly_water_lb_hr,      0.0,                  0.0,           None),
        ("Filter Wash Water",   "In",       wash_water_lb_hr,      0.0,                  0.0,           None),
        ("Flash Vapors",        "Out",      flash_vapor_lb_hr,     0.0,                  0.0,           FLASH_TEMP_F),
        ("Clarified Juice",     "Out",      cj_lb_hr,              cj_brix_pct,          cj_pol_pct,      clarified_juice_temp_f),
        ("Filter Cake",         "Out",      fc_lb_hr,              fc_brix_pct,          filter_cake_pol_pct, None),
        ("Milk of Lime",        "Internal", mol_lb_hr,             0.0,                  0.0,           None),
        ("Polymer Solution",    "Internal", poly_sol_lb_hr,        0.0,                  0.0,           None),
        ("Limed Juice Cold",    "Internal", lj_lb_hr,              lj_brix_pct,          lj_pol_pct,    limed_juice_cold_temp_f),
        ("Limed Juice Hot",     "Internal", lj_lb_hr,              lj_brix_pct,          lj_pol_pct,    limed_juice_hot_temp_f),
        ("Flashed Juice",       "Internal", fj_lb_hr,              fj_brix_pct,          fj_pol_pct,    FLASH_TEMP_F),
        ("Clarifier Underflow", "Internal", uf_lb_hr,              uf_brix_pct,   uf_pol_pct,    None),
        ("Filtrate",            "Internal", filtrate_lb_hr,        filtrate_brix_pct,        filtrate_pol_pct,  None),
    ]

    streams = {}
    for name, direction, lb_hr, brix, pol, temp in raw:
        purity = pol / brix * 100 if brix > 0 else 0.0
        sg     = specific_gravity(brix) if brix > 0 else 1.0
        streams[name] = {
            "direction":       direction,
            "lb_per_hr":       lb_hr,
            "gpm":             _gpm(lb_hr, sg),
            "brix_pct":        brix,
            "pol_pct":         pol,
            "purity_pct":      purity,
            "sg":              sg,
            "brix_lb_per_hr":  lb_hr * brix / 100,
            "pol_lb_per_hr":   lb_hr * pol / 100,
            "pct_on_cane":     lb_hr / cane_lb_hr * 100,
            "temp_f":          temp,
        }

    # ── Balance Check (external streams only) ─────────────────────────────────
    balance_keys = ("lb_per_hr", "brix_lb_per_hr", "pol_lb_per_hr")
    totals = {"in": {}, "out": {}, "difference": {}}
    for key in balance_keys:
        in_  = sum(s[key] for s in streams.values() if s["direction"] == "In")
        out_ = sum(s[key] for s in streams.values() if s["direction"] == "Out")
        totals["in"][key]         = in_
        totals["out"][key]        = out_
        totals["difference"][key] = in_ - out_

    return {
        "streams":                    streams,
        "balance":                    totals,
        "flash_vapor_pct":            flash_vapor_pct,
        "filter_cake_pol_lb_per_day": fc_pol_lb_hr * 24,
    }


def extract_clarification_outputs(result: dict) -> dict:
    """Pull key clarification outputs from a clarification_material_balance result."""
    cj = result["streams"]["Clarified Juice"]
    fc = result["streams"]["Filter Cake"]
    return {
        "clarified_juice_lb_per_hr":  cj["lb_per_hr"],
        "clarified_juice_brix":       cj["brix_pct"],
        "clarified_juice_purity":     cj["purity_pct"],
        "filter_cake_lb_per_hr":      fc["lb_per_hr"],
        "filter_cake_brix_pct":       fc["brix_pct"],
        "filter_cake_pol_pct":        fc["pol_pct"],
        "filter_cake_pol_lb_per_day": result["filter_cake_pol_lb_per_day"],
    }


def display_clarification_balance(result: dict) -> None:
    """Print a formatted summary of a clarification_material_balance result."""
    streams = result["streams"]

    col_w   = [22, 10, 10, 10, 8, 8, 8, 8, 6]
    headers = ["Stream", "lb/hr", "GPM", "Brix lb/hr", "Brix%", "Pol%", "Purity%", "%Cane", "°F"]

    def _fmt(v):
        if v is None:          return "-"
        if isinstance(v, str): return v
        return f"{v:,.2f}"

    sep        = "  ".join("-" * w for w in col_w)
    header_row = "  ".join(h.ljust(w) for h, w in zip(headers, col_w))

    print("\nClarification Material Balance")
    print(sep)
    print(header_row)
    print(sep)

    for direction in ("In", "Out", "Internal"):
        group = {n: s for n, s in streams.items() if s["direction"] == direction}
        if not group:
            continue
        print(f"  -- {direction} --")
        for name, s in group.items():
            row = [
                name,
                f"{s['lb_per_hr']:,.0f}",
                f"{s['gpm']:,.0f}",
                f"{s['brix_lb_per_hr']:,.0f}",
                f"{s['brix_pct']:.2f}",
                f"{s['pol_pct']:.2f}",
                f"{s['purity_pct']:.1f}" if s["brix_pct"] > 0 else "-",
                f"{s['pct_on_cane']:.2f}",
                _fmt(s["temp_f"]),
            ]
            print("  ".join(v.ljust(w) for v, w in zip(row, col_w)))

    print(sep)
    bal = result["balance"]
    for label, key in (("In", "in"), ("Out", "out"), ("Diff", "difference")):
        row = [label, f"{bal[key]['lb_per_hr']:,.0f}", "",
               f"{bal[key]['brix_lb_per_hr']:,.1f}", "", "", "", "", ""]
        print("  ".join(v.ljust(w) for v, w in zip(row, col_w)))
    print(sep)

    print(f"\nFlash Vapor: {result['flash_vapor_pct']:.3f}% of limed juice")
    print(f"Filter Cake Pol Loss: {result['filter_cake_pol_lb_per_day']:,.0f} lb/day")


if __name__ == "__main__":
    # Inputs consistent with the mill_floor_material_balance example
    # (cane_tpd=17,000, cane_pol_pct=13.5, cane_fiber_pct=14.0,
    #  imbibition=25%, bagasse_pol=1.8%, last_roll_purity=72%,
    #  bagasse_moisture=49%, mix_juice_purity=88%)
    result = clarification_material_balance(
        mixed_juice_lb_per_hr=1_361_900,
        mixed_juice_brix_pct=15.34,
        mixed_juice_purity_pct=90.0,
        cane_tpd=17_000,
        filter_wash_water_pct_on_cane=8.0,
        filter_cake_pct_on_cane=6.0,
        filter_cake_pol_pct=2.0,
        clarified_juice_purity=90.0,
        limed_juice_hot_temp_f=220.0,
        lime_lb_per_ton_cane=1.3,
        lime_baume=10,
        polymer_lb_per_ton_cane=0.014,
        polymer_conc_ppm=5000,
        clarifier_underflow_pct_cane=20,
    )
    display_clarification_balance(result)
    print(extract_clarification_outputs(result))

    for key, value in result["streams"]["Clarified Juice"].items(): # example if you want details on a stream
        print(f"{key}: {value}")


