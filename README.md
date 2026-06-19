# Multiple Effect Evaporator — Material & Energy Balance

Python OOP implementation of Harold Birkett's multiple-effect evaporator calculation method for raw sugar factories. Solves the simultaneous material and energy balance across any number of effects, with support for vapor bleeds, a pre-evaporator stage, and automatic pressure profile optimization using the Dessin heat transfer coefficient.

## Background

The solver iterates the inter-effect pressure profile until the U_calc / U_dessin ratio is uniform across all effects (Birkett criterion). Steam demand is solved by a secant method targeting the specified outlet brix. Boiling point elevation accounts for both dissolved solids (brix) and liquid head.

## Requirements

- Python 3.10+
- numpy
- iapws

```
pip install -r requirements.txt
```

## File Structure

| File | Description |
|---|---|
| `EvaporatorSet.py` | Orchestrates a multi-effect set — pressure profile iteration, steam convergence |
| `Evaporator.py` | Single Robert evaporator — energy balance, Dessin U, evaporation |
| `PreEvaporator.py` | Single pre-evaporator with fixed vapor bleed — iterates vapor pressure |
| `SugarStream.py` | Sugar juice stream object — brix, purity, flow, temperature, pressure |
| `SteamStream.py` | Steam / condensate stream object — uses IAPWS-97 for properties |
| `sugar_stream_properties.py` | Property correlations — BPE, latent heat, Cp, specific gravity |
| `evaporator_functions.py` | Engineering helpers — pressure conversions, shortcut steam estimate |
| `JuiceHeater.py` | Juice heater class (standalone, not part of evaporator set) |
| `EvaporationOOP_testing.py` | Regression test suite — 13 cases validated against reference outputs |

## Quick Start

```python
from SugarStream import SugarStream
from SteamStream import EvaporatorSteam
from EvaporatorSet import EvaporatorSet
from evaporator_functions import convert_psig_to_psia, convert_inHg_vacuum_to_psia

juice = SugarStream(brix=12, purity=90, flow_lb_per_hr=200_000, temp_deg_F=225,
                    pressure_psia=convert_psig_to_psia(20), level_ft=0)

steam = EvaporatorSteam(P_psia=convert_psig_to_psia(20), flow_lb_per_hr=0)

es = EvaporatorSet(
    juice_in=juice,
    supply_steam=steam,
    last_effect_pressure_psia=convert_inHg_vacuum_to_psia(26),
    target_brix_out=60,
    effect_areas_ft2=[4800, 4800, 4800],
    vapor_bleeds=[0, 0, 0],
    dessin_coefficient=18000,
    liquid_level_ft=2,
)

es.adjust_pressure_profile()
es.show_summary()
```

### With a pre-evaporator

```python
from PreEvaporator import PreEvaporator

juice_raw = SugarStream(brix=12, purity=90, flow_lb_per_hr=200_000, temp_deg_F=225,
                        pressure_psia=convert_psig_to_psia(20), level_ft=0)

pre = PreEvaporator(
    juice_in=juice_raw,
    supply_steam=EvaporatorSteam(P_psia=convert_psig_to_psia(20), flow_lb_per_hr=0),
    vapor_bleed_lb_per_hr=35_252,
    area_ft2=3300,
)

# pass pre.juice_out directly into the set
es = EvaporatorSet(juice_in=pre.juice_out, ...)
```

## Running the Tests

```
python EvaporationOOP_testing.py
```

Runs 13 cases (3-, 4-, and 5-effect sets with and without vapor bleeds and pre-evaporator) and compares results against reference outputs from the original functional program. All 13 cases pass within 0.01% tolerance.

## Units

| Quantity | Unit |
|---|---|
| Flow | lb/hr (tons/hr = flow / 2000) |
| Pressure | psia internally; psig / inHg vacuum for display |
| Temperature | deg F |
| Heat duty | BTU/hr |
| Heating surface | ft² |
| Brix | % (mass dissolved solids / total mass) |
