# script to control the Juice Heater Objects
from SugarStream import SugarStream
from SteamStream import SteamStream
import numpy as np

class JuiceHeaterShellTube:
    """Class to represent shell and tube juice heater"""
    def __init__(self, cold_stream: SugarStream, hot_stream: SteamStream, juice_out_temp_degF=220, U_btu_per_ft2_degF=220, installed_area_ft2=22000):
        self.U = U_btu_per_ft2_degF
        self.cold_stream = cold_stream
        self.hot_stream = hot_stream
        self.juice_out_temp_degF = juice_out_temp_degF
        self.installed_area_ft2 = installed_area_ft2
    
    @property
    def cold_delta_T(self):
        """juice temp rise"""
        return self.juice_out_temp_degF - self.cold_stream.temp_deg_F
    
    @property
    def Q_btu_per_hr(self):
        """Calculate the heat transfer rate in BTU/hr"""
        return self.cold_stream.flow_lb_per_hr * self.cold_stream.cp_btu_per_lb_deg_F * self.cold_delta_T
    
    @property
    def LMTD_degF(self):
        """Calculate the log mean temperature difference in °F"""
        delta_T1 = self.hot_stream.T - self.cold_stream.temp_deg_F
        delta_T2 = self.hot_stream.T - self.juice_out_temp_degF
        if delta_T1 == delta_T2:
            return delta_T1  # Avoid division by zero, LMTD is just the temperature difference
        else:
            return (delta_T1 - delta_T2) / np.log(delta_T1 / delta_T2)
    
    @property
    def required_area_ft2(self):
        """Calculate the required heat transfer area in ft²"""
        return self.Q_btu_per_hr / (self.U * self.LMTD_degF)
    
    @property
    def steam_required_lb_per_hr(self):
        """Calculate the required steam flow rate in lb/hr"""
        steam_req = self.Q_btu_per_hr / self.hot_stream.h_fg
        return steam_req
    
    @property
    def is_steam_hot_enough(self):
        """Check if the steam is hot enough to achieve the desired juice out temperature"""
        if self.hot_stream.T <= self.juice_out_temp_degF:
            msg = (f"NO! Steam temp ({self.hot_stream.T:.2f} °F) <= juice out temperature ({self.juice_out_temp_degF} °F).")
        else:
            msg = "YES"
        return msg
    
    def properties(self) -> dict:
        cls = type(self)
        prop_names = [k for k, v in vars(cls).items() if isinstance(v, property)]
        instance_vars = {k: v for k, v in vars(self).items() if not k.startswith('_')}
        return {**instance_vars, **{k: getattr(self, k) for k in prop_names}}
    
    def display_properties(self):
        """Display the properties of the juice heater in a readable format"""
        props = self.properties()
        for key, value in props.items():
            formatted = f"{value:,.2f}" if isinstance(value, (int, float)) else str(value)
            print(f"{key}: {formatted}")
