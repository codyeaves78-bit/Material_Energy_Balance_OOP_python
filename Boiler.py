from Bagasse import Bagasse
from SteamStream import SteamStream

class Boiler:
    def __init__(
            self, 
            bagasse=Bagasse(
                moisture_pct=50, 
                brix_pct=3, 
                pol_pct=2, 
                ash_pct=4, 
                flowrate_lb_hr=1
                ), 
                efficiency=70,
                pressure_psig = 180,
                deg_superheat = 0, 
                feed_water_temp=230,
                capacity=0,
                name='Boiler #'
                ):
        self.name = name
        self.bagasse = bagasse
        self.efficiency = efficiency
        self.capacity = capacity
        self.psia = pressure_psig + 14.696
        self.deg_sh = deg_superheat
        self.feed_wat_temp = feed_water_temp

    # create feed water
    @property
    def feed_water_stream(self):
        return SteamStream(T=self.feed_wat_temp, P=self.psia)
    
    @property
    def steam_stream(self):
        sat_steam = SteamStream(P=self.psia, x=1)
        if self.deg_sh > 0:
            temp = sat_steam.T + self.deg_sh
            sh_steam = SteamStream(P=self.psia, T=temp)
        return sh_steam if self.deg_sh > 0 else sat_steam
    
    @property
    def btu_for_1_lb(self):
        return self.steam_stream.h - self.feed_water_stream.h

    @property
    def steam_available_per_lb_bagasse(self):
        return self.bagasse.gcv * self.efficiency / 100 / self.btu_for_1_lb

    @property
    def steam_availabe_lb_hr(self):
        return self.steam_available_per_lb_bagasse * self.bagasse.flowrate_lb_hr

    def neat_display(self):
        fw = self.feed_water_stream
        st = self.steam_stream
        pressure_psig = self.psia - 14.696
        condition = "Superheated" if self.deg_sh > 0 else "Saturated"

        print("=" * 50)
        print(f"{'BOILER — ' + self.name:^50}")
        print("=" * 50)
        print(f"  {'--- Parameters ---':^46}")
        print(f"  {'Efficiency':<24} {self.efficiency:>10.1f}  %")
        print(f"  {'Pressure':<24} {pressure_psig:>10.1f}  psig  ({self.psia:.3f} psia)")
        print(f"  {'Feed Water Temp':<24} {self.feed_wat_temp:>10.1f}  °F")
        print(f"  {'Superheat':<24} {self.deg_sh:>10.1f}  °F above sat")
        print("-" * 50)
        print(f"  {'--- Feed Water ---':^46}")
        print(f"  {'Temperature':<24} {fw.T:>10.2f}  °F")
        print(f"  {'Enthalpy':<24} {fw.h:>10.2f}  BTU/lb")
        print("-" * 50)
        print(f"  {'--- Steam Out ---':^46}")
        print(f"  {'Temperature':<24} {st.T:>10.2f}  °F")
        print(f"  {'Enthalpy':<24} {st.h:>10.2f}  BTU/lb")
        print(f"  {'Condition':<24} {condition:>10}")
        print("-" * 50)
        print(f"  {'--- Performance ---':^46}")
        print(f"  {'Heat to make 1 lb steam':<24} {self.btu_for_1_lb:>10.2f}  BTU/lb steam")
        print(f"  {'Steam/Bagasse Ratio':<24} {self.steam_available_per_lb_bagasse:>10.3f}  lb/lb")
        print(f"  {'Steam Available from Bagasse':<24} {self.steam_availabe_lb_hr:>10,.1f}  lb/hr")
        print(f"Rated Steam Capacity: {self.capacity:,.0f}")
        print("=" * 50)


if __name__ == "__main__":
    # Test 1: Default boiler — saturated steam
    print("\nTEST 1: Default — saturated steam")
    b1 = Boiler(name='Boiler 1')
    b1.neat_display()

    # Test 2: Superheated steam
    print("\nTEST 2: Superheated +300°F")
    b2 = Boiler(pressure_psig=500, deg_superheat=400, feed_water_temp=230, efficiency=74, name='Boiler 2')
    b2.neat_display()

    # Test 3: Production boiler with real bagasse flowrate
    print("\nTEST 3: Production — 125,000 lb/hr bagasse")
    real_bagasse = Bagasse(moisture_pct=49.0, brix_pct=3.2, pol_pct=1.8, ash_pct=4.0, flowrate_lb_hr=100_000)
    b3 = Boiler(bagasse=real_bagasse, efficiency=62, pressure_psig=180, feed_water_temp=230, name='Boiler 3')
    b3.neat_display()
    real_bagasse.neat_display()

