def mill_floor_material_balance(
    cane_tpd: float,
    cane_pol_pct: float,
    cane_fiber_pct: float,
    imbibition_pct_on_cane: float,
    bagasse_pol_pct: float,
    last_roll_purity: float,
    bagasse_moisture_pct: float,
    mix_juice_purity: float,
    number_of_mills: int,
    mill_1_fiber_rise_load_fraction: float = 0.35,
) -> dict:
    """
    Solve the mill floor material balance.

    Inputs are all in short tons per day (TPD) and percent (%) on a mass basis.

    Parameters
    ----------
    cane_tpd                : Cane throughput (TPD).
    cane_pol_pct            : Pol % in cane.
    cane_fiber_pct          : Fiber % in cane.
    imbibition_pct_on_cane  : Imbibition water as % on cane.
    bagasse_pol_pct         : Pol % in bagasse (last mill reading).
    last_roll_purity        : Purity of last roll juice (%).
    bagasse_moisture_pct    : Moisture % in bagasse.
    mix_juice_purity        : Mixed juice purity (%).
    number_of_mills                  : Number of mills in the mill train.
    mill_1_fiber_rise_load_fraction  : Fraction of the total cane→bagasse fiber %
                                       rise that Mill 1 handles in a single step
                                       (default 0.35).  Remaining rise is split
                                       equally across Mills 2 through N.
    mill_1_fiber_rise_load_fraction : The fraction of fiber % rise of cane in to bagasse out of mill one as a % of total fiber change (fib % cane - fib % bagasse)

    Returns
    -------
    dict
        Keys: "streams", "mill_extraction_pct", "balance"

        "streams" — dict keyed by stream name, each with:
            direction, tpd, tph, lb_per_hr,
            brix_pct, pol_pct, fiber_pct, moisture_pct,
            tons_brix, tons_pol, tons_fiber, tons_moisture, pct_on_cane

        "mill_extraction_pct" — pol extracted into juice vs pol in cane

        "balance" — dict with "in", "out", "difference" sub-dicts (TPD, tons brix,
            tons pol, tons fiber, tons moisture)

        "mill_balances" — list of per-mill dicts (one per mill, ordered 1→N):
            mill, bagasse_in_tpd, mac_in_tpd, mac_in_source,
            bagasse_out_tpd, juice_out_tpd, juice_out_dest
    """
    # ── Imbibition ───────────────────────────────────────────────────────────
    imb_tpd = cane_tpd * imbibition_pct_on_cane / 100
    imb_gpm = imb_tpd * 2000 / 24 / 60 / 8.3 # gpm of imbibition

    # ── Bagasse ──────────────────────────────────────────────────────────────
    bag_brix_pct     = bagasse_pol_pct / last_roll_purity * 100
    bag_fiber_pct    = 100 - bag_brix_pct - bagasse_moisture_pct
    bag_tpd          = cane_tpd * cane_fiber_pct / bag_fiber_pct

    # ── Mixed Juice ──────────────────────────────────────────────────────────
    mix_juice_tpd    = cane_tpd + imb_tpd - bag_tpd
    tons_pol_juice   = cane_tpd * cane_pol_pct / 100 - bag_tpd * bagasse_pol_pct / 100
    tons_brix_juice  = tons_pol_juice * 100 / mix_juice_purity
    mix_juice_brix   = tons_brix_juice / mix_juice_tpd * 100
    mix_juice_pol    = mix_juice_brix * mix_juice_purity / 100
    mix_juice_moist  = 100 - mix_juice_brix

    # ── Cane (back-calculated brix and moisture) ──────────────────────────────
    cane_brix_pct    = (tons_brix_juice + bag_tpd * bag_brix_pct / 100) / cane_tpd * 100
    cane_moist_pct   = 100 - cane_brix_pct - cane_fiber_pct

    # ── Mill extraction ───────────────────────────────────────────────────────
    mill_extraction_pct = tons_pol_juice / (cane_tpd * cane_pol_pct / 100) * 100

    # ── Per-mill bagasse and maceration balance ──────────────────────────────
    # Fiber is conserved through the mill train (no fiber in juice).
    tons_fiber = cane_tpd * cane_fiber_pct / 100

    # Fiber % profile: Mill 1 handles 50% of the total rise in one step;
    # the remaining (N-1) mills share the rest in equal increments.
    # Result: fiber_list[i] = fiber % in bagasse exiting Mill i+1 (0-indexed).
    fib_change     = bag_fiber_pct - cane_fiber_pct        # total rise, always positive
    mill_1_bag_fib = cane_fiber_pct + mill_1_fiber_rise_load_fraction * fib_change     # Mill 1 exit fiber %
    fib_step       = (bag_fiber_pct - mill_1_bag_fib) / max(number_of_mills - 1, 1)

    fiber_list = [mill_1_bag_fib]
    for i in range(number_of_mills - 1):
        fiber_list.append(fiber_list[i] + fib_step)

    # Bagasse TPD at each mill exit derived from fiber conservation.
    bag_flows = [tons_fiber / (fib / 100) for fib in fiber_list]

    # Juice flows:
    #   Mill 1 — direct balance (no maceration in)
    #   Mill 2 — remainder so that Mills 1+2 together deliver the full mix juice total
    #   Mills 3..N — derived from the counter-current maceration mass balance:
    #       juice_out[i] = juice_out[i-1] - bag_flows[i-2] + bag_flows[i-1]
    j1 = cane_tpd - bag_flows[0]
    j2 = mix_juice_tpd - j1
    juice_flows = [j1, j2]
    for i in range(number_of_mills - 2):
        juice_flows.append(juice_flows[i + 1] - bag_flows[i] + bag_flows[i + 1])

    # ── Per-mill summary dicts ────────────────────────────────────────────────
    # juice_flows[0..1] go to process; juice_flows[2..N-1] are maceration juice.
    mill_balances = []
    for idx in range(number_of_mills):
        mill_num  = idx + 1
        bag_in    = cane_tpd if idx == 0 else bag_flows[idx - 1]
        bag_out   = bag_flows[idx]
        juice_out = juice_flows[idx]

        if mill_num == 1:
            mac_in  = 0.0
            mac_src = "None"
        elif mill_num == number_of_mills:
            mac_in  = imb_tpd
            mac_src = "Imbibition"
        else:
            mac_in  = juice_flows[idx + 1]
            mac_src = f"Mill {mill_num + 1} maceration"

        dest = "To process" if mill_num <= 2 else f"Mill {mill_num - 1} maceration"

        mill_balances.append({
            "mill":            mill_num,
            "bagasse_in_tpd":  bag_in,
            "mac_in_tpd":      mac_in,
            "mac_in_source":   mac_src,
            "bagasse_out_tpd": bag_out,
            "juice_out_tpd":   juice_out,
            "juice_out_dest":  dest,
        })

    # ── Pack streams ─────────────────────────────────────────────────────────
    raw_streams = [
        ("Cane",        "In",  cane_tpd,      cane_brix_pct,  cane_pol_pct,    cane_fiber_pct, cane_moist_pct),
        ("Imbibition",  "In",  imb_tpd,       0.0,            0.0,             0.0,            100.0),
        ("Mixed Juice", "Out", mix_juice_tpd, mix_juice_brix, mix_juice_pol,   0.0,            mix_juice_moist),
        ("Bagasse",     "Out", bag_tpd,       bag_brix_pct,   bagasse_pol_pct, bag_fiber_pct,  bagasse_moisture_pct),
    ]

    streams = {}
    for name, direction, tpd, brix, pol, fiber, moist in raw_streams:
        streams[name] = {
            "direction":    direction,
            "tpd":          tpd,
            "tph":          tpd / 24,
            "lb_per_hr":    tpd / 24 * 2000,
            "brix_pct":     brix,
            "pol_pct":      pol,
            "fiber_pct":    fiber,
            "moisture_pct": moist,
            "tons_brix":    tpd * brix  / 100,
            "tons_pol":     tpd * pol   / 100,
            "tons_fiber":   tpd * fiber / 100,
            "tons_moisture":tpd * moist / 100,
            "pct_on_cane":  tpd / cane_tpd * 100,
        }

    # ── Balance check ─────────────────────────────────────────────────────────
    balance_keys = ("tpd", "tons_brix", "tons_pol", "tons_fiber", "tons_moisture")
    totals = {"in": {}, "out": {}, "difference": {}}
    for key in balance_keys:
        total_in  = sum(s[key] for s in streams.values() if s["direction"] == "In")
        total_out = sum(s[key] for s in streams.values() if s["direction"] == "Out")
        totals["in"][key]         = total_in
        totals["out"][key]        = total_out
        totals["difference"][key] = total_in - total_out

    return {
        "streams":              streams,
        "imbibition_gpm":       imb_gpm,
        "mill_extraction_pct":  mill_extraction_pct,
        "balance":              totals,
        "mill_balances":        mill_balances,
    }


def extract_key_outputs(result: dict) -> dict:
    """Pull the seven key values out of a mill_floor_material_balance result."""
    mj  = result["streams"]["Mixed Juice"]
    bag = result["streams"]["Bagasse"]
    return {
        "mixed_juice_lb_per_hr": mj["lb_per_hr"],
        "mixed_juice_brix":      mj["brix_pct"],
        "mixed_juice_purity":    mj["pol_pct"] / mj["brix_pct"] * 100,
        "mixed_juice_water":     mj["moisture_pct"],
        "bagasse_lb_per_hr":     bag["lb_per_hr"],
        "bagasse_fiber_pct":     bag["fiber_pct"],
        "bagasse_pol_pct":       bag["pol_pct"],
        "bagasse_purity":        bag["pol_pct"] / bag["brix_pct"] * 100,
        "bagasse_brix":          bag["brix_pct"],
        "bagasse_moisture":      bag["moisture_pct"]
    }


def display_mill_balance(result: dict) -> None:
    """Print a formatted summary of a mill_floor_material_balance result."""
    streams = result["streams"]

    col_w = [14, 6, 10, 10, 16, 8, 8, 8, 10, 10, 10, 10, 10]
    headers = [
        "Stream", "Dir", "TPD", "TPH", "lb/hr",
        "Brix%", "Pol%", "Fib%", "T-Brix", "T-Pol", "T-Fiber", "T-Moist", "%Cane",
    ]
    row_keys = [
        "direction", "tpd", "tph", "lb_per_hr",
        "brix_pct", "pol_pct", "fiber_pct",
        "tons_brix", "tons_pol", "tons_fiber", "tons_moisture", "pct_on_cane",
    ]

    def _fmt(v):
        if isinstance(v, str):
            return v
        return f"{v:,.2f}"

    sep = "  ".join("-" * w for w in col_w)
    header_row = "  ".join(h.ljust(w) for h, w in zip(headers, col_w))
    print("\nMill Floor Material Balance")
    print(sep)
    print(header_row)
    print(sep)
    for name, s in streams.items():
        vals = [name] + [s[k] for k in row_keys]
        print("  ".join(_fmt(v).ljust(w) for v, w in zip(vals, col_w)))
    print(sep)

    bal = result["balance"]
    for label, key in (("In", "in"), ("Out", "out"), ("Diff", "difference")):
        row = [label, "", f"{bal[key]['tpd']:,.2f}", "", "",
               "", "", "",
               f"{bal[key]['tons_brix']:,.3f}",
               f"{bal[key]['tons_pol']:,.3f}",
               f"{bal[key]['tons_fiber']:,.3f}",
               f"{bal[key]['tons_moisture']:,.3f}", ""]
        print("  ".join(v.ljust(w) for v, w in zip(row, col_w)))
    print(sep)

    print(f"\nMill Extraction (Pol% Pol in Cane): {result['mill_extraction_pct']:.2f}%")
    print(f"Imbibition: {result['imbibition_gpm']:,.1f} GPM")

    # ── Per-mill maceration table ─────────────────────────────────────────────
    print("\nPer-Mill Maceration Balance")
    mc_w   = [6, 16, 16, 22, 16, 26]
    mc_hdr = ["Mill", "Bagasse In\n(TPD)", "Liquid In\n(TPD)", "Liquid In Source",
              "Bagasse Out\n(TPD)", "Juice Out (TPD) / Destination"]
    mc_sep = "  ".join("-" * w for w in mc_w)
    print(mc_sep)
    print("  ".join(h.split("\n")[0].ljust(w) for h, w in zip(mc_hdr, mc_w)))
    print("  ".join((h.split("\n")[1] if "\n" in h else "").ljust(w) for h, w in zip(mc_hdr, mc_w)))
    print(mc_sep)
    for m in result["mill_balances"]:
        row = [
            str(m["mill"]),
            f"{m['bagasse_in_tpd']:,.1f}",
            f"{m['mac_in_tpd']:,.1f}",
            m["mac_in_source"],
            f"{m['bagasse_out_tpd']:,.1f}",
            f"{m['juice_out_tpd']:,.1f}  ->  {m['juice_out_dest']}",
        ]
        print("  ".join(v.ljust(w) for v, w in zip(row, mc_w)))
    print(mc_sep)


if __name__ == "__main__":
    result = mill_floor_material_balance(
        cane_tpd=17_000,
        cane_pol_pct=13.5,
        cane_fiber_pct=14.0,
        imbibition_pct_on_cane=25.0,
        bagasse_pol_pct=1.8,
        last_roll_purity=72.0,
        bagasse_moisture_pct=49.0,
        mix_juice_purity=88.0,
        number_of_mills=5,
        mill_1_fiber_rise_load_fraction=0.35,
    )
    display_mill_balance(result)
    print(extract_key_outputs(result))
