from SugarStream import SugarStream
from Pan import Pan
from Centrifugal import Centrifugal


def display_balance(
    syrup: SugarStream,
    A_centrifugals: Centrifugal,
    B_centrifugals: Centrifugal,
    C_machines: Centrifugal,
    A_pans: Pan = None,
    B_pans: Pan = None,
    grain_pans: Pan = None,
    C_pans: Pan = None,
):
    """
    Pretty balance display for a three-boiling sugar house.

    System boundary:
        IN  — syrup (original, pre-remelt), wash water from each centrifugal
        OUT — A sugar, B sugar, C sugar, C final molasses, pan evaporation

    POL and solids balances close on this boundary.
    """

    W = 63

    def hdr(title):
        print(f"\n  {'─' * (W - 4)}")
        print(f"  {title}")
        print(f"  {'─' * (W - 4)}")

    def row(label, flow, brix, purity, pol, indent="  "):
        print(
            f"{indent}{label:<22}"
            f"  {flow:>10,.0f} lb/hr"
            f"  {brix:>5.1f}°Bx"
            f"  {purity:>5.1f}% P"
            f"  {pol:>10,.0f} lb/hr pol"
        )

    def chk(label, val_in, val_out):
        diff = val_out - val_in
        pct  = diff / val_in * 100 if val_in else 0
        flag = "  OK" if abs(pct) < 0.1 else "  *** CHECK"
        print(f"  {label:<18}  IN: {val_in:>12,.1f}   OUT: {val_out:>12,.1f}"
              f"   Δ: {diff:>+10,.1f} ({pct:+.3f}%){flag}")

    # ── Derived quantities ──────────────────────────────────────────────
    a_sugar_pol   = A_centrifugals.pol_to_sugar_lb_hr
    b_sugar_pol   = B_centrifugals.pol_to_sugar_lb_hr
    c_sugar_pol   = C_machines.pol_to_sugar_lb_hr
    fin_mol_pol   = C_machines.pol_to_molasses_lb_hr

    a_sugar_solids = A_centrifugals.crystals_to_sugar_lb_hr
    b_sugar_solids = B_centrifugals.crystals_to_sugar_lb_hr
    c_sugar_solids = C_machines.crystals_to_sugar_lb_hr
    fin_mol_solids = C_machines.molasses_solids_lb_hr

    total_sugar_flow   = (A_centrifugals.sugar_wet_lb_hr
                        + B_centrifugals.sugar_wet_lb_hr
                        + C_machines.sugar_wet_lb_hr)
    total_sugar_solids = a_sugar_solids + b_sugar_solids + c_sugar_solids
    total_sugar_pol    = a_sugar_pol + b_sugar_pol + c_sugar_pol

    wash_total = (A_centrifugals.wash_water_lb_hr
                + B_centrifugals.wash_water_lb_hr
                + C_machines.wash_water_lb_hr)

    # ── Header ──────────────────────────────────────────────────────────
    print(f"\n{'═' * W}")
    print(f"  THREE-BOILING HOUSE  —  MATERIAL BALANCE")
    print(f"{'═' * W}")

    # ── Feed ────────────────────────────────────────────────────────────
    hdr("FEED")
    print(f"  {'Stream':<22}  {'Flow':>14}  {'Brix':>7}  {'Purity':>8}  {'POL lb/hr':>14}")
    print(f"  {'─'*22}  {'─'*14}  {'─'*7}  {'─'*8}  {'─'*14}")
    row("Syrup",      syrup.flow_lb_per_hr, syrup.brix, syrup.purity, syrup.pol_flow)
    row("Wash water", wash_total,           0,          0,             0)
    print(f"  {'─'*22}  {'─'*14}  {'─'*7}  {'─'*8}  {'─'*14}")
    row("Total in",   syrup.flow_lb_per_hr + wash_total, syrup.brix, syrup.purity, syrup.pol_flow)

    # ── Sugar products ───────────────────────────────────────────────────
    hdr("SUGAR PRODUCTS")
    print(f"  {'Stream':<22}  {'Flow':>14}  {'Brix':>7}  {'Purity':>8}  {'POL lb/hr':>14}")
    print(f"  {'─'*22}  {'─'*14}  {'─'*7}  {'─'*8}  {'─'*14}")
    row("A Sugar",    A_centrifugals.sugar_wet_lb_hr, A_centrifugals.sugar_brix, A_centrifugals.sugar_purity, a_sugar_pol)
    row("B Sugar",    B_centrifugals.sugar_wet_lb_hr, B_centrifugals.sugar_brix, B_centrifugals.sugar_purity, b_sugar_pol)
    row("C Sugar",    C_machines.sugar_wet_lb_hr,     C_machines.sugar_brix,     C_machines.sugar_purity,     c_sugar_pol)
    print(f"  {'─'*22}  {'─'*14}  {'─'*7}  {'─'*8}  {'─'*14}")
    avg_purity = total_sugar_pol / total_sugar_solids * 100 if total_sugar_solids else 0
    avg_brix   = total_sugar_solids / total_sugar_flow * 100 if total_sugar_flow else 0
    row("Total sugar", total_sugar_flow, avg_brix, avg_purity, total_sugar_pol)

    # ── Final molasses ───────────────────────────────────────────────────
    hdr("FINAL MOLASSES  (C Machines outlet)")
    print(f"  {'Stream':<22}  {'Flow':>14}  {'Brix':>7}  {'Purity':>8}  {'POL lb/hr':>14}")
    print(f"  {'─'*22}  {'─'*14}  {'─'*7}  {'─'*8}  {'─'*14}")
    row("Final molasses", C_machines.molasses_flow_lb_hr, C_machines.molasses_brix, C_machines.molasses_purity, fin_mol_pol)

    # ── Pol recovery ─────────────────────────────────────────────────────
    hdr("POL RECOVERY")
    pol_in    = syrup.pol_flow
    sugar_rec = total_sugar_pol / pol_in * 100 if pol_in else 0
    mol_loss  = fin_mol_pol     / pol_in * 100 if pol_in else 0
    print(f"  POL in (syrup)       : {pol_in:>12,.1f} lb/hr")
    print(f"  POL to sugar         : {total_sugar_pol:>12,.1f} lb/hr  ({sugar_rec:.2f}%)")
    print(f"  POL to final molasses: {fin_mol_pol:>12,.1f} lb/hr  ({mol_loss:.2f}%)")

    # ── Steam consumption ────────────────────────────────────────────────
    if any(p is not None for p in [A_pans, B_pans, grain_pans, C_pans]):
        hdr("STEAM CONSUMPTION")
        print(f"  {'Pan':<22}  {'Steam lb/hr':>14}  {'Steam type':>12}  {'lb steam/lb H₂O':>16}")
        print(f"  {'─'*22}  {'─'*14}  {'─'*12}  {'─'*16}")
        total_steam = 0
        for pan, label in [(A_pans, "A Pans"), (B_pans, "B Pans"),
                           (grain_pans, "Grain Pans"), (C_pans, "C Pans")]:
            if pan is not None:
                total_steam += pan.steam_flow_lb_hr
                print(f"  {label:<22}  {pan.steam_flow_lb_hr:>14,.0f}"
                      f"  {pan.steam_type:>12}  {pan.steam_to_evaporation_ratio:>16.3f}")
        print(f"  {'─'*22}  {'─'*14}  {'─'*12}  {'─'*16}")
        print(f"  {'Total steam':<22}  {total_steam:>14,.0f}")

    # ── Balance closure ──────────────────────────────────────────────────
    hdr("BALANCE CLOSURE")
    pol_out    = total_sugar_pol + fin_mol_pol
    solids_in  = syrup.solids_flow
    solids_out = total_sugar_solids + fin_mol_solids
    chk("POL (lb/hr)",    syrup.pol_flow, pol_out)
    chk("Solids (lb/hr)", solids_in,      solids_out)

    print(f"\n{'═' * W}\n")


if __name__ == "__main__":
    from three_boiling_OOP import (
        syrup, A_centrifugals, B_centrifugals, C_machines,
        A_pans, B_pans, grain_pans, C_pans
    )
    display_balance(
        syrup=syrup,
        A_centrifugals=A_centrifugals,
        B_centrifugals=B_centrifugals,
        C_machines=C_machines,
        A_pans=A_pans,
        B_pans=B_pans,
        grain_pans=grain_pans,
        C_pans=C_pans,
    )
