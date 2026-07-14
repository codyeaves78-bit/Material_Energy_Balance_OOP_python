# condensate_utils: shared post-flash condensate helper. Condensate hotter
# than atmospheric partially flashes to vapor when let down to atmospheric
# pressure for return to the boiler feed system; this returns the liquid
# fraction that survives. Used by EvaporatorSet, the pan-floor balances, and
# JuiceHeatingStation to total "clean" (exhaust) vs "dirty" (V1-V4) return.

FLASH_TEMP_F = 212.0
H_FG_FLASH_BTU_LB = 970.0


def flash_condensate(flow_lb_per_hr: float, sat_temp_deg_F: float,
                      flash_temp_F: float = FLASH_TEMP_F,
                      h_fg_flash_btu_lb: float = H_FG_FLASH_BTU_LB) -> float:
    """Condensate flow (lb/hr) remaining as liquid after flashing to atmosphere."""
    if sat_temp_deg_F <= flash_temp_F:
        return flow_lb_per_hr
    flash = flow_lb_per_hr * (sat_temp_deg_F - flash_temp_F) / h_fg_flash_btu_lb
    return flow_lb_per_hr - flash
