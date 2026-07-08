class CoolingTower:
    "A very lightweight simple cooling tower calculation object"
    def __init__(self, hot_water_temp, hot_water_lb_hr, cool_water_temp, percent_blowdown):
        self.hot_water_temp = hot_water_temp
        self.hot_water_lb_hr = hot_water_lb_hr
        self.cool_water_temp = cool_water_temp
        self.perc_bd = percent_blowdown

    @property
    def blowdown_lb_hr(self):
        return self.hot_water_lb_hr * self.perc_bd / 100
    
    @property
    def blowdown_gpm(self):
        return self.blowdown_lb_hr / 60 / 8.3 # simple

    @property
    def water_to_tower(self):
        return self.hot_water_lb_hr - self.blowdown_lb_hr

    @property
    def evaporated(self):
        """cp = 1"""
        heat_to_cool = self.water_to_tower * (self.hot_water_temp - self.cool_water_temp)
        return heat_to_cool / 1000 # about 1000 btu / lb evaporated

    @property
    def cool_water_lb_hr(self):
        return self.water_to_tower - self.evaporated
    
    @property
    def cool_water_gpm(self):
        return self.cool_water_lb_hr / 60 / 8.3 # simple
    
    # need to include condenser to calculate makeup flowrate

