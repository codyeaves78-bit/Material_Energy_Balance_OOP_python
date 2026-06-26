from SugarStream import SugarStream


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


class Clarification:
    """
    Clarification section material balance for a single-clarifier cane sugar factory.

    All mass balance calculations run in __init__. The clarified juice output is a
    SugarStream so this unit can chain directly into an evaporator or pan stage.

    Parameters
    ----------
    mixed_juice_stream              : SugarStream from the mill floor.
    cane_tpd                        : Cane throughput (short TPD).
    filter_wash_water_pct_on_cane   : Wash water applied to rotary filter (% on cane).
    filter_cake_pct_on_cane         : Filter cake discharge rate (% on cane).
    filter_cake_pol_pct             : Pol % in filter cake (factory-measured).
    clarified_juice_purity          : Target clarified juice purity (%).
    limed_juice_cold_temp_f         : Limed juice temperature before heaters (°F) [default 85].
    limed_juice_hot_temp_f          : Limed juice temperature after heaters (°F) [default 220].
    clarified_juice_temp_f          : Clarified juice temperature leaving clarifier (°F) [default 205].
    lime_lb_per_ton_cane            : Lime addition (lb per short ton of cane) [default 1.3].
    lime_baume                      : Milk-of-lime concentration as Baumé [default 10].
    polymer_lb_per_ton_cane         : Polymer dose (lb per short ton of cane) [default 0.045].
    polymer_conc_ppm                : Polymer solution concentration in ppm [default 5000].
    clarifier_underflow_pct_cane    : Clarifier underflow as % of cane [default 20].
    name                            : Display name for the unit [default 'Clarification'].

    Key outputs
    -----------
    clarified_juice_stream      : SugarStream — clarified juice leaving the clarifier.
    flash_vapor_pct             : Flash vapor as % of limed juice.
    filter_cake_pol_lb_per_day  : Pol lost to filter cake (lb/day).
    streams                     : dict — all stream details (flow, brix, pol, gpm, etc.).
    """

    def __init__(
        self,
        mixed_juice_stream: SugarStream,
        cane_tpd: float,
        filter_wash_water_pct_on_cane: float,
        filter_cake_pct_on_cane: float,
        filter_cake_pol_pct: float,
        clarified_juice_purity: float,
        limed_juice_cold_temp_f: float = 85.0,
        limed_juice_hot_temp_f: float = 220.0,
        clarified_juice_temp_f: float = 205.0,
        lime_lb_per_ton_cane: float = 1.3,
        lime_baume: float = 10,
        polymer_lb_per_ton_cane: float = 0.045,
        polymer_conc_ppm: float = 5000,
        clarifier_underflow_pct_cane: float = 20,
        name: str = 'Clarification',
    ):
        self.name                          = name
        self.cane_tpd                      = cane_tpd
        self.filter_wash_water_pct_on_cane = filter_wash_water_pct_on_cane
        self.filter_cake_pct_on_cane       = filter_cake_pct_on_cane
        self.filter_cake_pol_pct           = filter_cake_pol_pct
        self.clarified_juice_purity        = clarified_juice_purity
        self.limed_juice_cold_temp_f       = limed_juice_cold_temp_f
        self.limed_juice_hot_temp_f        = limed_juice_hot_temp_f
        self.clarified_juice_temp_f        = clarified_juice_temp_f
        self.lime_lb_per_ton_cane          = lime_lb_per_ton_cane
        self.lime_baume                    = lime_baume
        self.polymer_lb_per_ton_cane       = polymer_lb_per_ton_cane
        self.polymer_conc_ppm              = polymer_conc_ppm
        self.clarifier_underflow_pct_cane  = clarifier_underflow_pct_cane

        FLASH_TEMP_F = 212.0

        # ── Unpack mixed juice from SugarStream ───────────────────────────────
        mj_lb_hr    = mixed_juice_stream.flow_lb_per_hr
        mj_brix_pct = mixed_juice_stream.brix
        mj_purity   = mixed_juice_stream.purity
        mj_temp_f   = mixed_juice_stream.temp_deg_F
        mj_pol_pct  = mj_brix_pct * mj_purity / 100

        cane_lb_hr = cane_tpd * 2000 / 24

        # ── Fixed external inputs (lb/hr) ─────────────────────────────────────
        lime_lb_hr       = cane_tpd * lime_lb_per_ton_cane / 24
        lime_water_lb_hr = lime_lb_hr / (lime_baume / 100) - lime_lb_hr
        polymer_lb_hr    = cane_tpd * polymer_lb_per_ton_cane / 24
        poly_water_lb_hr = polymer_lb_hr * 10**6 / polymer_conc_ppm - polymer_lb_hr
        wash_water_lb_hr = cane_lb_hr * filter_wash_water_pct_on_cane / 100
        fc_lb_hr         = cane_lb_hr * filter_cake_pct_on_cane / 100
        mol_lb_hr        = lime_lb_hr + lime_water_lb_hr
        poly_sol_lb_hr   = polymer_lb_hr + poly_water_lb_hr
        fixed_lb_hr      = mj_lb_hr + mol_lb_hr + poly_sol_lb_hr

        # ── MJ brix/pol (lb/hr) ───────────────────────────────────────────────
        mj_brix_lb_hr = mj_lb_hr * mj_brix_pct / 100
        mj_pol_lb_hr  = mj_lb_hr * mj_pol_pct  / 100
        fc_pol_lb_hr  = fc_lb_hr * filter_cake_pol_pct / 100

        # ── CJ brix/pol — external pol and brix balances ─────────────────────
        cj_pol_lb_hr  = mj_pol_lb_hr - fc_pol_lb_hr
        cj_brix_lb_hr = cj_pol_lb_hr * 100 / clarified_juice_purity

        # ── Filter cake brix ──────────────────────────────────────────────────
        fc_brix_lb_hr = mj_brix_lb_hr - cj_brix_lb_hr
        fc_purity     = fc_pol_lb_hr / fc_brix_lb_hr * 100
        fc_brix_pct   = fc_brix_lb_hr / fc_lb_hr * 100

        # ── Clarifier underflow ───────────────────────────────────────────────
        uf_brix_pct   = mj_brix_pct
        uf_pol_pct    = uf_brix_pct * fc_purity / 100
        uf_lb_hr      = clarifier_underflow_pct_cane / 100 * cane_lb_hr
        uf_pol_lb_hr  = uf_lb_hr * uf_pol_pct  / 100
        uf_brix_lb_hr = uf_lb_hr * uf_brix_pct / 100

        # ── Rotary filter — filtrate = underflow + wash − cake ────────────────
        filtrate_lb_hr      = wash_water_lb_hr + uf_lb_hr - fc_lb_hr
        filtrate_pol_lb_hr  = uf_pol_lb_hr  - fc_pol_lb_hr
        filtrate_brix_lb_hr = uf_brix_lb_hr - fc_brix_lb_hr
        filtrate_brix_pct   = filtrate_brix_lb_hr / filtrate_lb_hr * 100
        filtrate_pol_pct    = filtrate_pol_lb_hr  / filtrate_lb_hr * 100
        filtrate_purity     = filtrate_pol_lb_hr  / filtrate_brix_lb_hr * 100

        # ── Limed juice ───────────────────────────────────────────────────────
        lj_lb_hr      = fixed_lb_hr + filtrate_lb_hr
        lj_brix_lb_hr = mj_brix_lb_hr + filtrate_brix_lb_hr
        lj_pol_lb_hr  = mj_pol_lb_hr  + filtrate_pol_lb_hr
        lj_brix_pct   = lj_brix_lb_hr / lj_lb_hr * 100
        lj_pol_pct    = lj_pol_lb_hr  / lj_lb_hr * 100

        # ── Flash tank ────────────────────────────────────────────────────────
        flash_vapor_lb_hr = (
            lj_lb_hr * (limed_juice_hot_temp_f - 212) * get_cp(lj_brix_pct) / 970
            if limed_juice_hot_temp_f > 212 else 0
        )
        fj_lb_hr      = lj_lb_hr - flash_vapor_lb_hr
        fj_brix_lb_hr = lj_brix_lb_hr
        fj_pol_lb_hr  = lj_pol_lb_hr
        fj_brix_pct   = fj_brix_lb_hr / fj_lb_hr * 100
        fj_pol_pct    = fj_pol_lb_hr  / fj_lb_hr * 100

        # ── Clarified juice ───────────────────────────────────────────────────
        cj_lb_hr    = fixed_lb_hr + wash_water_lb_hr - fc_lb_hr - flash_vapor_lb_hr
        cj_pol_pct  = cj_pol_lb_hr  / cj_lb_hr * 100
        cj_brix_pct = cj_brix_lb_hr / cj_lb_hr * 100

        # ── Scalar outputs ────────────────────────────────────────────────────
        self.flash_vapor_pct            = flash_vapor_lb_hr / lj_lb_hr * 100
        self.filter_cake_pol_lb_per_day = fc_pol_lb_hr * 24

        # ── Clarified juice output stream ─────────────────────────────────────
        self.clarified_juice_stream = SugarStream(
            brix=cj_brix_pct,
            purity=clarified_juice_purity,
            flow_lb_per_hr=cj_lb_hr,
            temp_deg_F=clarified_juice_temp_f,
            pressure_psia=14.7,
            level_ft=0,
        )

        # ── Stream table ──────────────────────────────────────────────────────
        def _gpm(lb_hr, sg):
            return lb_hr / (sg * 8.34 * 60)

        raw = [
            ("Mixed Juice",         "In",       mj_lb_hr,          mj_brix_pct,       mj_pol_pct,          mj_temp_f),
            ("Lime",                "In",       lime_lb_hr,        0.0,               0.0,                 None),
            ("Water for Lime",      "In",       lime_water_lb_hr,  0.0,               0.0,                 None),
            ("Polymer",             "In",       polymer_lb_hr,     0.0,               0.0,                 None),
            ("Polymer Water",       "In",       poly_water_lb_hr,  0.0,               0.0,                 None),
            ("Filter Wash Water",   "In",       wash_water_lb_hr,  0.0,               0.0,                 None),
            ("Flash Vapors",        "Out",      flash_vapor_lb_hr, 0.0,               0.0,                 FLASH_TEMP_F),
            ("Clarified Juice",     "Out",      cj_lb_hr,          cj_brix_pct,       cj_pol_pct,          clarified_juice_temp_f),
            ("Filter Cake",         "Out",      fc_lb_hr,          fc_brix_pct,       filter_cake_pol_pct, None),
            ("Milk of Lime",        "Internal", mol_lb_hr,         0.0,               0.0,                 None),
            ("Polymer Solution",    "Internal", poly_sol_lb_hr,    0.0,               0.0,                 None),
            ("Limed Juice Cold",    "Internal", lj_lb_hr,          lj_brix_pct,       lj_pol_pct,          limed_juice_cold_temp_f),
            ("Limed Juice Hot",     "Internal", lj_lb_hr,          lj_brix_pct,       lj_pol_pct,          limed_juice_hot_temp_f),
            ("Flashed Juice",       "Internal", fj_lb_hr,          fj_brix_pct,       fj_pol_pct,          FLASH_TEMP_F),
            ("Clarifier Underflow", "Internal", uf_lb_hr,          uf_brix_pct,       uf_pol_pct,          None),
            ("Filtrate",            "Internal", filtrate_lb_hr,    filtrate_brix_pct, filtrate_pol_pct,    None),
        ]

        self.streams = {}
        for sname, direction, lb_hr, brix, pol, temp in raw:
            purity = pol / brix * 100 if brix > 0 else 0.0
            sg     = specific_gravity(brix) if brix > 0 else 1.0
            self.streams[sname] = {
                "direction":      direction,
                "lb_per_hr":      lb_hr,
                "gpm":            _gpm(lb_hr, sg),
                "brix_pct":       brix,
                "pol_pct":        pol,
                "purity_pct":     purity,
                "sg":             sg,
                "brix_lb_per_hr": lb_hr * brix / 100,
                "pol_lb_per_hr":  lb_hr * pol  / 100,
                "pct_on_cane":    lb_hr / cane_lb_hr * 100,
                "temp_f":         temp,
            }

    # ── Balance ───────────────────────────────────────────────────────────────

    @property
    def balance_check(self):
        keys = ("lb_per_hr", "brix_lb_per_hr", "pol_lb_per_hr")
        totals = {"in": {}, "out": {}, "difference": {}}
        for key in keys:
            in_  = sum(s[key] for s in self.streams.values() if s["direction"] == "In")
            out_ = sum(s[key] for s in self.streams.values() if s["direction"] == "Out")
            totals["in"][key]         = in_
            totals["out"][key]        = out_
            totals["difference"][key] = in_ - out_
        return totals

    # ── Display ───────────────────────────────────────────────────────────────

    def __repr__(self):
        cj = self.clarified_juice_stream
        return (
            f"Clarification(cane={self.cane_tpd:,.0f} TPD, "
            f"CJ brix={cj.brix:.2f}%, purity={cj.purity:.1f}%, "
            f"flow={cj.flow_lb_per_hr:,.0f} lb/hr)"
        )

    def neat_display(self):
        cj = self.clarified_juice_stream

        col_w   = [22, 10, 10, 10, 8, 8, 8, 8, 6]
        headers = ["Stream", "lb/hr", "GPM", "Brix lb/hr", "Brix%", "Pol%", "Purity%", "%Cane", "°F"]

        def _fmt(v):
            if v is None:          return "-"
            if isinstance(v, str): return v
            return f"{v:,.2f}"

        sep        = "  ".join("-" * w for w in col_w)
        header_row = "  ".join(h.ljust(w) for h, w in zip(headers, col_w))

        print(f"\n{'═' * 61}")
        print(f"  {self.name}")
        print(f"{'═' * 61}")
        print(header_row)
        print(sep)

        for direction in ("In", "Out", "Internal"):
            group = {n: s for n, s in self.streams.items() if s["direction"] == direction}
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
        bal = self.balance_check
        for label, key in (("In", "in"), ("Out", "out"), ("Diff", "difference")):
            row = [label, f"{bal[key]['lb_per_hr']:,.0f}", "",
                   f"{bal[key]['brix_lb_per_hr']:,.1f}", "", "", "", "", ""]
            print("  ".join(v.ljust(w) for v, w in zip(row, col_w)))
        print(sep)

        print(f"\n  Flash vapor:          {self.flash_vapor_pct:.3f}% of limed juice")
        print(f"  Filter cake pol loss: {self.filter_cake_pol_lb_per_day:,.0f} lb/day")

        print(f"\n  Clarified juice stream:")
        print(f"  {cj}")
        print(f"\n{'═' * 61}\n")


if __name__ == "__main__":
    from MillFloor import MillFloor

    mill = MillFloor(
        cane_tpd=17_000,
        cane_pol_pct=13.5,
        cane_fiber_pct=14.0,
        imbibition_pct_on_cane=25.0,
        bagasse_pol_pct=1.8,
        last_roll_purity=72.0,
        bagasse_moisture_pct=49.0,
        mix_juice_purity=88.0,
        number_of_mills=5,
        juice_temp_F=90.0,
    )

    clarifier = Clarification(
        mixed_juice_stream=mill.mixed_juice_stream,
        cane_tpd=mill.cane_tpd,
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

    print(clarifier)
    clarifier.neat_display()

    print("Clarified juice stream:")
    print(clarifier.clarified_juice_stream)
