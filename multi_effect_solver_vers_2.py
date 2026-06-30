from time import time

from EvaporatorSet import EvaporatorSet
from SugarStream import SugarStream
from SteamStream import EvaporatorSteam


def solve_evaporator_sets(
    juice_brix: float,
    juice_purity: float,
    juice_flow_lb_per_hr: float,
    juice_temp_deg_F: float,
    set_configs: list,
    juice_pressure_psia: float = 40,
    juice_level_ft: float = 0,
    target_brix_out: float = 65,
    dessin_coefficient: float = 18000,
    liquid_level_ft: float = 2,
    n_iterations: int = 10,
    dampening: float = 0.1,
    verbose: bool = True,
) -> list:
    """
    Build multiple EvaporatorSet instances, distribute juice based on heating
    surface and delta-P weights, then balance juice flow across sets so all
    sets reach the same average U_calc/U_dessin ratio.

    Parameters
    ----------
    juice_brix : float
        Brix of clarified juice entering the evaporator station.
    juice_purity : float
        Purity of clarified juice (%).
    juice_flow_lb_per_hr : float
        Total clarified juice flow to the station (lb/hr).
    juice_temp_deg_F : float
        Temperature of clarified juice (°F).
    set_configs : list[dict]
        One dict per evaporator set.  Required keys:
            "effect_areas_ft2"  : list[float]  heating surface per effect (ft²)
            "supply_steam_psia" : float        supply steam pressure (psia)
            "last_effect_psia"  : float        last-effect vapor pressure (psia)
        Optional keys (fall back to the function-level defaults when omitted):
            "vapor_bleeds"       : list[float]  vapor bleed flows (lb/hr)
            "target_brix_out"    : float        target syrup brix for this set
            "dessin_coefficient" : float        design U (BTU/hr·ft²·°F)
            "liquid_level_ft"    : float        calandria liquid level (ft)
            "name"               : str          label used in printed output
    juice_pressure_psia : float
        Juice-side pressure (psia).  Default 40.
    juice_level_ft : float
        Juice level used for boiling-point-elevation head correction (ft).
        Default 0.
    target_brix_out : float
        Default target syrup brix applied to every set (overridden per set).
        Default 65.
    dessin_coefficient : float
        Default design U (BTU/hr·ft²·°F) applied to every set.  Default 18000.
    liquid_level_ft : float
        Default calandria liquid level (ft) applied to every set.  Default 2.
    n_iterations : int
        Number of U-ratio balancing iterations.  Default 10.
    dampening : float
        Exponent applied to each fraction update step.  Lower values produce
        smaller corrections per iteration (more stable, more iterations
        needed).  Default 0.1.
    verbose : bool
        Print iteration summaries and final results.  Default True.

    Returns
    -------
    list[EvaporatorSet]
        The solved set objects in the same order as set_configs.
        Call .show_summary() on any of them for detailed effect-by-effect output.

    Example
    -------
    >>> sets = solve_evaporator_sets(
    ...     juice_brix=14,
    ...     juice_purity=90,
    ...     juice_flow_lb_per_hr=1_500_000,
    ...     juice_temp_deg_F=220,
    ...     set_configs=[
    ...         {
    ...             "effect_areas_ft2": [25000, 25000, 25000, 25000],
    ...             "supply_steam_psia": 30,
    ...             "last_effect_psia": 2.4,
    ...             "vapor_bleeds": [100000, 50000],
    ...             "name": "Set 1 (4-eff 25k)",
    ...         },
    ...         {
    ...             "effect_areas_ft2": [12000, 12000, 12000, 12000],
    ...             "supply_steam_psia": 25,
    ...             "last_effect_psia": 2.4,
    ...             "vapor_bleeds": [50000, 20000],
    ...             "name": "Set 2 (4-eff 12k)",
    ...         },
    ...         {
    ...             "effect_areas_ft2": [11000, 9000, 9000],
    ...             "supply_steam_psia": 16,
    ...             "last_effect_psia": 2.4,
    ...             "name": "Set 3 (3-eff 11-9k)",
    ...         },
    ...     ],
    ... )
    """
    start = time()
    n_sets = len(set_configs)

    set_names = [
        cfg.get("name", f"Set {i + 1}") for i, cfg in enumerate(set_configs)
    ]

    # ── 1. Clarified juice feed stream ────────────────────────────────────
    clarified_juice = SugarStream(
        brix=juice_brix,
        purity=juice_purity,
        flow_lb_per_hr=juice_flow_lb_per_hr,
        temp_deg_F=juice_temp_deg_F,
        pressure_psia=juice_pressure_psia,
        level_ft=juice_level_ft,
    )

    # ── 2. Initial juice fractions: weight = (total HS / n_effects) * ΔP ─
    # Heavier weight → more heating surface per effect and/or larger ΔP
    # → that set can carry more juice load at startup.
    weights = []
    for cfg in set_configs:
        areas = cfg["effect_areas_ft2"]
        n_eff = len(areas)
        total_hs = sum(areas)
        dp = cfg["supply_steam_psia"] - cfg["last_effect_psia"]
        weights.append(total_hs * dp / n_eff)

    wt_sum = sum(weights)
    fracs = [w / wt_sum for w in weights]

    if verbose:
        header = "  ".join(f"{name}: {f:.4f}" for name, f in zip(set_names, fracs))
        print(f"\nStep 1 — Initial fractions (HS × ΔP / n_eff):\n  {header}")

    # ── 3. Build EvaporatorSet objects ────────────────────────────────────
    sets = []
    for i, cfg in enumerate(set_configs):
        n_eff = len(cfg["effect_areas_ft2"])
        juice_i = SugarStream.copy(
            clarified_juice,
            flow_lb_per_hr=fracs[i] * juice_flow_lb_per_hr,
        )
        evap_set = EvaporatorSet(
            juice_in=juice_i,
            supply_steam=EvaporatorSteam(cfg["supply_steam_psia"]),
            last_effect_pressure_psia=cfg["last_effect_psia"],
            target_brix_out=cfg.get("target_brix_out", target_brix_out),
            effect_areas_ft2=cfg["effect_areas_ft2"],
            vapor_bleeds=cfg.get("vapor_bleeds", [0] * (n_eff - 1)),
            dessin_coefficient=cfg.get("dessin_coefficient", dessin_coefficient),
            liquid_level_ft=cfg.get("liquid_level_ft", liquid_level_ft),
            name=cfg.get("name", f"Set {i + 1}"),
        )
        sets.append(evap_set)

    # ── 4. Refine fractions using built-set weights then initial solve ─────
    # EvaporatorSet.weight_for_init_distr already computes (HS/n_eff) × ΔP
    # using the actual supply steam pressure and last-effect pressure stored
    # on the object, so this step re-weights with the same formula but reads
    # directly from the constructed objects (catches any constructor overrides).
    set_weights = [s.weight_for_init_distr for s in sets]
    sw_sum = sum(set_weights)
    fracs = [w / sw_sum for w in set_weights]

    if verbose:
        header = "  ".join(f"{name}: {f:.4f}" for name, f in zip(set_names, fracs))
        print(f"\nStep 2 — Refined fractions (from built EvaporatorSet weights):\n  {header}")
        print()

    # Apply refined fractions and run initial pressure-profile solve on each set
    for i, evap in enumerate(sets):
        evap.juice_in.flow_lb_per_hr = fracs[i] * juice_flow_lb_per_hr
        evap.adjust_pressure_profile()
        if verbose:
            print(f"── Initial solve: {set_names[i]} ──")
            evap.show_summary()
            print()

    # ── 5. U-ratio balancing loop ──────────────────────────────────────────
    # Under-loaded sets (low U ratio relative to the average) receive more
    # juice; over-loaded sets give juice away.  The dampening exponent keeps
    # corrections small to avoid oscillation.
    if verbose:
        print(f"\n{'='*60}")
        print(f"  U-ratio balancing loop  ({n_iterations} iterations, dampening={dampening})")
        print(f"{'='*60}")

    for iteration in range(n_iterations):
        u_vals = [s.U_ratio_avg for s in sets]
        u_avg = sum(u_vals) / n_sets

        # Update all-but-last fractions; last set gets the remainder
        new_fracs = []
        for i in range(n_sets - 1):
            ratio = u_avg / u_vals[i] if u_vals[i] != 0 else 1.0
            new_fracs.append(fracs[i] * (ratio ** dampening))
        new_fracs.append(max(0.0, 1.0 - sum(new_fracs)))
        fracs = new_fracs

        for i, evap in enumerate(sets):
            evap.juice_in.flow_lb_per_hr = fracs[i] * juice_flow_lb_per_hr
            evap.adjust_pressure_profile()

        if verbose:
            u_str = "  ".join(f"{name}:{u:.4f}" for name, u in zip(set_names, u_vals))
            f_str = "  ".join(f"{name}:{f:.4f}" for name, f in zip(set_names, fracs))
            print(f"  Iter {iteration + 1:>3}  U_avg={u_avg:.4f}  U=[{u_str}]  fracs=[{f_str}]")

    # ── 6. Final summary ──────────────────────────────────────────────────
    elapsed = (time() - start) * 1000
    print(f"\n{'='*60}")
    print(f"  EVAPORATION RESULTS   ({elapsed:.1f} ms total)")
    print(f"{'='*60}")
    for i, evap in enumerate(sets):
        flow = fracs[i] * juice_flow_lb_per_hr
        print(f"\n{set_names[i]}  —  {fracs[i]*100:.2f}% of juice  ({flow:,.0f} lb/hr)")
        print(25 * '-')
        evap.show_summary()
    print(f"{'='*100}")
    print(f"\n")
    return sets


# ---------------------------------------------------------------------------
# Example run — edit numbers below and run:  python multi_effect_solver_vers_2.py
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    start_time = time() * 1000
    solved_sets = solve_evaporator_sets(
        # ── Clarified juice feed ───────────────────────────────────────────
        juice_brix=14,
        juice_purity=90,
        juice_flow_lb_per_hr=1_500_000,
        juice_temp_deg_F=220,
        juice_pressure_psia=40,

        # ── Global defaults (override per set in set_configs if needed) ────
        target_brix_out=65,
        dessin_coefficient=18000,
        liquid_level_ft=2,

        # ── Iteration control ──────────────────────────────────────────────
        n_iterations=10,
        dampening=0.2,

        # ── Set configurations ─────────────────────────────────────────────
        # Each dict needs: effect_areas_ft2, supply_steam_psia, last_effect_psia
        # Optional per-set overrides: vapor_bleeds, target_brix_out,
        #                             dessin_coefficient, liquid_level_ft, name
        set_configs=[
            {
                "name": "Set 1 (4-eff 25k ft²)",
                "effect_areas_ft2": [25000, 25000, 25000, 25000],
                "supply_steam_psia": 30,
                "last_effect_psia": 2.4,
                "vapor_bleeds": [100000, 50000, 50000],
            },
            {
                "name": "Set 2 (4-eff 12k ft²)",
                "effect_areas_ft2": [12000, 12000, 12000, 12000],
                "supply_steam_psia": 25,
                "last_effect_psia": 2.4,
                "vapor_bleeds": [50000, 20000],
            },
            {
                "name": "Set 3 (3-eff 11-9k ft²)",
                "effect_areas_ft2": [11000, 9000, 9000],
                "supply_steam_psia": 16,
                "last_effect_psia": 2.4,
                "vapor_bleeds": [50000]
            },
        ],
    )

    end_time = time() * 1000
    solve_time = end_time - start_time
    print(f"\n Time to solve {solve_time:.0f} ms")
