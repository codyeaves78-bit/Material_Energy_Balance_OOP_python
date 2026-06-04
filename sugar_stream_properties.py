# basic functions to call for the SugarStream object

import numpy as np

# building my functions to call
def bpe_brix(brix):
  """ bpe from brix alone"""
  bpe = 4.266667 * brix / (100 - brix)
  return bpe

def bpe_head(lvl, brix, t_vap):
  """ bpe from head, level in ft"""
  brix_poly = (
      0.99991
      + 0.0038008 * brix
      + 0.000012662 * (brix**2)
      + 0.00000009596 * (brix**3)
  )

  temp_poly = (
      5.314
      - 0.07135 * t_vap
      + 0.00033908 * (t_vap**2)
      - 0.00000055728 * (t_vap**3)
  )

  bpe_calc = lvl * 6 * brix_poly * temp_poly
  if bpe_calc <1:
    bpe_calc = 1
  return bpe_calc

def sat_steam_temp(p_psia):
    """saturation steam temperature, I use this over IAPWS97 for speed"""
    """Only for pressure 1-60 psia"""
    A = 6.239238
    B = 2988.801361
    C = 377.305590
    temp = B / (A - np.log10(p_psia)) - C
    return temp

def bpe_total(lvl, brix, p_vap_psia):
   """bpe total, combine previous functions, lvl in ft"""
   t_vap = sat_steam_temp(p_vap_psia)
   bpe1 = bpe_brix(brix)
   bpe2 = bpe_head(lvl, brix, t_vap) # lvl in ft
   bpe_total = bpe1 + bpe2
   return bpe_total

def get_latent_heat(p_psia):
    """gets the latent heat of the steam or liquid"""
    # only for psia 1 to 60
    # this is much much faster but very slightly less accurate than using IAPWS97
    # Calculate the polynomial
    temp = sat_steam_temp(p_psia)
    h_fg = -0.00000152231563 * temp**3 + .000504774867 * temp**2 - 0.634291695987 * temp + 1096.29
    return h_fg

def get_cp(brix):
  """gets the specific heat capacity"""
  cp = 0.9964 - 0.005656 * brix
  return cp

def specific_gravity(brix): 
    """gets the specific gravity of the sugar solution, only for 68 deg F, but good enough for our purposes"""
    sg = (
       62.2511
       + 0.24081 * brix
       + 0.0007902404 * brix**2
       + 0.00000423954  * brix**3
       - 0.00000001657193 * brix**4
        ) / 62.4
    return sg