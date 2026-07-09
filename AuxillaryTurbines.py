# AuxillaryTurbines: solves the auxillary drive turbines (ID fans, pumps, etc.)
# from the input lists, then reports them side by side in one table.
# Units with 0 HP are skipped in the display.

from Turbine import Turbine
from SteamStream import SteamStream


class AuxillaryTurbines:
    """
    Solves every auxillary drive turbine and holds the results.

    Inputs:
        name_list             : REQUIRED list of unit names, one entry per
                                turbine (e.g. ['123 ID Fan', '4 ID Fan', ...])
        hp_list               : list of HP demand for each unit, in the same
                                order as name_list
                                (use 0 to leave a unit out of the display)
        isentropic_efficiency : list of turbine isentropic efficiencies in %
                                (e.g. 50 for 50%), equal in length to above
        live_steam_object     : SteamStream at live steam conditions
                                (e.g. SteamStream(P=180, x=1), P in psia, T in °F)
        exhaust_psia          : exhaust (back) pressure (psia)

    The class maps these into the auxillary_turbines dictionary internally.
    """

    def __init__(self, group_name, name_list, hp_list, isentropic_efficiency, live_steam_object, exhaust_psia):
        if len(name_list) != len(hp_list):
            raise ValueError(
                f"name_list has {len(name_list)} entries "
                f"but hp_list has {len(hp_list)} — they must match"
            )
        if len(isentropic_efficiency) != len(hp_list):
            raise ValueError(
                f"isentropic_efficiency has {len(isentropic_efficiency)} entries "
                f"but hp_list has {len(hp_list)} — they must match"
            )

        # Define turbine group name
        self.group_name = group_name

        # map the inputs into the auxillary turbine dictionary
        self.auxillary_turbines = {
            'name_list':             name_list,
            'isentropic_efficiency': isentropic_efficiency,
            'live_steam_object':     live_steam_object,
            'exhaust_psia':          exhaust_psia,
            'hp_list':               hp_list,
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
            f"total HP={self.total_hp:,.0f})"
        )

    # ------------------------------------------------------------------
    # Display
    # ------------------------------------------------------------------

    def generate_pfd(self, show=True, save_path=None, include_table=True):
        """Generate a process flow diagram with the turbine table. Returns the Figure."""
        from turbine_diagram import plot_turbine_group
        return plot_turbine_group(self, show=show, save_path=save_path,
                                  include_table=include_table)

    def to_excel(self, workbook):
        """Write this turbine group to its own styled sheet (PFD + tables)."""
        from turbine_diagram import group_to_excel
        return group_to_excel(self, workbook)

    def neat_display(self):
        def fmt_x(x):
            return "Superheat" if x is None or x >= 1.0 else f"{x:.4f}"

        # size the name column to the longest name in service
        C0 = max([12] + [len(trb.name) for trb in self.turbines])
        C1, C2, C3, C4, C5, C6, C7, C8, C9 = 12, 13, 9, 10, 8, 8, 8, 8, 9
        widths = (C0, C1, C2, C3, C4, C5, C6, C7, C8, C9)
        sep = "-+-".join("-" * w for w in widths)
        W   = len(sep)
        div = "=" * W

        hdr1 = (f"{'':^{C0}} | {'Inlet Flow':^{C1}} | {'Exhaust Avail':^{C2}} | "
                f"{'HP':^{C3}} | {'Steam Rate':^{C4}} | "
                f"{'Inlet':^{C5}} | {'Inlet':^{C6}} | "
                f"{'Outlet':^{C7}} | {'Outlet':^{C8}} | {'Outlet':^{C9}}")
        hdr2 = (f"{'Unit':^{C0}} | {'lb/hr':^{C1}} | {'lb/hr':^{C2}} | "
                f"{'':^{C3}} | {'lb/HP-hr':^{C4}} | "
                f"{'psia':^{C5}} | {'temp °F':^{C6}} | "
                f"{'psia':^{C7}} | {'temp °F':^{C8}} | {'quality':^{C9}}")

        print(div)
        print(f"{self.group_name}".center(W))
        print(div)
        print(hdr1)
        print(hdr2)
        print(sep)

        for i, trb in enumerate(self.turbines):
            if self.auxillary_turbines['hp_list'][i] == 0:
                continue  # unit not in service, leave it out of the table
            exhaust = trb.exhaust_steam
            print(f"{trb.name:>{C0}} | {trb.steam_flow_lb_hr:>{C1},.0f} | {trb.exhaust_available:>{C2},.0f} | "
                  f"{trb.hp_demand:>{C3},.0f} | "
                  f"{trb.steam_rate:>{C4},.2f} | "
                  f"{trb.inlet_steam.P:>{C5},.1f} | {trb.inlet_steam.T:>{C6},.1f} | "
                  f"{exhaust.P:>{C7},.1f} | {exhaust.T:>{C8},.1f} | {fmt_x(exhaust.x):^{C9}}")

        print(sep)
        print(f"{'TOTAL':>{C0}} | {self.total_inlet_flow_lb_hr:>{C1},.0f} | {self.total_exhaust_available_lb_hr:>{C2},.0f} | "
              f"{self.total_hp:>{C3},.0f} | "
              f"{self.total_inlet_flow_lb_hr / self.total_hp:>{C4},.2f} | "
              f"{'':^{C5}} | {'':^{C6}} | {'':^{C7}} | {'':^{C8}} | {'':^{C9}}")
        print(div)


if __name__ == "__main__":
    from excel_export import new_workbook
    aux = AuxillaryTurbines(
        group_name='ID Fan Turbines',
        name_list=['123 ID Fan', '4 ID Fan', '5 ID Fan', '6 ID Fan', '7 ID Fan', '8 ID Fan'],
        hp_list=[750, 235, 400, 795, 1200, 1300],    # HP demand for each unit, same order as name_list
        isentropic_efficiency=[50, 50, 50, 50, 50, 50],      # %, must be equal in length to above list
        live_steam_object=SteamStream(P=190, x=1),   # P in psia, T in deg F
        exhaust_psia=32,                             # psia
    )
    print(aux)
    print()
    aux.neat_display()
    wb = new_workbook()
    aux.to_excel(wb)
    wb.save(filename='aux_turbines.xlsx')
    print('Saved excel workbook as aux_turbine.xlsx')

# for your main script, you can finish up with these fd_hp_list = [233, 350] names ['7 FD Fan', '8 FD Fan']
# then these [400, 400, 400, 400] and the names ['boiler_feed_water_1', 'boiler_feed_water_2', 'boiler_feed_water_3', 'juice_pump']