#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Three boiling sugar balance."""


# ── private helpers ──────────────────────────────────────────────────────────

def _sjm(J, S, M):
    return S * (J - M) / (J * (S - M))

def _from_low(J, S, M, M_sol):
    """Cobenze: given low-side solids, return (high_sol, feed_sol)."""
    S_sol = M_sol * (J - M) / (S - J)
    J_sol = M_sol * (S - M) / (S - J)
    return S_sol, J_sol

def _split(J, S, M, J_sol):
    """Cobenze: split feed solids into (high_sol, low_sol)."""
    S_sol = J_sol * (J - M) / (S - M)
    M_sol = J_sol * (S - J) / (S - M)
    return S_sol, M_sol

def _lbs(sol, brix):
    return sol * 100.0 / brix


# ── main function ────────────────────────────────────────────────────────────

def three_boiling(
    syrup_brix        = 60.00,
    syrup_purity      = 80.00,
    sugar_purity      = 98.00,   # combined A+B sugar purity for SJM
    a_massc_brix      = 92.00,   # A massecuite purity is calculated, not input
    b_massc_brix      = 94.00,
    b_massc_purity    = 72.00,
    c_massc_brix      = 97.00,
    c_massc_purity    = 57.50,
    grain_brix        = 88.00,
    grain_purity      = 70.00,
    c_sugar_brix      = 88.00,   # C sugar remelted = magma
    c_sugar_purity    = 84.00,
    a_sugar_brix      = 99.60,   # A sugar purity is derived from the balance
    b_sugar_brix      = 99.60,
    b_sugar_purity    = 98.00,
    a_molass_brix     = 65.00,
    a_molass_purity   = 61.57,
    b_molass_brix     = 65.00,
    b_molass_purity   = 52.00,
    fin_molass_brix   = 80.00,
    fin_molass_purity = 30.00,
    total_syrup_solids = 100_000.0,
    pan_factor_a      = 1.15,
    pan_factor_b      = 1.15,
    pan_factor_c      = 1.25,
    pan_factor_grain  = 1.25,
    print_report      = True,
):
    """
    Three-boiling material and energy balance.

    All purity values:  purity = pol / brix * 100  (%)
    All brix values:    % dissolved solids (°Brix)
    Solids / pol units: lb (same basis as total_syrup_solids)

    Returns a dict with keys for every computed stream and energy figure.
    Each stream sub-dict has keys: pol, brix, material, purity, brix_pct.
    """

    def stream(pol, sol, brix_pct):
        return dict(pol=pol, brix=sol, material=_lbs(sol, brix_pct),
                    purity=pol/sol*100, brix_pct=brix_pct)

    # Step 1 — SJM: pol split
    total_pol      = total_syrup_solids * syrup_purity / 100
    frac_sugar     = _sjm(syrup_purity, sugar_purity, fin_molass_purity)
    pol_sugar      = total_pol * frac_sugar
    pol_fin        = total_pol - pol_sugar

    # Step 2 — final molasses
    fin_sol = pol_fin / (fin_molass_purity / 100)
    fin_molasses = stream(pol_fin, fin_sol, fin_molass_brix)

    # Step 3 — C massecuite & C sugar from final molasses
    c_sug_sol, c_mas_sol = _from_low(c_massc_purity, c_sugar_purity, fin_molass_purity, fin_sol)
    c_sugar     = stream(c_sug_sol * c_sugar_purity / 100, c_sug_sol, c_sugar_brix)
    c_massecuite = stream(c_mas_sol * c_massc_purity / 100, c_mas_sol, c_massc_brix)

    # Step 4 — grain & B molasses from C massecuite feed
    gr_sol, b_mol_sol = _split(c_massc_purity, grain_purity, b_molass_purity, c_mas_sol)
    grain      = stream(gr_sol   * grain_purity   / 100, gr_sol,    grain_brix)
    b_molasses = stream(b_mol_sol * b_molass_purity / 100, b_mol_sol, b_molass_brix)

    # Step 5 — syrup & A molasses to grain strike
    syr_gr, amol_gr = _split(grain_purity, syrup_purity, a_molass_purity, gr_sol)
    syrup_to_grain    = stream(syr_gr  * syrup_purity   / 100, syr_gr,  syrup_brix)
    a_molass_to_grain = stream(amol_gr * a_molass_purity / 100, amol_gr, a_molass_brix)

    # Step 6 — B massecuite & B sugar from B molasses
    b_sug_sol, b_mas_sol = _from_low(b_massc_purity, b_sugar_purity, b_molass_purity, b_mol_sol)
    b_sugar     = stream(b_sug_sol * b_sugar_purity / 100, b_sug_sol, b_sugar_brix)
    b_massecuite = stream(b_mas_sol * b_massc_purity / 100, b_mas_sol, b_massc_brix)

    # Step 7 — A sugar by subtraction
    a_sug_sol = (total_syrup_solids - fin_sol) - b_sug_sol
    a_sug_pol = pol_sugar - b_sugar['pol']
    a_sugar = dict(pol=a_sug_pol, brix=a_sug_sol,
                   material=_lbs(a_sug_sol, a_sugar_brix),
                   purity=a_sug_pol/a_sug_sol*100, brix_pct=a_sugar_brix)

    # Step 8 — magma split proportional to A : B sugar
    frac_a = a_sug_sol / (a_sug_sol + b_sug_sol)
    frac_b = 1.0 - frac_a
    magma_to_a = stream(c_sugar['pol']*frac_a, c_sug_sol*frac_a, c_sugar_brix)
    magma_to_b = stream(c_sugar['pol']*frac_b, c_sug_sol*frac_b, c_sugar_brix)

    # Step 9 — syrup & A molasses to B strike
    syr_amol_b_sol = b_mas_sol - magma_to_b['brix']
    syr_amol_b_pol = b_massecuite['pol'] - magma_to_b['pol']
    avg_pur_b      = syr_amol_b_pol / syr_amol_b_sol * 100
    syr_b, amol_b  = _split(avg_pur_b, syrup_purity, a_molass_purity, syr_amol_b_sol)
    syrup_to_b    = stream(syr_b  * syrup_purity   / 100, syr_b,  syrup_brix)
    a_molass_to_b = stream(amol_b * a_molass_purity / 100, amol_b, a_molass_brix)

    # Step 10 — total A molasses
    amol_tot_sol = amol_b + amol_gr
    amol_tot_pol = a_molass_to_b['pol'] + a_molass_to_grain['pol']
    a_molasses = dict(pol=amol_tot_pol, brix=amol_tot_sol,
                      material=a_molass_to_b['material'] + a_molass_to_grain['material'],
                      purity=amol_tot_pol/amol_tot_sol*100, brix_pct=a_molass_brix)

    # Step 11 — A massecuite
    a_mas_sol = a_sug_sol + amol_tot_sol
    a_mas_pol = a_sug_pol + amol_tot_pol
    a_massecuite = dict(pol=a_mas_pol, brix=a_mas_sol,
                        material=_lbs(a_mas_sol, a_massc_brix),
                        purity=a_mas_pol/a_mas_sol*100, brix_pct=a_massc_brix)

    # Step 12 — syrup to A strike
    syr_a_sol = total_syrup_solids - syr_b - syr_gr
    syrup_to_a = stream(syr_a_sol * syrup_purity / 100, syr_a_sol, syrup_brix)

    # Strike feeds
    def add_streams(*streams_list):
        pol = sum(s['pol']      for s in streams_list)
        sol = sum(s['brix']     for s in streams_list)
        mat = sum(s['material'] for s in streams_list)
        return dict(pol=pol, brix=sol, material=mat,
                    purity=pol/sol*100, brix_pct=sol/mat*100)

    a_feed    = add_streams(syrup_to_a, magma_to_a)
    b_feed    = add_streams(syrup_to_b, a_molass_to_b, magma_to_b)
    c_feed    = add_streams(grain, b_molasses)
    grain_feed = add_streams(syrup_to_grain, a_molass_to_grain)

    # Steps 14–15 — evaporation & exhaust
    evap_a     = a_feed['material']     - a_massecuite['material']
    evap_b     = b_feed['material']     - b_massecuite['material']
    evap_c     = c_feed['material']     - c_massecuite['material']
    evap_grain = grain_feed['material'] - grain['material']
    total_evap = evap_a + evap_b + evap_c + evap_grain

    exhaust_a     = evap_a     * pan_factor_a
    exhaust_b     = evap_b     * pan_factor_b
    exhaust_c     = evap_c     * pan_factor_c
    exhaust_grain = evap_grain * pan_factor_grain
    total_exhaust = exhaust_a + exhaust_b + exhaust_c + exhaust_grain

    results = dict(
        # streams
        a_sugar=a_sugar,        b_sugar=b_sugar,        c_sugar=c_sugar,
        fin_molasses=fin_molasses,
        a_massecuite=a_massecuite, b_massecuite=b_massecuite, c_massecuite=c_massecuite,
        grain=grain,
        a_molasses=a_molasses,  b_molasses=b_molasses,
        magma_to_a=magma_to_a, magma_to_b=magma_to_b,
        syrup_to_a=syrup_to_a, syrup_to_b=syrup_to_b, syrup_to_grain=syrup_to_grain,
        a_molass_to_b=a_molass_to_b, a_molass_to_grain=a_molass_to_grain,
        a_strike_feed=a_feed, b_strike_feed=b_feed,
        c_strike_feed=c_feed, grain_strike_feed=grain_feed,
        # evaporation
        evap_a=evap_a, evap_b=evap_b, evap_c=evap_c, evap_grain=evap_grain,
        total_evap=total_evap,
        # exhaust
        exhaust_a=exhaust_a, exhaust_b=exhaust_b,
        exhaust_c=exhaust_c, exhaust_grain=exhaust_grain,
        total_exhaust=total_exhaust,
    )

    if print_report:
        _print_report(results, total_syrup_solids, total_pol,
                      pan_factor_a, pan_factor_b, pan_factor_c, pan_factor_grain)

    return results


# ── report ───────────────────────────────────────────────────────────────────

def _print_report(r, total_syrup_solids, total_pol,
                  pf_a, pf_b, pf_c, pf_grain):
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        try: sys.stdout.reconfigure(encoding='utf-8')
        except Exception: pass

    SEP = "=" * 72

    def row(name, s, evap=None):
        if evap is not None:
            print(f"  {'  Evaporation':<30} {'':>9} {'':>9} {evap:>12,.0f}        —       —")
            return
        pur  = f"{s['purity']:.2f}"  if s['purity']   else "    —"
        bpct = f"{s['brix_pct']:.2f}" if s['brix_pct'] else "    —"
        print(f"  {name:<30} {s['pol']:>9,.0f} {s['brix']:>9,.0f}"
              f" {s['material']:>12,.0f} {pur:>8} {bpct:>7}")

    print(SEP)
    print(f"  THREE BOILING SYSTEM  —  Basis: {total_syrup_solids:,.0f} lb Syrup Solids")
    print(SEP)
    print(f"  {'Stream':<30} {'Pol lb':>9} {'Brix lb':>9} {'Material lb':>12} {'Purity':>8} {'Brix':>7}")
    print(SEP)

    print("\n  \"A\" Strike")
    row("    Magma",          r['magma_to_a'])
    row("    Syrup",          r['syrup_to_a'])
    row("    Total",          r['a_strike_feed'])
    row(None, None,           evap=r['evap_a'])
    row("    A Massecuite",   r['a_massecuite'])
    row("    A Sugar",        r['a_sugar'])
    row("    A Molasses",     r['a_molasses'])

    print("\n  \"B\" Strike")
    row("    Magma",          r['magma_to_b'])
    row("    Syrup",          r['syrup_to_b'])
    row("    A Molasses",     r['a_molass_to_b'])
    row("    Total",          r['b_strike_feed'])
    row(None, None,           evap=r['evap_b'])
    row("    B Massecuite",   r['b_massecuite'])
    row("    B Sugar",        r['b_sugar'])
    row("    B Molasses",     r['b_molasses'])

    print("\n  \"C\" Strike")
    row("    Grain",          r['grain'])
    row("    B Molasses",     r['b_molasses'])
    row("    Total",          r['c_strike_feed'])
    row(None, None,           evap=r['evap_c'])
    row("    C Massecuite",   r['c_massecuite'])
    row("    C Sugar / Magma",r['c_sugar'])
    row("    Final Molasses", r['fin_molasses'])

    print("\n  Grain Strike")
    row("    Syrup",          r['syrup_to_grain'])
    row("    A Molasses",     r['a_molass_to_grain'])
    row("    Total",          r['grain_strike_feed'])
    row(None, None,           evap=r['evap_grain'])
    row("    Grain",          r['grain'])

    print(f"\n{SEP}")
    print("  EXHAUST / VAPOR REQUIRED FOR SUGAR BOILING")
    print(f"  {'Strike':<12} {'Evaporation':>14} {'Pan Factor':>12} {'Exhaust':>14}")
    print(f"  {'-'*54}")
    for label, evap, pf, exh in [
        ("A",     r['evap_a'],     pf_a,     r['exhaust_a']),
        ("B",     r['evap_b'],     pf_b,     r['exhaust_b']),
        ("C",     r['evap_c'],     pf_c,     r['exhaust_c']),
        ("Grain", r['evap_grain'], pf_grain, r['exhaust_grain']),
    ]:
        print(f"  {label:<12} {evap:>14,.0f} {pf:>12.2f} {exh:>14,.0f}")
    print(f"  {'-'*54}")
    print(f"  {'Total':<12} {r['total_evap']:>14,.0f} {'':>12} {r['total_exhaust']:>14,.0f}")

    # closure
    pol_out = r['a_sugar']['pol'] + r['b_sugar']['pol'] + r['fin_molasses']['pol']
    sol_out = r['a_sugar']['brix'] + r['b_sugar']['brix'] + r['fin_molasses']['brix']
    syr_all = r['syrup_to_a']['brix'] + r['syrup_to_b']['brix'] + r['syrup_to_grain']['brix']
    cy_a = r['a_sugar']['material'] / r['a_massecuite']['material'] * 100
    cy_b = r['b_sugar']['material'] / r['b_massecuite']['material'] * 100
    cy_c = r['c_sugar']['material'] / r['c_massecuite']['material'] * 100

    print(f"\n{SEP}")
    print("  BALANCE CLOSURE")
    print(SEP)
    print(f"  Pol  in {total_pol:>10,.0f} lb    Pol  out {pol_out:>10,.0f} lb    error {total_pol-pol_out:>+.1f} lb")
    print(f"  Brix in {total_syrup_solids:>10,.0f} lb    Brix out {sol_out:>10,.0f} lb    error {total_syrup_solids-sol_out:>+.1f} lb")
    print(f"  Syrup to A+B+Grain {syr_all:>10,.0f} lb    error {total_syrup_solids-syr_all:>+.1f} lb")
    print(f"\n  Crystal Yields (sugar / massecuite, material basis)")
    print(f"  A: {cy_a:.1f}%     B: {cy_b:.1f}%     C: {cy_c:.1f}%")
    print(SEP)


# ── run standalone ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    three_boiling()
