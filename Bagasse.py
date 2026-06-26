class Bagasse:
    def __init__(self, moisture_pct, brix_pct, pol_pct, ash_pct, flowrate_lb_hr):
        self.moisture_pct = moisture_pct
        self.brix_pct = brix_pct
        self.pol_pct = pol_pct
        self.ash_pct = ash_pct
        self.flowrate_lb_hr = flowrate_lb_hr

    @property
    def fiber_pct(self):
        return 100 - self.moisture_pct - self.brix_pct

    @property
    def gcv(self):
        M = self.moisture_pct
        A = self.ash_pct
        B = self.brix_pct
        return (19605 - 196.05 * M - 196.05 * A - 31.14 * B) * 0.4299

    def display(self):
        print("=" * 40)
        print(f"{'BAGASSE PROPERTIES':^40}")
        print("=" * 40)
        print(f"  {'Flowrate':<20} {self.flowrate_lb_hr:>10,.2f}  lb/hr")
        print("-" * 40)
        print(f"  {'Fiber':<20} {self.fiber_pct:>10.2f}  %")
        print(f"  {'Moisture':<20} {self.moisture_pct:>10.2f}  %")
        print(f"  {'Brix':<20} {self.brix_pct:>10.2f}  %")
        print(f"  {'Pol':<20} {self.pol_pct:>10.2f}  %")
        print(f"  {'Ash':<20} {self.ash_pct:>10.2f}  %  (assumed part of fiber)")
        print("-" * 40)
        print(f"  {'GCV':<20} {self.gcv:>10.2f}  BTU/lb")
        print("=" * 40)


if __name__ == "__main__":
    b = Bagasse(
        moisture_pct=49.0,
        brix_pct=1.2,
        pol_pct=0.8,
        ash_pct=4.0,
        flowrate_lb_hr=125_000
    )
    b.display()
