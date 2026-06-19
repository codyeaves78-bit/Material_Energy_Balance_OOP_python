# Centrifugal separator — SJM (Sugar-Massecuite-Molasses) material balance.
# Two-step approach: (1) SJM ideal split with specified S, J, M₀; (2) crystal loss as
# 100%-pol sucrose fragments dissolve into molasses, updating M; (3) final SJM with updated M.
# target_molasses_brix drives wash water back-calculation.
# sugar_purity (AP = pol/solids) and sugar_moisture are specified quality targets.

from SugarStream import SugarStream

_GAL_PER_FT3 = 7.48052  # US gallons per cubic foot


def _sugar_density_lb_ft3(brix, temp_F=77.0):
    """Density of a sugar solution (lb/ft³) at given Brix and temperature.
    Same formula as Massecuite._density_at — Brix-polynomial fit at 20°C with linear T correction.
    """
    rho_20C = 0.99823 + 3.848e-3*brix + 1.427e-5*brix**2 + 1.5e-8*brix**3
    temp_C  = (temp_F - 32) * 5/9
    return rho_20C * (1 - 4.1e-4 * (temp_C - 20)) * 62.428


class Centrifugal:
    """
    Centrifugal separator for massecuite.

    massecuite            : Massecuite instance — provides crystal_content, masse_brix,
                            masse_purity, ml_purity, massecuite_temp
    massecuite_flow_lb_hr : massecuite flow entering the centrifugal (lb/hr)
                            — pass pan.massecuite_flow_lb_hr when chaining from Pan
    target_molasses_brix  : desired molasses outlet Brix — back-calculates required wash water
    crystal_loss_pct      : % of gross crystals dissolved or lost to molasses [default 1.0]
    sugar_purity          : apparent purity of the sugar product (AP = pol/solids × 100)  [e.g. 99.5]
                            Industry-standard definition: pol as a % of dry solids (not wet weight).
                            Rule of thumb: A ≈ 99.5, B ≈ 98–99, C ≈ 93–96.
    sugar_moisture        : moisture in the wet sugar product (%)  [e.g. 0.5]

    SJM balance (two-step):
        S = sugar_purity (AP),  J = masse_purity,  M₀ = ml_purity

        Step 1 — ideal split at 0% crystal loss (S, J, M₀):
            mol_solids_ideal  = massecuite_solids × (S − J) / (S − M₀)
            pol_mol_ideal     = M₀/100 × mol_solids_ideal

        Step 2 — crystal loss as pure-sucrose fragments into molasses:
            crystal_pol_lost  = crystals_gross × crystal_loss_pct / 100   (100% pol)
            mol_pol_updated   = pol_mol_ideal + crystal_pol_lost
            mol_solids_updated= mol_solids_ideal + crystal_pol_lost
            M_updated         = mol_pol_updated / mol_solids_updated × 100

        Step 3 — final SJM with updated M:
            sugar_solids      = massecuite_solids × (J − M_updated) / (S − M_updated)
            sugar_pol         = S/100 × sugar_solids
            sugar_wet         = sugar_solids / (1 − sugar_moisture/100)
            molasses_solids   = massecuite_solids − sugar_solids
            molasses_flow     = molasses_solids / (target_molasses_brix/100)  ← target brix
            wash_water        = molasses_flow + sugar_wet − massecuite_flow   ← back-calculated
            pol_to_molasses   = pol_in − sugar_pol
            molasses_purity   = pol_to_molasses / molasses_solids × 100

    Output dicts:
        .sugar    — wet flow, dry flow, pol, purity, moisture
        .molasses — flow, brix, purity, pol

    Output stream:
        .molasses_stream — SugarStream ready to feed the next Pan grade
    """

    def __init__(self, massecuite, massecuite_flow_lb_hr,
                 target_molasses_brix=85.0,
                 purity_rise=2.0,
                 sugar_purity=99.5,
                 sugar_moisture=0.5):
        self.massecuite            = massecuite
        self.massecuite_flow_lb_hr = massecuite_flow_lb_hr
        self.target_molasses_brix  = target_molasses_brix
        self.purity_rise           = purity_rise
        self.sugar_purity          = sugar_purity
        self.sugar_moisture        = sugar_moisture

    # ------------------------------------------------------------------
    # SJM balance  (S = sugar_purity, J = masse_purity, M = molasses_purity)
    # (S-J)/(S-M) = molasses solids / massecuite solids
    # (J-M)/(S-M) = sugar solids   / massecuite solids
    # Pol balance closes exactly in one pass — no iteration needed.
    # ------------------------------------------------------------------

    @property
    def massecuite_solids_lb_hr(self):
        """Total solids entering in the massecuite (lb/hr)."""
        return self.massecuite_flow_lb_hr * self.massecuite.masse_brix / 100.0

    @property
    def molasses_purity(self):
        """Molasses apparent purity = ml_purity + purity_rise (%).
        purity_rise captures all effects (crystal loss, wash dilution, etc.)
        and is specified by the user based on process knowledge.
        """
        return self.massecuite.ml_purity + self.purity_rise

    @property
    def crystals_to_sugar_lb_hr(self):
        """Dry solids in the sugar product (lb/hr).
        SJM: massecuite_solids × (J − M) / (S − M)
        """
        S = self.sugar_purity
        J = self.massecuite.masse_purity
        M = self.molasses_purity
        return self.massecuite_solids_lb_hr * (J - M) / (S - M)

    # ------------------------------------------------------------------
    # Sugar product
    # ------------------------------------------------------------------

    @property
    def sugar_wet_lb_hr(self):
        """Wet sugar flow leaving the centrifugal (crystals + retained moisture) (lb/hr)."""
        return self.crystals_to_sugar_lb_hr / (1.0 - self.sugar_moisture / 100.0)

    @property
    def sugar_moisture_lb_hr(self):
        """Moisture retained in the sugar product (lb/hr)."""
        return self.sugar_wet_lb_hr - self.crystals_to_sugar_lb_hr

    @property
    def sugar_brix(self):
        """Brix of the wet sugar product (%) = 100 − moisture%.
        Solids fraction of the wet sugar on a weight basis.
        """
        return 100.0 - self.sugar_moisture

    @property
    def sugar_pol_lb_hr(self):
        """Sucrose (pol) in the sugar product (lb/hr).
        sugar_purity is Apparent Purity (AP) = pol/solids × 100, the standard industry definition.
        pol = solids × AP/100 = crystals_to_sugar × sugar_purity/100.
        """
        return self.crystals_to_sugar_lb_hr * self.sugar_purity / 100.0

    # ------------------------------------------------------------------
    # Molasses balance
    # ------------------------------------------------------------------

    @property
    def pol_in_lb_hr(self):
        """Total sucrose entering the centrifugal from the massecuite (lb/hr)."""
        return self.massecuite_solids_lb_hr * self.massecuite.masse_purity / 100.0

    @property
    def molasses_solids_lb_hr(self):
        """Dissolved solids in the molasses stream (lb/hr)."""
        return self.massecuite_solids_lb_hr - self.crystals_to_sugar_lb_hr

    @property
    def molasses_brix(self):
        """Molasses outlet Brix — equals target_molasses_brix (%)."""
        return self.target_molasses_brix

    @property
    def molasses_flow_lb_hr(self):
        """Total molasses flow: back-calculated from target_molasses_brix (lb/hr).
        molasses_flow = molasses_solids / (target_molasses_brix / 100)
        """
        return self.molasses_solids_lb_hr / (self.target_molasses_brix / 100.0)

    @property
    def wash_water_lb_hr(self):
        """Wash water required to reach target_molasses_brix (lb/hr).
        wash_water = molasses_flow + sugar_wet - massecuite_flow
        Negative means the massecuite molasses is already below target brix — raise instead.
        """
        ww = self.molasses_flow_lb_hr + self.sugar_wet_lb_hr - self.massecuite_flow_lb_hr
        if ww < 0:
            raise ValueError(
                f"target_molasses_brix ({self.target_molasses_brix:.1f}) is higher than the "
                f"natural molasses Brix without wash water "
                f"({self.molasses_solids_lb_hr / (self.massecuite_flow_lb_hr - self.sugar_wet_lb_hr) * 100:.1f}). "
                "Lower the target or set it to None to skip washing."
            )
        return ww

    @property
    def pol_to_sugar_lb_hr(self):
        """Sucrose assigned to the sugar product (lb/hr)."""
        return self.sugar_pol_lb_hr

    @property
    def pol_to_molasses_lb_hr(self):
        """Sucrose in the molasses stream (lb/hr) = molasses_purity/100 × molasses_solids."""
        return self.pol_in_lb_hr - self.pol_to_sugar_lb_hr

    @property
    def molasses_density_lb_ft3(self):
        """Molasses density at 77°F (25°C) standard reference (lb/ft³)."""
        return _sugar_density_lb_ft3(self.molasses_brix, temp_F=77.0)

    @property
    def molasses_density_lb_gal(self):
        """Molasses density at 77°F standard reference (lb/US gal)."""
        return self.molasses_density_lb_ft3 / _GAL_PER_FT3

    @property
    def molasses_flow_gal_min(self):
        """Molasses volumetric flow at 77°F reference density (US gal/min)."""
        return self.molasses_flow_lb_hr / (self.molasses_density_lb_gal * 60.0)
    
    @property
    def sugar_pol(self):
        """Calculates the Pol % sugar"""
        return self.sugar_pol_lb_hr / self.sugar_wet_lb_hr * 100

    # ------------------------------------------------------------------
    # Crystal yield
    # ------------------------------------------------------------------

    @property
    def station_crystal_yield_pct_brix(self):
        """Crystals recovered as % of massecuite solids (brix basis).
        100 × (J − M) / (100 − M)  where J = masse_purity, M = molasses_purity.
        """
        J = self.massecuite.masse_purity
        M = self.molasses_purity
        return 100.0 * (J - M) / (100.0 - M)

    @property
    def station_crystal_yield_pct_masse(self):
        """Crystals recovered as % of total massecuite flow (wet basis).
        = crystal_yield_pct_brix × masse_brix / 100
        """
        return self.station_crystal_yield_pct_brix * self.massecuite.masse_brix / 100.0

    # ------------------------------------------------------------------
    # Output stream (for chaining to the next Pan grade)
    # ------------------------------------------------------------------

    @property
    def molasses_stream(self):
        """SugarStream representing the molasses output.
        Temperature set to the massecuite boiling temperature — adjust if needed.
        Use this as a feed_stream to the next Pan grade.
        """
        return SugarStream(
            brix=self.molasses_brix,
            purity=self.molasses_purity,
            flow_lb_per_hr=self.molasses_flow_lb_hr,
            temp_deg_F=self.massecuite.massecuite_temp,
            pressure_psia=14.7,
            level_ft=0,
        )

    # ------------------------------------------------------------------
    # Dict outputs
    # ------------------------------------------------------------------

    @property
    def sugar(self):
        """Sugar product summary dict."""
        return {
            'flow_wet_lb_hr':  self.sugar_wet_lb_hr,
            'flow_dry_lb_hr':  self.crystals_to_sugar_lb_hr,
            'pol_lb_hr':       self.sugar_pol_lb_hr,
            'purity_pct':      self.sugar_purity,
            'moisture_pct':    self.sugar_moisture,
        }

    @property
    def molasses(self):
        """Molasses stream summary dict."""
        return {
            'flow_lb_hr':  self.molasses_flow_lb_hr,
            'brix':        self.molasses_brix,
            'purity':      self.molasses_purity,
            'pol_lb_hr':   self.pol_to_molasses_lb_hr,
        }

    # ------------------------------------------------------------------
    # Dunder / display
    # ------------------------------------------------------------------

    def __repr__(self):
        return (
            f"Centrifugal(masse_flow={self.massecuite_flow_lb_hr:,.0f} lb/hr, "
            f"J={self.massecuite.masse_purity:.1f}%, "
            f"M={self.molasses_purity:.1f}% (ml={self.massecuite.ml_purity:.1f}+rise={self.purity_rise:.1f}), "
            f"S={self.sugar_purity:.1f}%, target_mol_brix={self.target_molasses_brix:.1f})"
        )

    def properties(self):
        return {
            # --- Feed ---
            'massecuite_flow_lb_hr':   self.massecuite_flow_lb_hr,
            'masse_brix':              self.massecuite.masse_brix,
            'masse_purity':            self.massecuite.masse_purity,
            'ml_purity':               self.massecuite.ml_purity,
            # --- SJM inputs ---
            'sugar_purity_pct':        self.sugar_purity,
            'molasses_purity_target':  self.molasses_purity,
            'purity_rise':             self.purity_rise,
            # --- Wash ---
            'target_molasses_brix':    self.target_molasses_brix,
            'wash_water_lb_hr':        self.wash_water_lb_hr,
            # --- Sugar product ---
            'sugar_solids_lb_hr':      self.crystals_to_sugar_lb_hr,
            'sugar_moisture_pct':      self.sugar_moisture,
            'sugar_wet_lb_hr':         self.sugar_wet_lb_hr,
            'sugar_moisture_lb_hr':    self.sugar_moisture_lb_hr,
            'sugar_pol_lb_hr':         self.sugar_pol_lb_hr,
            # --- Molasses ---
            'pol_in_lb_hr':            self.pol_in_lb_hr,
            'pol_to_sugar_lb_hr':      self.pol_to_sugar_lb_hr,
            'pol_to_molasses_lb_hr':   self.pol_to_molasses_lb_hr,
            'molasses_flow_lb_hr':     self.molasses_flow_lb_hr,
            'molasses_brix':           self.molasses_brix,
            'molasses_purity':         self.molasses_purity,
            # --- Performance ---
            'station_crystal_yield_pct_brix':  self.station_crystal_yield_pct_brix,
            'station_crystal_yield_pct_masse': self.station_crystal_yield_pct_masse,
        }

    def display_properties(self):
        props = self.properties()
        print("Units: flow(lb/hr), purity/brix/moisture(%)")
        for k, v in props.items():
            print(f"  {k:<28}: {v:,.3f}")


if __name__ == "__main__":
    from Massecuite import Massecuite

    # --- A massecuite example: target molasses brix drives wash water ---
    masse_A = Massecuite(
        ml_purity=70, masse_purity=90, masse_brix=92,
        inches_vacuum=23.5, supersaturation=1.2, head_ft=2,
    )
    cent_A = Centrifugal(
        massecuite=masse_A,
        massecuite_flow_lb_hr=226_630,
        target_molasses_brix=78.0,
        purity_rise=1.1,   # molasses purity = ml_purity + rise = 71.1%
        sugar_purity=99.5,
        sugar_moisture=0.5,
    )
    print("=== A Centrifugal ===")
    print(cent_A)
    print()
    cent_A.display_properties()
    print()
    print("Sugar  :", cent_A.sugar)
    print("Molasses:", cent_A.molasses)
    print(f"  wash water required: {cent_A.wash_water_lb_hr:,.0f} lb/hr")

    print()
    print("=== C Centrifugal (low-grade, no wash) ===")
    masse_C = Massecuite(
        ml_purity=30, masse_purity=54, masse_brix=96,
        inches_vacuum=26.0, supersaturation=1.2, head_ft=2,
    )
    cent_C = Centrifugal(
        massecuite=masse_C,
        massecuite_flow_lb_hr=100_000,
        target_molasses_brix=85.0,
        purity_rise=3.5,   # molasses purity = 33.5%
        sugar_purity=80.0,
        sugar_moisture=6,
    )
    print(cent_C)
    print()
    cent_C.display_properties()
    print()
    print("Molasses stream for next Pan:")
    ms = cent_C.molasses_stream
    print(f"  flow={ms.flow_lb_per_hr:,.0f} lb/hr  brix={ms.brix:.1f}  purity={ms.purity:.1f}")

    print()
    print("=== Water balance check (should close to zero) ===")
    for label, cent in [("A", cent_A), ("C", cent_C)]:
        water_in  = (cent.massecuite_flow_lb_hr * (1 - cent.massecuite.masse_brix / 100)
                     + cent.wash_water_lb_hr)
        water_out = (cent.sugar_moisture_lb_hr
                     + cent.molasses_flow_lb_hr * (1 - cent.molasses_brix / 100))
        print(f"  {label} pan: water_in={water_in:,.3f}  water_out={water_out:,.3f}  "
              f"imbalance={water_in - water_out:+.6f} lb/hr")

## Claude, I think i see the issue for the program. The centrifugal object is actually quite straight forward... 
## Do this first...
## sjm on centrifugal with 0% crystals lost. S = sugar purity, J = massecuite purity, M = molasses purity (mother liquor for 0% loss)
## lbs solids massecuite * (S - J) / (S - M) = lbs solids perfect molasses
## lbs solids massecuite - lbs solids perfect molasses = lbs solids in sugar
## pol in sugar = sugar purity * lbs solids sugar / 100
## pol in molasses = molasses purity * lbs solids molasses / 100
## Now account for sugar crystals loss
## crystals lbs pol = 100 % (pure sugar crystals 100% pol) * % crystals * massecuite flow
## crystals lbs washed into molasses = % cryst loss / 100 * crystals lbs pol 
## update molasses properties... lbs pol in molasses += crystals lbs washed into molasses, lbs brix molasses / hr += crystals lbs washed into molasses, purity molasses = lbs pol / lbs brix in molasses * 100
## update sugar properties... just do an SJM balance since purity is still defined as an input.. define new M = updated molasses purity
## sugar solids lb / hr = solids in massecuite lb / hr * (J - M) / (S - M), sugar lbs pol / hr = sugar purity / 100 * sugar solids lb/hr
## balance check... POL IN = masse lb/hr * % pol, POL OUT = sugar lbs pol / hr + molasses lbs pol / hr
## BRIX IN = masse lb/hr * %brix, BRIX OUT = sugar solids lb/hr + lbs brix molasses / hr
## Water IN = (1 - brix) * masse lb/hr, Water OUT subtotal = water in sugar + water in molasses. wash water = WATER IN - WATER OUT sub total