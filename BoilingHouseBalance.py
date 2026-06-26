from SugarStream import SugarStream
from Pan import Pan
from Centrifugal import Centrifugal


class BoilingHouseBalance:
    """
    Material balance summary for a three-boiling sugar house.

    Aggregates pre-built centrifugal and pan objects into a single balance
    report. All derived quantities are computed in __init__ and stored as
    attributes for direct access.

    System boundary
    ---------------
    IN  — syrup (pre-remelt), wash water from each centrifugal stage.
    OUT — A sugar, B sugar, C sugar, final molasses, pan evaporation.

    Parameters
    ----------
    syrup           : SugarStream — clarified/evaporated syrup entering the boiling house.
    A_centrifugals  : Centrifugal — A-product centrifugal machines.
    B_centrifugals  : Centrifugal — B-product centrifugal machines.
    C_machines      : Centrifugal — C-product centrifugal machines (final molasses outlet).
    A_pans          : Pan — A-massecuite vacuum pans [optional].
    B_pans          : Pan — B-massecuite vacuum pans [optional].
    grain_pans      : Pan — grain/seed pans [optional].
    C_pans          : Pan — C-massecuite vacuum pans [optional].
    name            : Display name for the unit [default 'Three-Boiling House'].

    Key outputs
    -----------
    total_sugar_flow_lb_hr  : Combined wet sugar output (lb/hr).
    pol_recovery_pct        : POL recovered to sugar as % of syrup POL.
    molasses_loss_pct       : POL lost to final molasses as % of syrup POL.
    total_steam_lb_hr       : Total pan steam consumption (lb/hr); 0 if no pans provided.
    """

    def __init__(
        self,
        syrup: SugarStream,
        A_centrifugals: Centrifugal,
        B_centrifugals: Centrifugal,
        C_machines: Centrifugal,
        A_pans: Pan = None,
        B_pans: Pan = None,
        grain_pans: Pan = None,
        C_pans: Pan = None,
        name: str = 'Three-Boiling House',
    ):
        self.name           = name
        self.syrup          = syrup
        self.A_centrifugals = A_centrifugals
        self.B_centrifugals = B_centrifugals
        self.C_machines     = C_machines
        self.A_pans         = A_pans
        self.B_pans         = B_pans
        self.grain_pans     = grain_pans
        self.C_pans         = C_pans

        # ── Sugar pol and solids (lb/hr) ──────────────────────────────────────
        self.a_sugar_pol    = A_centrifugals.pol_to_sugar_lb_hr
        self.b_sugar_pol    = B_centrifugals.pol_to_sugar_lb_hr
        self.c_sugar_pol    = C_machines.pol_to_sugar_lb_hr
        self.fin_mol_pol    = C_machines.pol_to_molasses_lb_hr

        self.a_sugar_solids = A_centrifugals.crystals_to_sugar_lb_hr
        self.b_sugar_solids = B_centrifugals.crystals_to_sugar_lb_hr
        self.c_sugar_solids = C_machines.crystals_to_sugar_lb_hr
        self.fin_mol_solids = C_machines.molasses_solids_lb_hr

        # ── Totals ────────────────────────────────────────────────────────────
        self.total_sugar_flow_lb_hr = (
            A_centrifugals.sugar_wet_lb_hr
            + B_centrifugals.sugar_wet_lb_hr
            + C_machines.sugar_wet_lb_hr
        )
        self.total_sugar_solids = (
            self.a_sugar_solids + self.b_sugar_solids + self.c_sugar_solids
        )
        self.total_sugar_pol = (
            self.a_sugar_pol + self.b_sugar_pol + self.c_sugar_pol
        )
        self.wash_total = (
            A_centrifugals.wash_water_lb_hr
            + B_centrifugals.wash_water_lb_hr
            + C_machines.wash_water_lb_hr
        )

        # ── Pol recovery ──────────────────────────────────────────────────────
        pol_in = syrup.pol_flow
        self.pol_recovery_pct  = self.total_sugar_pol / pol_in * 100 if pol_in else 0
        self.molasses_loss_pct = self.fin_mol_pol      / pol_in * 100 if pol_in else 0

        # ── Steam ─────────────────────────────────────────────────────────────
        self.total_steam_lb_hr = sum(
            p.steam_flow_lb_hr for p in [A_pans, B_pans, grain_pans, C_pans]
            if p is not None
        )

    # ── Balance ───────────────────────────────────────────────────────────────

    @property
    def balance_check(self):
        pol_out    = self.total_sugar_pol + self.fin_mol_pol
        solids_out = self.total_sugar_solids + self.fin_mol_solids
        return {
            'pol': {
                'in_lb_hr':   self.syrup.pol_flow,
                'out_lb_hr':  pol_out,
                'diff_lb_hr': self.syrup.pol_flow - pol_out,
            },
            'solids': {
                'in_lb_hr':   self.syrup.solids_flow,
                'out_lb_hr':  solids_out,
                'diff_lb_hr': self.syrup.solids_flow - solids_out,
            },
        }

    # ── Display ───────────────────────────────────────────────────────────────

    def __repr__(self):
        return (
            f"BoilingHouseBalance(syrup={self.syrup.flow_lb_per_hr:,.0f} lb/hr, "
            f"pol_recovery={self.pol_recovery_pct:.2f}%, "
            f"sugar={self.total_sugar_flow_lb_hr:,.0f} lb/hr)"
        )

    def neat_display(self):
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

        syrup = self.syrup
        A, B, C = self.A_centrifugals, self.B_centrifugals, self.C_machines

        print(f"\n{'═' * W}")
        print(f"  {self.name}  —  MATERIAL BALANCE")
        print(f"{'═' * W}")

        # ── Feed ──────────────────────────────────────────────────────────────
        hdr("FEED")
        print(f"  {'Stream':<22}  {'Flow':>14}  {'Brix':>7}  {'Purity':>8}  {'POL lb/hr':>14}")
        print(f"  {'─'*22}  {'─'*14}  {'─'*7}  {'─'*8}  {'─'*14}")
        row("Syrup",      syrup.flow_lb_per_hr,                   syrup.brix, syrup.purity, syrup.pol_flow)
        row("Wash water", self.wash_total,                         0,          0,            0)
        print(f"  {'─'*22}  {'─'*14}  {'─'*7}  {'─'*8}  {'─'*14}")
        row("Total in",   syrup.flow_lb_per_hr + self.wash_total,  syrup.brix, syrup.purity, syrup.pol_flow)

        # ── Sugar products ─────────────────────────────────────────────────────
        hdr("SUGAR PRODUCTS")
        print(f"  {'Stream':<22}  {'Flow':>14}  {'Brix':>7}  {'Purity':>8}  {'POL lb/hr':>14}")
        print(f"  {'─'*22}  {'─'*14}  {'─'*7}  {'─'*8}  {'─'*14}")
        row("A Sugar", A.sugar_wet_lb_hr, A.sugar_brix, A.sugar_purity, self.a_sugar_pol)
        row("B Sugar", B.sugar_wet_lb_hr, B.sugar_brix, B.sugar_purity, self.b_sugar_pol)
        row("C Sugar", C.sugar_wet_lb_hr, C.sugar_brix, C.sugar_purity, self.c_sugar_pol)
        print(f"  {'─'*22}  {'─'*14}  {'─'*7}  {'─'*8}  {'─'*14}")
        avg_purity = self.total_sugar_pol    / self.total_sugar_solids * 100 if self.total_sugar_solids else 0
        avg_brix   = self.total_sugar_solids / self.total_sugar_flow_lb_hr   * 100 if self.total_sugar_flow_lb_hr else 0
        row("Total sugar", self.total_sugar_flow_lb_hr, avg_brix, avg_purity, self.total_sugar_pol)

        # ── Final molasses ─────────────────────────────────────────────────────
        hdr("FINAL MOLASSES  (C Machines outlet)")
        print(f"  {'Stream':<22}  {'Flow':>14}  {'Brix':>7}  {'Purity':>8}  {'POL lb/hr':>14}")
        print(f"  {'─'*22}  {'─'*14}  {'─'*7}  {'─'*8}  {'─'*14}")
        row("Final molasses", C.molasses_flow_lb_hr, C.molasses_brix, C.molasses_purity, self.fin_mol_pol)

        # ── Pol recovery ───────────────────────────────────────────────────────
        hdr("POL RECOVERY")
        pol_in = syrup.pol_flow
        print(f"  POL in (syrup)       : {pol_in:>12,.1f} lb/hr")
        print(f"  POL to sugar         : {self.total_sugar_pol:>12,.1f} lb/hr  ({self.pol_recovery_pct:.2f}%)")
        print(f"  POL to final molasses: {self.fin_mol_pol:>12,.1f} lb/hr  ({self.molasses_loss_pct:.2f}%)")

        # ── Steam consumption ──────────────────────────────────────────────────
        pans = [
            (self.A_pans,     "A Pans"),
            (self.B_pans,     "B Pans"),
            (self.grain_pans, "Grain Pans"),
            (self.C_pans,     "C Pans"),
        ]
        if any(p is not None for p, _ in pans):
            hdr("STEAM CONSUMPTION")
            print(f"  {'Pan':<22}  {'Steam lb/hr':>14}  {'Steam type':>12}  {'lb steam/lb H₂O':>16}")
            print(f"  {'─'*22}  {'─'*14}  {'─'*12}  {'─'*16}")
            for pan, label in pans:
                if pan is not None:
                    print(f"  {label:<22}  {pan.steam_flow_lb_hr:>14,.0f}"
                          f"  {pan.steam_type:>12}  {pan.steam_to_evaporation_ratio:>16.3f}")
            print(f"  {'─'*22}  {'─'*14}  {'─'*12}  {'─'*16}")
            print(f"  {'Total steam':<22}  {self.total_steam_lb_hr:>14,.0f}")

        # ── Balance closure ────────────────────────────────────────────────────
        hdr("BALANCE CLOSURE")
        bal = self.balance_check
        chk("POL (lb/hr)",    bal['pol']['in_lb_hr'],    bal['pol']['in_lb_hr']    - bal['pol']['diff_lb_hr'])
        chk("Solids (lb/hr)", bal['solids']['in_lb_hr'], bal['solids']['in_lb_hr'] - bal['solids']['diff_lb_hr'])

        print(f"\n{'═' * W}\n")


if __name__ == "__main__":
    from three_boiling_double_magma_OOP import (
        syrup, A_centrifugals, B_centrifugals, C_machines,
        A_pans, B_pans, grain_pans, C_pans
    )

    balance = BoilingHouseBalance(
        syrup=syrup,
        A_centrifugals=A_centrifugals,
        B_centrifugals=B_centrifugals,
        C_machines=C_machines,
        A_pans=A_pans,
        B_pans=B_pans,
        grain_pans=grain_pans,
        C_pans=C_pans,
    )

    print(balance)
    balance.neat_display()
