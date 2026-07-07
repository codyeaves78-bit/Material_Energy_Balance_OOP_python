# AuxillaryTurbines: solves the auxillary drive turbines (ID fans, pumps, etc.)
# from the input lists and a fiber rate, then reports them side by side in one
# table. Units with 0 HP/TFH are skipped in the display.

from Turbine import Turbine
from SteamStream import SteamStream


class AuxillaryTurbines:
    """
    Solves every auxillary drive turbine and holds the results.

    Inputs:
        name_list             : REQUIRED list of unit names, one entry per
                                turbine (e.g. ['123 ID Fan', '4 ID Fan', ...])
        hp_ton_fiber_hr       : list of HP per ton fiber per hour demand for
                                each unit, in the same order as name_list
                                (use 0 to leave a unit out of the display)
        isentropic_efficiency : list of turbine isentropic efficiencies in %
                                (e.g. 50 for 50%), equal in length to above
        live_steam_object     : SteamStream at live steam conditions
                                (e.g. SteamStream(P=180, x=1), P in psia, T in °F)
        exhaust_psia          : exhaust (back) pressure (psia)
        tons_fiber_hr         : fiber rate (ton fiber/hr) — sets each turbine's HP demand

    The class maps these into the auxillary_turbines dictionary internally.
    """

    def __init__(self, name_list, hp_ton_fiber_hr, isentropic_efficiency, live_steam_object, exhaust_psia, tons_fiber_hr):
        if len(name_list) != len(hp_ton_fiber_hr):
            raise ValueError(
                f"name_list has {len(name_list)} entries "
                f"but hp_ton_fiber_hr has {len(hp_ton_fiber_hr)} — they must match"
            )
        if len(isentropic_efficiency) != len(hp_ton_fiber_hr):
            raise ValueError(
                f"isentropic_efficiency has {len(isentropic_efficiency)} entries "
                f"but hp_ton_fiber_hr has {len(hp_ton_fiber_hr)} — they must match"
            )
        self.tons_fiber_hr = tons_fiber_hr

        # map the inputs into the auxillary turbine dictionary
        self.auxillary_turbines = {
            'name_list':             name_list,
            'hp_ton_fiber_hr':       hp_ton_fiber_hr,
            'isentropic_efficiency': isentropic_efficiency,
            'live_steam_object':     live_steam_object,
            'exhaust_psia':          exhaust_psia,
            'hp_list':               [hptf * tons_fiber_hr for hptf in hp_ton_fiber_hr],
        }

        # solve each turbine
        self.turbines = []
        for i in range(len(self.auxillary_turbines['hp_list'])):
            trb = Turbine(
                inlet_steam=self.auxillary_turbines['live_steam_object'],
                outlet_pressure_psia=self.auxillary_turbines['exhaust_psia'],
                isentropic_efficiency=self.auxillary_turbines['isentropic_efficiency'][i] / 100,  # get % to decimal form
                hp_demand=self.auxillary_turbines['hp_list'][i],
                name=self.auxillary_turbines['name_list'][i],
            )
            self.turbines.append(trb)

    # ------------------------------------------------------------------
    # Totals
    # ------------------------------------------------------------------

    @property
    def total_hp(self):
        return sum(trb.hp_demand for trb in self.turbines)

    @property
    def total_inlet_flow_lb_hr(self):
        return sum(trb.steam_flow_lb_hr for trb in self.turbines)

    @property
    def total_exhaust_available_lb_hr(self):
        return sum(trb.exhaust_available for trb in self.turbines)

    def __repr__(self):
        return (
            f"AuxillaryTurbines({len(self.turbines)} units, "
            f"{self.tons_fiber_hr:,.0f} ton fiber/hr, "
            f"total HP={self.total_hp:,.0f})"
        )

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def display_auxillary_turbine_information(self):
        def fmt_x(x):
            return "Superheat" if x is None or x >= 1.0 else f"{x:.4f}"

        # size the name column to the longest name in service
        C0 = max([12] + [len(trb.name) for trb in self.turbines])
        C1, C2, C3, C4, C5, C6, C7, C8, C9, C10 = 12, 13, 9, 8, 10, 8, 8, 8, 8, 9
        widths = (C0, C1, C2, C3, C4, C5, C6, C7, C8, C9, C10)
        sep = "-+-".join("-" * w for w in widths)
        W   = len(sep)
        div = "=" * W

        hdr1 = (f"{'':^{C0}} | {'Inlet Flow':^{C1}} | {'Exhaust Avail':^{C2}} | "
                f"{'HP':^{C3}} | {'HP/TFH':^{C4}} | {'Steam Rate':^{C5}} | "
                f"{'Inlet':^{C6}} | {'Inlet':^{C7}} | "
                f"{'Outlet':^{C8}} | {'Outlet':^{C9}} | {'Outlet':^{C10}}")
        hdr2 = (f"{'Unit':^{C0}} | {'lb/hr':^{C1}} | {'lb/hr':^{C2}} | "
                f"{'':^{C3}} | {'':^{C4}} | {'lb/HP-hr':^{C5}} | "
                f"{'psia':^{C6}} | {'temp °F':^{C7}} | "
                f"{'psia':^{C8}} | {'temp °F':^{C9}} | {'quality':^{C10}}")

        print(div)
        print(f"AUXILLARY TURBINES  —  {self.tons_fiber_hr:,.0f} TON FIBER/HR".center(W))
        print(div)
        print(hdr1)
        print(hdr2)
        print(sep)

        for i, trb in enumerate(self.turbines):
            if self.auxillary_turbines['hp_ton_fiber_hr'][i] == 0:
                continue  # unit not in service, leave it out of the table
            exhaust = trb.exhaust_steam
            print(f"{trb.name:>{C0}} | {trb.steam_flow_lb_hr:>{C1},.0f} | {trb.exhaust_available:>{C2},.0f} | "
                  f"{trb.hp_demand:>{C3},.0f} | {self.auxillary_turbines['hp_ton_fiber_hr'][i]:>{C4},.1f} | "
                  f"{trb.steam_rate:>{C5},.2f} | "
                  f"{trb.inlet_steam.P:>{C6},.1f} | {trb.inlet_steam.T:>{C7},.1f} | "
                  f"{exhaust.P:>{C8},.1f} | {exhaust.T:>{C9},.1f} | {fmt_x(exhaust.x):^{C10}}")

        print(sep)
        print(f"{'TOTAL':>{C0}} | {self.total_inlet_flow_lb_hr:>{C1},.0f} | {self.total_exhaust_available_lb_hr:>{C2},.0f} | "
              f"{self.total_hp:>{C3},.0f} | {sum(self.auxillary_turbines['hp_ton_fiber_hr']):>{C4},.1f} | "
              f"{self.total_inlet_flow_lb_hr / self.total_hp:>{C5},.2f} | "
              f"{'':^{C6}} | {'':^{C7}} | {'':^{C8}} | {'':^{C9}} | {'':^{C10}}")
        print(div)


if __name__ == "__main__":
    aux = AuxillaryTurbines(
        name_list=['123 ID Fan', '4 ID Fan', 'Boiler Feed Pump', 'Injection Pump'],
        hp_ton_fiber_hr=[12, 8, 10, 0],              # hp per ton fiber hr demand for each unit, same order as name_list
        isentropic_efficiency=[50, 50, 50, 50],      # %, must be equal in length to above list
        live_steam_object=SteamStream(P=180, x=1),   # P in psia, T in deg F
        exhaust_psia=30,                             # psia
        tons_fiber_hr=112,                           # ton fiber per hour at 18000 tpd and 15% fiber
    )
    print(aux)
    print()
    aux.display_auxillary_turbine_information()
