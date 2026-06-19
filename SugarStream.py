# Oject SugarStream calculates properties and updates them based on the file sugar_stream_properties.py

import numpy as np
from sugar_stream_properties import bpe_brix, bpe_head, sat_steam_temp, bpe_total, get_latent_heat, get_cp, specific_gravity

class SugarStream:
    _count = 0
    """Class to represent the sugar stream, it will calculate properties based on the input parameters and update them as needed"""
    def __init__(self, brix=0, purity=0, flow_lb_per_hr=0, temp_deg_F=90, pressure_psia=14.7, level_ft=0):
        """Initialize the sugar stream with the given parameters, and calculate properties"""
        SugarStream._count += 1
        self.stream_id = SugarStream._count
        self.brix = brix
        self.purity = purity
        self.flow_lb_per_hr = flow_lb_per_hr
        self.temp_deg_F = temp_deg_F
        self.pressure_psia = pressure_psia
        self.level_ft = level_ft
    
    @property
    def pol(self):
        return self.purity * self.brix / 100 if self.brix > 0 and self.purity > 0 else 0
    
    @property
    def boiling_point_elevation_deg_F(self):
        return bpe_total(self.level_ft, self.brix, self.pressure_psia) if self.brix > 0 else 0
    
    @property
    def cp_btu_per_lb_deg_F(self):
        return get_cp(self.brix) if self.brix > 0 else 1
    
    @property
    def specific_gravity(self):
        return specific_gravity(self.brix) if self.brix > 0 else 1
    
    @property
    def latent_heat_btu_per_lb(self):
        return get_latent_heat(self.pressure_psia) if self.pressure_psia > 0 else 0
    
    @property
    def vapor_saturation_temp_deg_F(self):
        return sat_steam_temp(self.pressure_psia) if self.pressure_psia > 0 else 0
       
    def current_temp_to_bpe_plus_vapor_temp(self):
        """Sets the current temp to the vapor boiling temp + boiling point elevation, useful in evaporator calculations"""
        self.temp_deg_F = self.vapor_saturation_temp_deg_F + self.boiling_point_elevation_deg_F

    def properties(self) -> dict:
        cls = type(self)
        prop_names = [k for k, v in vars(cls).items() if isinstance(v, property)]
        instance_vars = vars(self)
        return {**instance_vars, **{k: getattr(self, k) for k in prop_names}}
    
    def __repr__(self):
        return (f"SugarStream(brix={self.brix:.2f}, purity={self.purity:.2f}, "
                f"flow={self.flow_lb_per_hr:,.2f} lb/hr, temp={self.temp_deg_F:.2f}°F, "
                f"pressure={self.pressure_psia:.2f} psia, level={self.level_ft:.1f} ft)")
    
    def display_properties(self):
        """Display the properties of the sugar stream in a readable format"""
        props = self.properties()
        for key, value in props.items():
            print(f"{key}: {value:,.2f}")
    
    @classmethod
    def copy(cls, stream: 'SugarStream', **overrides):
        """Create a copy of the stream with optional overrides for any properties"""
        params = {
            'brix': stream.brix,
            'purity': stream.purity,
            'flow_lb_per_hr': stream.flow_lb_per_hr,
            'temp_deg_F': stream.temp_deg_F,
            'pressure_psia': stream.pressure_psia,
            'level_ft': stream.level_ft
        }
        params.update(overrides)
        return cls(**params)

if __name__ == "__main__":
    # Example usage
    my_stream = SugarStream(brix=14, purity=90, flow_lb_per_hr=1_500_000, temp_deg_F=235, pressure_psia=50, level_ft=2)
    my_stream.display_properties()
    print(f'\n')
    my_stream.pressure_psia = 10
    my_stream.display_properties()
    