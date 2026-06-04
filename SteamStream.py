# This holds the settings for the SteamStream class object
from iapws import IAPWS97
import numpy as np
from sugar_stream_properties import sat_steam_temp, get_latent_heat
import time

class SteamStream:
    """Class to represent the steam streams of the factory, built for highest accuracy, do not use for trial and error calculations"""
    _count = 0

    def __init__(self, T=None, P=None, h=None, s=None, x=None, flow_lb_per_hr=0):
        """
        Pass any 2 parameters in English units:
        T = temperature (°F)
        P = pressure (psia)
        h = enthalpy (BTU/lb)
        s = entropy (BTU/lb·°R)
        x = quality (0-1, dimensionless)
        flow_lb_per_hr = mass flow rate (lb/hr)
        """
        SteamStream._count += 1
        self.stream_id = SteamStream._count
        self.flow_lb_per_hr = flow_lb_per_hr
        self._defining_params = {'T': T, 'P': P, 'h': h, 's': s, 'x': x}  # store originals
        self._state = self._build_state(T, P, h, s, x)
    
    def _build_state(self, T=None, P=None, h=None, s=None, x=None):
        # convert inputs to SI for IAPWS97
        kwargs = {}
        if T is not None: kwargs['T'] = (T - 32) * 5/9 + 273.15  # °F → K
        if P is not None: kwargs['P'] = P * 0.00689476           # psia → MPa
        if h is not None: kwargs['h'] = h * 2.326                # BTU/lb → kJ/kg
        if s is not None: kwargs['s'] = s * 4.1868               # BTU/lb·°R → kJ/kg·K
        if x is not None: kwargs['x'] = x                        # dimensionless
        return IAPWS97(**kwargs)

    def update(self, T=None, P=None, h=None, s=None, x=None):
        """Update the state with any 2 parameters in English units"""
        self._state = self._build_state(T, P, h, s, x)

    @property
    def T(self):
        """Temperature °F"""
        return (self._state.T - 273.15) * 9/5 + 32

    @property
    def P(self):
        """Pressure psia"""
        return self._state.P / 0.00689476

    @property
    def h(self):
        """Enthalpy BTU/lb"""
        return self._state.h / 2.326

    @property
    def s(self):
        """Entropy BTU/lb·°R"""
        return self._state.s / 4.1868

    @property
    def x(self):
        """Quality 0-1"""
        return self._state.x

    @property
    def v(self):
        """Specific volume ft³/lb"""
        return self._state.v * 16.0185  # m³/kg → ft³/lb

    @property
    def rho(self):
        """Density lb/ft³"""
        return 1 / self.v

    @property
    def h_fg(self):
        """Latent heat BTU/lb"""
        sat_liq = IAPWS97(P=self._state.P, x=0)
        sat_vap = IAPWS97(P=self._state.P, x=1)
        return (sat_vap.h - sat_liq.h) / 2.326
    
    @property
    def is_superheater(self):
        """Check if the steam is superheated (x=1 and T > saturation temp)"""
        sat_temp_kelvin = IAPWS97(P=self._state.P, x=1).T
        sat_temp = (sat_temp_kelvin - 273.15) * 9/5 + 32 # conversion to °F
        if self.T > (sat_temp + .01): # add small tolerance
            msg = (f"YES! Steam is superheated. T={self.T:.2f} °F > saturation temp {sat_temp:.2f} °F at P={self.P:.2f} psia.")
        else:
            msg = (f"NO! Steam is not superheated. T={self.T:.2f} °F <= saturation temp {sat_temp:.2f} °F at P={self.P:.2f} psia.")
        return msg

    def __repr__(self):
        return (f"SteamStream(T={self.T:.2f}°F, P={self.P:.2f} psia, "
                f"h={self.h:.2f} BTU/lb, x={self.x})")
    
    def properties(self) -> dict:
        cls = type(self)
        prop_names = [k for k, v in vars(cls).items() if isinstance(v, property)]
        instance_vars = {k: v for k, v in vars(self).items() if not k.startswith('_')}
        return {**instance_vars, **{k: getattr(self, k) for k in prop_names}}
    
    def display_properties(self):
        props = self.properties()
        print("Units: T(°F), P(psia), h(BTU/lb), s(BTU/lb·°R), v(ft³/lb), rho(lb/ft³), h_fg(BTU/lb)")
        for key, value in props.items():
            formatted = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
            print(f"{key}: {formatted}")
    
# Below are some test cases, I will wrap in triple quotes to avoid running every time, unwrap to test
"""  
my_steam = SteamStream(T=400, P=50, flow_lb_per_hr=1000)
my_steam.display_properties()
print("\n making exhaust steam now...   ")
exhaust_steam = SteamStream(P=30, x=1, flow_lb_per_hr=1000)
exhaust_steam.display_properties()
print("\n making exhaust steam super heated now...   ")
exhaust_steam.update(P=30, T=400)
exhaust_steam.display_properties()
print("\n now sat mix steam at 30 psia...   ")
exhaust_steam.update(P=30, x=0.5)
exhaust_steam.display_properties()
print("\n sat liquid...   ")
exhaust_steam.update(P=30, x=0)
exhaust_steam.display_properties()
print("\n subcooled liquid...   ")
exhaust_steam.update(P=30, T=200)  # Example subcooled temperature
exhaust_steam.display_properties()
"""  

class EvaporatorSteam:
    """A simpler steam stream class specifically for evaporator trial and error calculations, built for speed"""
    def __init__(self, P_psia=14.7, flow_lb_per_hr=0):
        self.P_psia = P_psia
        self.flow_lb_per_hr = flow_lb_per_hr

    @property
    def sat_temp_deg_F(self):
        return sat_steam_temp(self.P_psia)
    
    @property
    def h_fg(self):
        return get_latent_heat(self.P_psia)
    
    def __repr__(self):
        return (f"EvaporatorSteam(P_psia={self.P_psia:.2f}, flow_lb_per_hr={self.flow_lb_per_hr:,.2f})")
    
    def properties(self) -> dict:
        cls = type(self)
        prop_names = [k for k, v in vars(cls).items() if isinstance(v, property)]
        instance_vars = {k: v for k, v in vars(self).items() if not k.startswith('_')}
        return {**instance_vars, **{k: getattr(self, k) for k in prop_names}}
    
    def display_properties(self):
        props = self.properties()
        print("Units: T(°F), P(psia), h_fg(BTU/lb)")
        for key, value in props.items():
            formatted = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
            print(f"{key}: {formatted}")

#Test case for EvaporatorSteam
"""
evap_steam = EvaporatorSteam(P_psia=30, flow_lb_per_hr=1000)
evap_steam.display_properties()
print("\n changing pressure to 8 psia...   ")
evap_steam.P_psia = 8
evap_steam.display_properties()
"""

# now to show the time difference between this and the full IAPWS97 steam stream

"""
start_time_simple = time.time()
evap_steam = EvaporatorSteam(P_psia=30, flow_lb_per_hr=1000)
evap_steam.display_properties()
end_time_simple = time.time()
simple_time = end_time_simple - start_time_simple
print(f"\n EvaporatorSteam calculation took {simple_time:.6f} seconds.")
print("\n Now testing full IAPWS97 SteamStream...   ")
start_time_full = time.time()
full_steam = SteamStream(P=30, x=1, flow_lb_per_hr=1000)
full_steam.display_properties()
end_time_full = time.time()
full_time = end_time_full - start_time_full
print(f"\n Full IAPWS97 SteamStream calculation took {full_time:.6f} seconds.")
difference = full_time - simple_time
print(f"\n The full IAPWS97 SteamStream is {difference:.6f} seconds slower than the simpler EvaporatorSteam, which takes {difference/simple_time:.2f} times longer for calculation time.")
"""