from SugarStream import SugarStream
from Bagasse import Bagasse


class MillFloor:
    """
    Mill floor material balance for a counter-current cane milling train.

    All mass balance calculations run in __init__. Results are stored as
    instance attributes for direct access — no dictionary key hunting.

    Parameters
    ----------
    cane_tpd                        : Cane throughput (short tons per day).
    cane_pol_pct                    : Pol % in cane.
    cane_fiber_pct                  : Fiber % in cane.
    imbibition_pct_on_cane          : Imbibition water as % on cane.
    bagasse_pol_pct                 : Pol % in bagasse (last mill reading).
    last_roll_purity                : Purity of last-roll juice (%).
    bagasse_moisture_pct            : Moisture % in bagasse.
    bagasse_ash_pct                 : Ash % in bagasse (used for GCV calculation) [default 2.0].
    mix_juice_purity                : Mixed juice purity (%).
    number_of_mills                 : Number of mills in the train.
    juice_temp_F                    : Temperature of mixed juice leaving the mills (°F).
    mill_1_fiber_rise_load_fraction : Fraction of total fiber % rise (cane→bagasse)
                                      absorbed by Mill 1 in a single step [default 0.35].
    name                            : Display name for the unit [default 'Mill Floor'].

    Key outputs
    -----------
    mixed_juice_stream  : SugarStream — mixed juice leaving the mill floor.
    bagasse_stream      : Bagasse — bagasse leaving the last mill (includes GCV property).
    mill_balances       : list[dict] — per-mill intermediate bagasse and maceration flows
                          (use for pump sizing; not required for the overall material balance).
    mill_extraction_pct : Pol extraction efficiency (% of pol in cane recovered in juice).
    imbibition_gpm      : Imbibition water flow (US gal/min).
    """

    def __init__(
        self,
        cane_tpd: float,
        cane_pol_pct: float,
        cane_fiber_pct: float,
        imbibition_pct_on_cane: float,
        bagasse_pol_pct: float,
        last_roll_purity: float,
        bagasse_moisture_pct: float,
        mix_juice_purity: float,
        number_of_mills: int,
        juice_temp_F: float = 90.0,
        bagasse_ash_pct: float = 2.0,
        mill_1_fiber_rise_load_fraction: float = 0.35,
        name: str = 'Mill Floor',
    ):
        self.name                           = name
        self.cane_tpd                       = cane_tpd
        self.cane_tph                       = self.cane_tpd / 24
        self.cane_lb_hr                     = self.cane_tpd * 2000 / 24
        self.cane_pol_pct                   = cane_pol_pct
        self.cane_fiber_pct                 = cane_fiber_pct
        self.imbibition_pct_on_cane         = imbibition_pct_on_cane
        self.imbibition_lb_hr               = self.imbibition_pct_on_cane / 100 * self.cane_lb_hr
        self.imbibition_tph                 = self.imbibition_lb_hr / 2000
        self.bagasse_pol_pct                = bagasse_pol_pct
        self.last_roll_purity               = last_roll_purity
        self.bagasse_moisture_pct           = bagasse_moisture_pct
        self.bagasse_ash_pct                = bagasse_ash_pct
        self.mix_juice_purity               = mix_juice_purity
        self.number_of_mills                = number_of_mills
        self.juice_temp_F                   = juice_temp_F
        self.mill_1_fiber_rise_load_fraction = mill_1_fiber_rise_load_fraction

        # ── Imbibition ────────────────────────────────────────────────────────
        imb_tpd = cane_tpd * imbibition_pct_on_cane / 100
        imb_gpm = imb_tpd * 2000 / 24 / 60 / 8.3

        # ── Bagasse ───────────────────────────────────────────────────────────
        bag_brix_pct  = bagasse_pol_pct / last_roll_purity * 100
        bag_fiber_pct = 100 - bag_brix_pct - bagasse_moisture_pct
        bag_tpd       = cane_tpd * cane_fiber_pct / bag_fiber_pct

        # ── Mixed Juice ───────────────────────────────────────────────────────
        mix_juice_tpd   = cane_tpd + imb_tpd - bag_tpd
        tons_pol_juice  = cane_tpd * cane_pol_pct / 100 - bag_tpd * bagasse_pol_pct / 100
        tons_brix_juice = tons_pol_juice * 100 / mix_juice_purity
        mix_juice_brix  = tons_brix_juice / mix_juice_tpd * 100
        mix_juice_pol   = mix_juice_brix * mix_juice_purity / 100
        mix_juice_lb_hr = mix_juice_tpd / 24 * 2000

        # ── Cane (back-calculated brix and moisture) ──────────────────────────
        cane_brix_pct  = (tons_brix_juice + bag_tpd * bag_brix_pct / 100) / cane_tpd * 100
        cane_moist_pct = 100 - cane_brix_pct - cane_fiber_pct
        self.cane_brix_pct  = cane_brix_pct
        self.cane_moist_pct = cane_moist_pct

        # ── Mill extraction ───────────────────────────────────────────────────
        self.mill_extraction_pct = tons_pol_juice / (cane_tpd * cane_pol_pct / 100) * 100
        self.imbibition_gpm      = imb_gpm

        # ── Per-mill intermediate flows (for maceration pump sizing) ──────────
        tons_fiber     = cane_tpd * cane_fiber_pct / 100
        fib_change     = bag_fiber_pct - cane_fiber_pct
        mill_1_bag_fib = cane_fiber_pct + mill_1_fiber_rise_load_fraction * fib_change
        fib_step       = (bag_fiber_pct - mill_1_bag_fib) / max(number_of_mills - 1, 1)

        fiber_list = [mill_1_bag_fib]
        for i in range(number_of_mills - 1):
            fiber_list.append(fiber_list[i] + fib_step)

        bag_flows   = [tons_fiber / (fib / 100) for fib in fiber_list]
        j1          = cane_tpd - bag_flows[0]
        j2          = mix_juice_tpd - j1
        juice_flows = [j1, j2]
        for i in range(number_of_mills - 2):
            juice_flows.append(juice_flows[i + 1] - bag_flows[i] + bag_flows[i + 1])

        mill_balances = []
        for idx in range(number_of_mills):
            mill_num  = idx + 1
            bag_in    = cane_tpd if idx == 0 else bag_flows[idx - 1]
            bag_out   = bag_flows[idx]
            juice_out = juice_flows[idx]

            if mill_num == 1:
                mac_in, mac_src = 0.0, "None"
            elif mill_num == number_of_mills:
                mac_in, mac_src = imb_tpd, "Imbibition"
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

        self.mill_balances = mill_balances

        # ── Mixed juice output ────────────────────────────────────────────────
        self.mixed_juice_stream = SugarStream(
            brix=mix_juice_brix,
            purity=mix_juice_purity,
            flow_lb_per_hr=mix_juice_lb_hr,
            temp_deg_F=juice_temp_F,
            pressure_psia=14.7,
            level_ft=0,
        )

        # ── Bagasse output ────────────────────────────────────────────────────
        self.bagasse_stream = Bagasse(
            moisture_pct=bagasse_moisture_pct,
            brix_pct=bag_brix_pct,
            pol_pct=bagasse_pol_pct,
            ash_pct=bagasse_ash_pct,
            flowrate_lb_hr=bag_tpd / 24 * 2000,
        )

    @property
    def balance_check(self):
        mj  = self.mixed_juice_stream
        bag = self.bagasse_stream

        mj_tph       = mj.flow_lb_per_hr / 2000
        mj_brix_tph  = mj.solids_flow    / 2000   # solids_flow is lb/hr
        mj_pol_tph   = mj.pol_flow       / 2000   # pol_flow is lb/hr
        mj_moist_tph = mj_tph - mj_brix_tph       # no fiber in juice

        bag_tph       = bag.flowrate_lb_hr / 2000
        bag_brix_tph  = bag_tph * bag.brix_pct     / 100
        bag_pol_tph   = bag_tph * bag.pol_pct      / 100
        bag_fiber_tph = bag_tph * bag.fiber_pct    / 100
        bag_moist_tph = bag_tph * bag.moisture_pct / 100

        # total mass
        total_in  = self.cane_tph + self.imbibition_tph
        total_out = mj_tph + bag_tph

        # pol balance
        pol_in  = self.cane_tph * self.cane_pol_pct  / 100
        pol_out = mj_pol_tph + bag_pol_tph

        # brix balance
        brix_in  = self.cane_tph * self.cane_brix_pct / 100   # imbibition is pure water
        brix_out = mj_brix_tph + bag_brix_tph

        # fiber balance (fiber stays in bagasse only — none in juice)
        fiber_in  = self.cane_tph * self.cane_fiber_pct / 100
        fiber_out = bag_fiber_tph

        # water balance
        water_in  = self.cane_tph * self.cane_moist_pct / 100 + self.imbibition_tph
        water_out = mj_moist_tph + bag_moist_tph

        return {
            'total': {'in_tph': total_in,  'out_tph': total_out,  'diff_tph': total_in  - total_out},
            'pol':   {'in_tph': pol_in,    'out_tph': pol_out,    'diff_tph': pol_in    - pol_out},
            'brix':  {'in_tph': brix_in,   'out_tph': brix_out,   'diff_tph': brix_in   - brix_out},
            'fiber': {'in_tph': fiber_in,  'out_tph': fiber_out,  'diff_tph': fiber_in  - fiber_out},
            'water': {'in_tph': water_in,  'out_tph': water_out,  'diff_tph': water_in  - water_out},
        }


    # ── Display ───────────────────────────────────────────────────────────────

    def __repr__(self):
        return (
            f"MillFloor(cane={self.cane_tpd:,.0f} TPD, "
            f"pol={self.cane_pol_pct:.1f}%, fiber={self.cane_fiber_pct:.1f}%, "
            f"extraction={self.mill_extraction_pct:.2f}%, "
            f"mills={self.number_of_mills})"
        )

    def neat_display(self):
        mj  = self.mixed_juice_stream
        bag = self.bagasse_stream

        def row(label, value, unit=""):
            print(f"  {label:<35} {value:>14,.2f}  {unit}")

        def section(title):
            print(f"\n  {'─' * 57}")
            print(f"  {title}")
            print(f"  {'─' * 57}")

        print(f"\n{'═' * 61}")
        print(f"  {self.name}  |  {self.number_of_mills} mills  "
              f"|  extraction={self.mill_extraction_pct:.2f}%")
        print(f"{'═' * 61}")

        section("CANE FEED")
        row("Cane throughput",      self.cane_tpd,              "TPD")
        row("Cane pol",             self.cane_pol_pct,          "%")
        row("Cane fiber",           self.cane_fiber_pct,        "%")
        row("Imbibition",           self.imbibition_pct_on_cane,"% on cane")
        row("Imbibition flow",      self.imbibition_gpm,        "GPM")

        section("MIXED JUICE")
        row("Flow",                 mj.flow_lb_per_hr,          "lb/hr")
        row("Brix",                 mj.brix,                    "%")
        row("Purity",               mj.purity,                  "%")
        row("Pol",                  mj.pol,                     "%")
        row("Temperature",          mj.temp_deg_F,              "°F")

        section("BAGASSE")
        row("Flow",                 bag.flowrate_lb_hr,              "lb/hr")
        row("Flow",                 bag.flowrate_lb_hr / 2000 * 24,  "TPD")
        row("Fiber",                bag.fiber_pct,                   "%")
        row("Pol",                  bag.pol_pct,                     "%")
        row("Brix",                 bag.brix_pct,                    "%")
        row("Moisture",             bag.moisture_pct,                "%")

        section("PERFORMANCE")
        row("Mill extraction",      self.mill_extraction_pct,   "% pol in cane")

        section("STREAM TABLE  (TPH)")
        self._print_stream_table()

        print(f"\n{'═' * 61}\n")

    def _print_stream_table(self):
        mj  = self.mixed_juice_stream
        bag = self.bagasse_stream

        mj_tph       = mj.flow_lb_per_hr / 2000
        mj_brix_tph  = mj.solids_flow    / 2000
        mj_pol_tph   = mj.pol_flow       / 2000
        mj_water_tph = mj_tph - mj_brix_tph

        bag_tph       = bag.flowrate_lb_hr / 2000
        bag_pol_tph   = bag_tph * bag.pol_pct      / 100
        bag_brix_tph  = bag_tph * bag.brix_pct     / 100
        bag_fiber_tph = bag_tph * bag.fiber_pct    / 100
        bag_water_tph = bag_tph * bag.moisture_pct / 100

        cane_pol_tph   = self.cane_tph * self.cane_pol_pct   / 100
        cane_brix_tph  = self.cane_tph * self.cane_brix_pct  / 100
        cane_fiber_tph = self.cane_tph * self.cane_fiber_pct / 100
        cane_water_tph = self.cane_tph * self.cane_moist_pct / 100

        #          name           dir    flow               pol           brix           fiber          water
        rows = [
            ("Cane",        "In",  self.cane_tph,      cane_pol_tph,  cane_brix_tph,  cane_fiber_tph, cane_water_tph),
            ("Imbibition",  "In",  self.imbibition_tph, 0.0,          0.0,            0.0,            self.imbibition_tph),
            ("Mixed Juice", "Out", mj_tph,             mj_pol_tph,   mj_brix_tph,    0.0,            mj_water_tph),
            ("Bagasse",     "Out", bag_tph,            bag_pol_tph,  bag_brix_tph,   bag_fiber_tph,  bag_water_tph),
        ]

        w = [14, 4, 12, 12, 12, 12, 12]
        hdrs = ["Stream", "Dir", "Flow (TPH)", "Pol (TPH)", "Brix (TPH)", "Fiber (TPH)", "Water (TPH)"]
        sep  = "  ".join("-" * c for c in w)

        print("  " + "  ".join(h.ljust(c) for h, c in zip(hdrs, w)))
        print("  " + sep)

        in_tot  = [0.0] * 5
        out_tot = [0.0] * 5

        for name, direction, flow, pol, brix, fiber, water in rows:
            vals = [flow, pol, brix, fiber, water]
            cells = [name, direction] + [f"{v:,.2f}" for v in vals]
            print("  " + "  ".join(v.ljust(c) for v, c in zip(cells, w)))
            totals = in_tot if direction == "In" else out_tot
            for i, v in enumerate(vals):
                totals[i] += v

        print("  " + sep)
        diff = [i - o for i, o in zip(in_tot, out_tot)]
        for label, vals, fmt in [
            ("Total In",    in_tot,  ",.2f"),
            ("Total Out",   out_tot, ",.2f"),
            ("Difference",  diff,    "+,.4f"),
        ]:
            cells = [label, ""] + [format(v, fmt) for v in vals]
            print("  " + "  ".join(v.ljust(c) for v, c in zip(cells, w)))
        print("  " + sep)

    def display_stream_table(self):
        """Print the stream component flow table as a standalone call."""
        hdrs_line = f"  Stream Component Flows — {self.name}"
        print(f"\n{hdrs_line}")
        self._print_stream_table()

    def display_mill_balances(self):
        mc_w   = [6, 16, 16, 22, 16, 26]
        mc_hdr = ["Mill", "Bagasse In (TPD)", "Liquid In (TPD)",
                  "Liquid In Source", "Bagasse Out (TPD)",
                  "Juice Out (TPD) / Dest"]
        mc_sep = "  ".join("-" * w for w in mc_w)

        print("\nPer-Mill Maceration Balance")
        print(mc_sep)
        print("  ".join(h.ljust(w) for h, w in zip(mc_hdr, mc_w)))
        print(mc_sep)
        for m in self.mill_balances:
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
        mill_1_fiber_rise_load_fraction=0.35,
    )

    print(mill)
    mill.neat_display()
    mill.display_mill_balances()

    print("\nMixed juice stream:")
    print(mill.mixed_juice_stream)

    print("\nBagasse stream:")
    mill.bagasse_stream.neat_display()
