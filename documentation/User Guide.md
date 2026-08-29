# Cane Sugar Factory Material and Energy Balance (Python OOP) — User Guide

Each class can stand alone and run calculations, provided you've cloned the repo and installed the requirements.

The general import format is `from XXX import XXX` — the filename and class name are usually identical:

```python
from SugarStream import SugarStream
```

There are some exceptions, where the class name differs from the filename:

```python
from SteamStream import EvaporatorSteam
```

Until the worked examples are finished, the best reference for everything is `main.py`.

---

## Foundations

Four classes make up the foundation everything else is built on: `SugarStream` and `SteamStream`/`EvaporatorSteam` for streams, and `Massecuite` for pan work. Learn these and the equipment classes read easily, since they're mostly assemblies of streams.

- **`SugarStream`** — any water–sugar–non-sugar mixture (juice, syrup, molasses, massecuite, magma).
- **`SteamStream`** — high-accuracy steam/water, wraps IAPWS97. Use when you want precision.
- **`EvaporatorSteam`** — fast steam properties from correlations. Use for trial-and-error loops.
- **`Massecuite`** — boiling-point rise, crystal content, and temperature solves for vacuum pans and crystallizers.

---

## SugarStream

`SugarStream` covers every water–sugar–non-sugar mixture in the factory: juice, syrup, molasses, massecuite, and magma. There is a dedicated `Massecuite` class for pan material and energy balances, but `SugarStream` gives you the basic properties engineers typically look for.

```python
>>> from SugarStream import SugarStream
>>> my_stream = SugarStream(brix=14, purity=90, flow_lb_per_hr=100, temp_deg_F=225, pressure_psia=50, level_ft=2)
>>> my_stream.display_properties()
stream_id: 2.00
brix: 14.00
purity: 90.00
flow_lb_per_hr: 100.00
temp_deg_F: 225.00
pressure_psia: 50.00
level_ft: 2.00
pol: 12.60
boiling_point_elevation_deg_F: 1.69
cp_btu_per_lb_deg_F: 0.92
specific_gravity: 1.05
cu_ft_hr: 1.52
latent_heat_btu_per_lb: 924.15
vapor_saturation_temp_deg_F: 280.98
solids_flow: 14.00
pol_flow: 12.60
```

You can change a property, such as brix, and the dependent properties recalculate:

```python
>>> my_stream.brix = 95
>>> my_stream.display_properties()
stream_id: 2.00
brix: 95.00
purity: 90.00
flow_lb_per_hr: 100.00
temp_deg_F: 225.00
pressure_psia: 50.00
level_ft: 2.00
pol: 85.50
boiling_point_elevation_deg_F: 82.07
cp_btu_per_lb_deg_F: 0.46
specific_gravity: 1.52
cu_ft_hr: 1.06
latent_heat_btu_per_lb: 924.15
vapor_saturation_temp_deg_F: 280.98
solids_flow: 95.00
pol_flow: 85.50
```

Note how the dependent properties changed — `pol`, `solids_flow`, `pol_flow`, and others. Keep that in mind when running your own calculations.

You can also return the properties as a dictionary:

```python
>>> my_stream.brix = 65  # note that I changed brix here
>>> my_stream.properties()
{'stream_id': 2, 'brix': 65, 'purity': 90, 'flow_lb_per_hr': 100, 'temp_deg_F': 225, 'pressure_psia': 50, 'level_ft': 2, 'pol': 58.5, 'boiling_point_elevation_deg_F': 8.923810142857143, 'cp_btu_per_lb_deg_F': 0.62876, 'specific_gravity': 1.3158810906176885, 'cu_ft_hr': 1.2178639194608702, 'latent_heat_btu_per_lb': np.float64(924.1472739021877), 'vapor_saturation_temp_deg_F': np.float64(280.9818423397531), 'solids_flow': 65.0, 'pol_flow': 58.5}
```

### Helper methods

Beyond reading and setting properties, `SugarStream` has a few methods that handle common factory transformations.

**`evaporate(new_brix, new_temp)`** — transforms the stream in place to a new brix, conserving solids and recomputing the flow. Handy for turning clarified juice into syrup for pan-floor calcs. Purity is unchanged (evaporation removes only water):

```python
>>> cj = SugarStream(brix=14, purity=90, flow_lb_per_hr=1_500_000, temp_deg_F=210)
>>> cj.evaporate(new_brix=65, new_temp=140)
>>> repr(cj)
'SugarStream(brix=65.00, purity=90.00, flow=323,076.92 lb/hr, temp=140.00°F, pressure=14.70 psia, level=0.0 ft)'
>>> cj.solids_flow          # solids conserved: 14% of 1,500,000 = 210,000
210000.0
```

**`copy(stream, **overrides)`** — a classmethod that clones a stream, optionally overriding any parameter. Useful for branching a stream without disturbing the original:

```python
>>> syrup2 = SugarStream.copy(cj, brix=68, purity=88)
>>> repr(syrup2)
'SugarStream(brix=68.00, purity=88.00, flow=323,076.92 lb/hr, temp=140.00°F, pressure=14.70 psia, level=0.0 ft)'
```

**`current_temp_to_bpe_plus_vapor_temp()`** — sets the stream's temperature to its vapor saturation temperature plus boiling-point elevation, i.e. the temperature it would actually boil at given its pressure and brix. Convenient inside evaporator calculations:

```python
>>> v = SugarStream(brix=60, purity=85, flow_lb_per_hr=100_000, pressure_psia=10, level_ft=1)
>>> v.current_temp_to_bpe_plus_vapor_temp()
>>> round(v.temp_deg_F, 2)   # sat 193.16 °F + bpe 7.70 °F
200.86
```

---

## SteamStream and EvaporatorSteam

Two steam classes, for two different needs. `SteamStream` wraps IAPWS97 for accuracy; `EvaporatorSteam` uses fast correlations for speed inside iterative loops. Pick based on whether you're after precision or throughput.

### SteamStream

`SteamStream` is a powerful, highly accurate class that wraps the IAPWS97 object from `iapws` in unit conversions, so you can use it the same way you'd use IAPWS97 directly — but in US customary units. Give it any two inputs that IAPWS97 accepts:

```python
>>> from SteamStream import SteamStream
>>> my_steam = SteamStream(T=350, P=50)  # any 2 inputs that work with IAPWS97 work here
>>> my_steam.properties()
{'stream_id': 1,
 'flow_lb_per_hr': 0,
 'T': 349.9999999999999,
 'P': 50.0,
 'h': np.float64(1210.2039776365916),
 's': np.float64(1.705277415909871),
 'x': 1,
 'v': np.float64(9.427310020194167),
 'rho': np.float64(0.10607479735554552),
 'h_fg': np.float64(924.0066546909492),
 'is_superheated': 'YES! Steam is superheated. T=350.00 °F > saturation temp 280.99 °F at P=50.00 psia.'}
```

`properties()` gives you a dictionary to do what you wish with. For a cleaner display — including a units legend — use `display_properties()`:

```python
>>> my_steam.display_properties()
Units: T(°F), P(psia), h(BTU/lb), s(BTU/lb·°R), v(ft³/lb), rho(lb/ft³), h_fg(BTU/lb)
stream_id: 1.00
flow_lb_per_hr: 0.00
T: 350.00
P: 50.00
h: 1,210.20
s: 1.71
x: 1.00
v: 9.43
rho: 0.11
h_fg: 924.01
is_superheated: YES! Steam is superheated. T=350.00 °F > saturation temp 280.99 °F at P=50.00 psia.
```

You can specify a flow when constructing the object:

```python
>>> my_other_steam = SteamStream(x=1, P=500, flow_lb_per_hr=1000)
>>> my_other_steam.display_properties()
Units: T(°F), P(psia), h(BTU/lb), s(BTU/lb·°R), v(ft³/lb), rho(lb/ft³), h_fg(BTU/lb)
stream_id: 2.00
flow_lb_per_hr: 1,000.00
T: 467.05
P: 500.00
h: 1,205.02
s: 1.46
x: 1.00
v: 0.93
rho: 1.08
h_fg: 755.48
is_superheated: NO! Steam is not superheated. T=467.05 °F <= saturation temp 467.05 °F at P=500.00 psia.
```

Flow can be set directly:

```python
>>> my_other_steam.flow_lb_per_hr = 2000
>>> my_other_steam.display_properties()
Units: T(°F), P(psia), h(BTU/lb), s(BTU/lb·°R), v(ft³/lb), rho(lb/ft³), h_fg(BTU/lb)
stream_id: 2.00
flow_lb_per_hr: 2,000.00
T: 467.05
P: 500.00
h: 1,205.02
s: 1.46
x: 1.00
v: 0.93
rho: 1.08
h_fg: 755.48
is_superheated: NO! Steam is not superheated. T=467.05 °F <= saturation temp 467.05 °F at P=500.00 psia.
```

The state properties, however, can't be set directly — use `update()` with two arguments instead. The steam state is solved from two independent properties via IAPWS97, so changing one means re-solving with a fresh pair. Flow is just a multiplier on that state, which is why it can be assigned on its own:

```python
>>> my_other_steam.update(T=750, P=550)
>>> my_other_steam.display_properties()
Units: T(°F), P(psia), h(BTU/lb), s(BTU/lb·°R), v(ft³/lb), rho(lb/ft³), h_fg(BTU/lb)
stream_id: 2.00
flow_lb_per_hr: 2,000.00
T: 750.00
P: 550.00
h: 1,382.37
s: 1.62
x: 1.00
v: 1.24
rho: 0.81
h_fg: 743.61
is_superheated: YES! Steam is superheated. T=750.00 °F > saturation temp 476.98 °F at P=550.00 psia.
```

### EvaporatorSteam

`EvaporatorSteam` is the fast counterpart to `SteamStream`. Instead of IAPWS97, it uses the pressure correlations from `sugar_stream_properties.py` for saturation temperature and latent heat. It's built for evaporator trial-and-error calculations where a full IAPWS97 solve on every iteration would be wasteful — the accuracy tradeoff is small, and it's valid for roughly 1–60 psia.

It takes a pressure and an optional flow:

```python
>>> from SteamStream import EvaporatorSteam
>>> evap = EvaporatorSteam(P_psia=30, flow_lb_per_hr=1000)
>>> evap.display_properties()
Units: T(°F), P(psia), h_fg(BTU/lb)
P_psia: 30.00
flow_lb_per_hr: 1,000.00
sat_temp_deg_F: 250.31
h_fg: 945.27
```

Pressure can be changed directly, and the saturation temperature and latent heat follow:

```python
>>> evap.P_psia = 8
>>> evap.display_properties()
Units: T(°F), P(psia), h_fg(BTU/lb)
P_psia: 8.00
flow_lb_per_hr: 1,000.00
sat_temp_deg_F: 182.80
h_fg: 987.91
```

Like the other classes, it returns a dictionary via `properties()`:

```python
>>> evap.properties()
{'P_psia': 8, 'flow_lb_per_hr': 1000, 'sat_temp_deg_F': 182.79906858782903, 'h_fg': 987.9105787358312}
```

**When to use which:** reach for `SteamStream` when you need superheat, entropy, or high accuracy, or when working with boiler/turbine steam. Reach for `EvaporatorSteam` when you're iterating a multiple-effect evaporator and only need saturation temperature and latent heat at low pressures — it's dramatically faster per call.

---

## Massecuite

`Massecuite` handles the material and energy balance for a massecuite in a vacuum pan or crystallizer: boiling-point rise (BPR), crystal content, mother-liquor properties, and the temperature solve. The BPR regression is sourced from Birkett fig. 12.14, as presented in his Nicholls class notes; below 60 mother-liquor purity is extrapolated, so treat low-purity results with caution.

It runs in one of **two modes**, and you must give exactly one of `supersaturation` or `temp_F`:

- **Boiling mode** (`supersaturation` given) — the massecuite is boiling in a pan. Its temperature is solved from the vapor-space vacuum, the static head, and the BPR regression. All boiling properties apply (water boiling point and BPR at both surface and head). Requires `head_ft`.
- **Set-temperature mode** (`temp_F` given) — the massecuite is off-boiling in a crystallizer, reheater, or in transport, and its temperature is imposed by heat exchange. `massecuite_temp` returns your `temp_F` directly; the boiling-solve properties are unavailable, since BPR-based supersaturation only means something at boiling equilibrium.

### Boiling mode

```python
>>> from Massecuite import Massecuite
>>> masse = Massecuite(ml_purity=70, masse_purity=90, masse_brix=92,
...                    inches_vacuum=23.5, supersaturation=1.2, head_ft=2,
...                    flow_lb_hr=500_000)
>>> masse.display_properties()
Units: T(°F), BPR(°F), density(lb/ft³), flow(lb/hr), purity/brix/yield(%)
  ml_purity                    : 70.000
  masse_purity                 : 90.000
  masse_brix                   : 92.000
  crystal_content_pct          : 61.333
  mother_liquor_brix           : 79.310
  crystal_yield_pct_brix_pct   : 66.667
  density_lb_ft3               : 93.208
  massecuite_temp              : 181.263
  sat_bpr                      : 19.998
  inches_vacuum                : 23.500
  vapor_pressure_psia          : 3.154
  supersaturation              : 1.200
  head_ft                      : 2.000
  water_bp_surface             : 143.356
  massecuite_temp_surf         : 165.235
  bpr_at_surface               : 21.879
  water_bp_at_head             : 157.265
  bpr_at_head                  : 23.998
  flow_lb_hr                   : 500000.000
  solids_flow                  : 460000.000
  pol_flow                     : 414000.000
```

A few things worth understanding in that output:

- **Surface vs. head.** The pan reports two conditions. At the *surface* there's no liquid head, so the water boils lower and the massecuite sits cooler. At the *head* (here 2 ft down), static head raises the local pressure, the water boils hotter, and so does the massecuite. The `_surf` and `_at_head` properties let you see both.
- **`massecuite_temp`** is the head temperature — the meaningful one for the bulk of the massecuite.
- **Composition** (`crystal_content_pct`, `mother_liquor_brix`, `crystal_yield_pct_brix_pct`) comes straight from the purities and brix, independent of the temperature solve.
- **Flow properties** (`solids_flow`, `pol_flow`, `cu_ft_hr`) only appear when you pass `flow_lb_hr`.

The solves are cached — the iteration runs once per instance, on first access, then the results are reused.

### Set-temperature mode, and copy()

`copy()` clones a massecuite and lets you override inputs. Overriding `temp_F` switches the copy to set-temperature mode (dropping the old supersaturation); overriding `supersaturation` switches back. This models a massecuite leaving the pan and entering a crystallizer cleanly:

```python
>>> cryst = masse.copy(temp_F=120, ml_purity=64)
>>> cryst.display_properties()
Units: T(°F), BPR(°F), density(lb/ft³), flow(lb/hr), purity/brix/yield(%)
  ml_purity                    : 64.000
  masse_purity                 : 90.000
  masse_brix                   : 92.000
  crystal_content_pct          : 66.444
  mother_liquor_brix           : 76.159
  crystal_yield_pct_brix_pct   : 72.222
  density_lb_ft3               : 93.208
  massecuite_temp              : 120.000
  sat_bpr                      : 14.150
  flow_lb_hr                   : 500000.000
  solids_flow                  : 460000.000
  pol_flow                     : 414000.000
```

Notice the boiling-only rows (`vapor_pressure_psia`, `water_bp_surface`, `bpr_at_head`, and so on) are gone — in set-temperature mode those aren't defined, and reaching for them raises a clear error telling you to `copy(supersaturation=...)` if the massecuite is back in a pan. Because the copy runs back through the constructor, validation re-runs and it solves fresh, with no stale cached results carried over.

---

## Bagasse

`Bagasse` is a stream class like `SugarStream`, just for the fibrous solid leaving the last mill instead of a liquid. Give it a proximate analysis (moisture, brix, pol, ash — all as % of wet weight) and a flow, and it derives fiber content and gross calorific value (GCV):

```python
>>> from Bagasse import Bagasse
>>> b = Bagasse(
...     moisture_pct=49.0,
...     brix_pct=1.2,
...     pol_pct=0.8,
...     ash_pct=4.0,
...     flowrate_lb_hr=125_000,
... )
>>> b.neat_display()
========================================
           BAGASSE PROPERTIES
========================================
  Flowrate             125,000.00  lb/hr
----------------------------------------
  Fiber                     49.80  %
  Moisture                  49.00  %
  Brix                       1.20  %
  Pol                        0.80  %
  Ash                        4.00  %  (assumed part of fiber)
----------------------------------------
  GCV                     3945.18  BTU/lb
========================================
```

A couple of things worth knowing:

- **`fiber_pct`** is a calculated number, not a lab input: `100 - moisture_pct - brix_pct`. `pol_pct` and `ash_pct` aren't subtracted out — pol is treated as part of brix (dissolved solids), and ash is left inside the fiber fraction (hence the `(assumed part of fiber)` note on `neat_display()`). Note that in reality, I am not saying ash is literally a part of fiber, but something needed to be nested in something else to make the typical lab numbers work out (pol, moisture, last roll purity). I do not, nor do I know any LA mills that record ash % bagasse independent of the other values on the manufacturing report. 
- **`gcv`** is a moisture/ash/brix-penalized correlation — more moisture, ash, or entrained brix all pull the calorific value down from the bone-dry-fiber ceiling (`19605 - 196.05*M - 196.05*A - 31.14*B`, converted from kJ/kg to BTU/lb by the trailing `0.4299` factor).
- Unlike `SugarStream`, this class only ships `neat_display()` — there's no `properties()`/`display_properties()` dict export and no `__repr__`, so if you need the values programmatically, read the attributes/properties (`b.fiber_pct`, `b.gcv`, etc.) directly. This is because this stream is only meant to be used in the Boiler class, there is not much utility for it otherwise. 

---
# Equipment Classes

## JuiceHeaterShellTube

This class represents a heat exchanger. It was originally intended for shell-and-tube calculations (tube velocity, pressure drop, number of passes), but that scope was dropped as outside the project, though the name is still intact. Instead it does the basic heat-exchanger balance, `Q = U * A * LMTD`, and works for either type — plate or shell-and-tube.

With the stream classes above under your belt, `JuiceHeaterShellTube` is intuitive: hand it a cold `SugarStream` and a hot `SteamStream`, plus the design parameters. `steam_type` tags which steam source feeds the heater — `0` for exhaust, `1`–`4` for vapor bleeds V1 through V4.

```python
>>> from JuiceHeater import JuiceHeaterShellTube
>>> heater = JuiceHeaterShellTube(
...     cold_stream=SugarStream(brix=14, purity=90, temp_deg_F=90, pressure_psia=40, level_ft=0, flow_lb_per_hr=100),
...     hot_stream=SteamStream(x=1, P=30),
...     name="Juice Heater",
...     juice_out_temp_degF=220,
...     U_btu_per_ft2_degF=185,
...     installed_area_ft2=6000,
...     steam_type=0,   # 0 = exhaust, 1–4 = vapor bleeds V1–V4
... )
>>> heater.properties()
{'name': 'Juice Heater',
 'U': 185,
 'cold_stream': SugarStream(brix=14.00, purity=90.00, flow=100.00 lb/hr, temp=90.00°F, pressure=40.00 psia, level=0.0 ft),
 'hot_stream': SteamStream(T=250.30°F, P=30.00 psia, h=1164.14 BTU/lb, x=1),
 'juice_out_temp_degF': 220,
 'installed_area_ft2': 6000,
 'steam_type': 0,
 'juice_out': SugarStream(brix=14.00, purity=90.00, flow=100.00 lb/hr, temp=220.00°F, pressure=40.00 psia, level=0.0 ft),
 'cold_delta_T': 130,
 'Q_btu_per_hr': 11923.807999999999,
 'LMTD_degF': np.float64(78.03739510075035),
 'required_area_ft2': np.float64(0.8259247522678584),
 'steam_required_lb_per_hr': np.float64(12.614946467763332),
 'is_steam_hot_enough': 'YES'}
```

Please note that `steam_type` doesn't actually do anything within the heater class itself, but rather serves a more important role in `main.py` (or any full factory balance `.py` file): being able to work with the `Evaporator` and `EvaporatorSet` classes to automate the V1–V4 bleed quantities needed, rather than manually inputting bleed quantities. You can even wrap your balance in a loop to update the heater class steam pressure and feed that output back to the `EvaporatorSet`, but we'll cover that later.

From here on, some of the equipment objects are packaged with `neat_display()`, `to_excel()`, & `generate_pfd()`. 

```python
>>> heater.neat_display()
==============================================================
                JUICE HEATER  —  JUICE HEATER
==============================================================

  DESIGN PARAMETERS
--------------------------------------------------------------
  Overall HT Coeff. (U)                     185.0 BTU/ft²·°F
  Juice Outlet Temperature                          220.0 °F
  Installed Area                                   6,000 ft²

  INLET CONDITIONS
--------------------------------------------------------------
  Juice Inlet Temperature                            90.0 °F
  Juice Flow Rate                                  100 lb/hr
  Juice Brix                                        14.0 °Bx
  Juice Purity                                        90.0 %
  Steam Temperature                                 250.3 °F

  HEAT TRANSFER RESULTS
--------------------------------------------------------------
  Juice Temperature Rise (ΔT)                       130.0 °F
  LMTD                                               78.0 °F
  Heat Duty (Q)                                11,924 BTU/hr
  Required Area                                        1 ft²
  Steam Required                                    13 lb/hr
  Steam Hot Enough?                                      YES

==============================================================
```

`generate_pfd()` returns a matplotlib figure of the process flow diagram:

```python
>>> heater.generate_pfd()
<Figure size 1050x958 with 2 Axes>
```

<img width="1050" height="958" alt="Juice heater PFD" src="https://github.com/user-attachments/assets/ba3d8ef7-dcce-43cf-88d4-527ec2f58115" />

By default `generate_pfd()` has `show=True`, which opens a window — fine interactively, but in a script or headless environment pass `save_path="pfd.png"` (or set a non-interactive matplotlib backend) so it doesn't block.

`to_excel()` writes the results into a workbook:

```python
>>> from excel_export import new_workbook
>>> wb = new_workbook()
>>> heater.to_excel(wb)
>>> wb.save("juice_heater.xlsx")
>>> print("Saved juice_heater.xlsx")
Saved juice_heater.xlsx
```

The workbook is saved in the current working directory. Check out `JuiceHeater.py` and run it to see the workbook.

---

## Evaporator

`Evaporator` models a single Robert vessel in the evaporator station: a juice-side `SugarStream` coming in, a calandria-side `EvaporatorSteam` (or `SteamStream`) supplying the heat, and the vessel's area and vapor-space pressure. It solves how much water flashes/evaporates off the juice, what brix the juice leaves at, and how the calculated heat-transfer coefficient stacks up against a Dessin's-method estimate.

Unlike `JuiceHeaterShellTube`, the outlet streams aren't recomputed automatically on every access — call `solve()` once you're happy with the inputs, and it pushes the results into `juice_side_out` and `vapor_out`:

```python
>>> from SugarStream import SugarStream
>>> from SteamStream import EvaporatorSteam
>>> from Evaporator import Evaporator
>>> clear_juice = SugarStream(brix=14, purity=90, flow_lb_per_hr=1_000_000, temp_deg_F=225, pressure_psia=60, level_ft=0)
>>> exhaust_steam = EvaporatorSteam(P_psia=30, flow_lb_per_hr=100_000)
>>> evaporator = Evaporator(
...     juice_side_in=clear_juice,
...     calandria_side=exhaust_steam,
...     area_ft2=25_000,
...     liquid_level_ft=2,
...     dessin_coefficient=18000,
...     vapor_pressure_psia=25,
... )
>>> evaporator.solve()
>>> evaporator.display_properties()
Units: T(°F), P(psia), h_fg(BTU/lb)
juice_side_in: SugarStream(brix=14.00, purity=90.00, flow=1,000,000.00 lb/hr, temp=225.00°F, pressure=60.00 psia, level=0.0 ft)
calandria_side: EvaporatorSteam(P_psia=30.00, flow_lb_per_hr=100,000.00)
area_ft2: 25,000.00
dessin_coefficient: 18,000.00
vapor_pressure_psia: 25.00
liquid_level_ft: 2.00
juice_side_out: SugarStream(brix=15.27, purity=90.00, flow=916,932.68 lb/hr, temp=241.82°F, pressure=25.00 psia, level=2.0 ft)
vapor_out: EvaporatorSteam(P_psia=25.00, flow_lb_per_hr=83,067.32)
vapor_bleed: EvaporatorSteam(P_psia=25.00, flow_lb_per_hr=0.00)
heat_duty_btu_per_hr: 94,526,921.13
lbs_evaporated_per_hr: 83,083.82
heat_from_flash: -15,426,312.33
heat_available_for_evaporation: 79,100,608.81
brix_out: 15.27
delta_T_juice_steam: 8.50
dessin_U: 539.21
heat_xfer_U: 445.04
U_ratio: 0.83
bpe_juice: 1.77
vapor_temperature: 240.05
condensate_out: 100,000.00

 Juice In details: 
 ...
 Material and Energy Balance

Entering: 100,000.00 lb/hr * 945.27 BTU/lb = 94,526,921.13 BTU/hr
Plus: 1,000,000.00 lb/hr * 0.92 BTU/lb * (-16.82°F) = -15,426,312.33 BTU/hr
Available for Evaporation: 94,526,921.13 + -15,426,312.33 = 79,100,608.81 BTU/hr
```

A few things worth knowing:

- **`heat_duty_btu_per_hr`** is just calandria steam flow × its latent heat.
- **`heat_from_flash`** accounts for the juice entering above (or below) the temperature it settles at on the outlet side. It's negative in this example because the juice is actually *heating up* (225°F in → 241.82°F out, since the outlet is pinned to the lower vapor-space pressure's saturation point), so it subtracts from the heat available for evaporation rather than adding to it — watch the sign, don't assume it's always a bonus.
- **`brix_out`** and `juice_side_out` are solved from the lbs evaporated, not assumed — change an input (steam flow, area, vapor pressure) and call `solve()` again to update them; nothing recalculates until you do.
- **`U_ratio`** (`heat_xfer_U / dessin_U`) is the sanity check on vessel performance: near 1.0 says the calculated coefficient matches what Dessin's correlation expects for this brix and ΔT; well below 1.0 (0.83 here) flags scaling, fouling, or an area/duty mismatch worth a second look.
- **`vapor_bleed`** lets you pull a bleed stream off this effect (e.g. to feed a `JuiceHeaterShellTube`), but setting it doesn't touch the balance by itself — `EvaporatorSet` is what nets the bleed out of `lbs_evaporated_per_hr` before forwarding vapor to the next effect. Set it directly and it's on you to account for it downstream.

`Evaporator` has no `neat_display()` — `display_properties()` (above) is the full report, including both streams and the balance walk-through. Multiple `Evaporator` instances get chained by `EvaporatorSet` / `multi_effect_solver_vers_2` for the full multi-effect station; see `main.py` for that pattern.
---

## Pan

`Pan` runs the full material and energy balance for a vacuum pan — one or more feed `SugarStream`s in, a boiling massecuite out, sized against a calandria and vapor-space condition. It builds its own internal `Massecuite` from the feeds, so you don't hand it one directly.

```python
>>> from SugarStream import SugarStream
>>> from Pan import Pan
>>> syrup   = SugarStream(brix=80, purity=88, flow_lb_per_hr=250_000, temp_deg_F=144, pressure_psia=14.7, level_ft=0)
>>> footing = SugarStream(brix=88, purity=92, flow_lb_per_hr=50_000, temp_deg_F=150, pressure_psia=14.7, level_ft=0)
>>> pan = Pan(
...     feed_streams=[syrup, footing],
...     heating_surface_ft2=22_000,
...     inches_vacuum=26.5,
...     supersaturation=1.2,
...     head_ft=2,
...     masse_brix=96,
...     ml_purity=70,
...     calandria_pressure_psia=21.696,   # V1 steam (7 psig)
...     heat_loss_factor=0.05,
... )
```

Note what you give it and what it derives:

- **`ml_purity`** (mother liquor purity) is a direct input — pull it from lab analysis or process knowledge.
- **`masse_purity`** is *not* an input. It's a property, derived live from the pol/solids balance across `feed_streams`: `Σ(flow×purity×brix) / Σ(flow×brix)`. Add, remove, or reweight feed streams and it updates automatically.
- **`calandria_pressure_psia`** drives `calandria_T_sat_F` and `h_fg_calandria` live through an internal `EvaporatorSteam` — change the attribute after construction (e.g. once you know the actual measured header pressure) and every heat-transfer result downstream recalculates, no re-instantiation needed. `pan.neat_display()` below shows this in the "single-pass U refinement" idea from `Pan.py`'s own `__main__` block.

`pan.neat_display()`:

```
===========================================================
  Pan  |  21.70 psia steam  |  22,000 ft²  |  26.5 inHg vacuum
===========================================================

  -------------------------------------------------------
  FEED
  -------------------------------------------------------
  Total feed flow                          300,000.0  lb/hr
  Feed solids                              244,000.0  lb/hr
  Feed temperature                             145.0  °F

  -------------------------------------------------------
  MASSECUITE
  -------------------------------------------------------
  Massecuite flow                          254,166.7  lb/hr
  Massecuite brix                               96.0  %
  Massecuite purity                             88.7  %
  Mother liquor purity                          70.0  %
  Crystal content                               59.9  %
  Mother liquor brix                            90.0  %

  -------------------------------------------------------
  EVAPORATION
  -------------------------------------------------------
  Water evaporated                          45,833.3  lb/hr
  Massecuite temp                              163.0  °F
  Vapor pressure                                 1.7  psia
  BPR at head                                   21.6  °F

  -------------------------------------------------------
  ENERGY BALANCE
  -------------------------------------------------------
  Sensible heat                          2,285,707.4  BTU/hr
  Evaporation heat                      46,979,010.1  BTU/hr
  Heat loss                              2,463,235.9  BTU/hr
  Total duty                            51,727,953.5  BTU/hr

  -------------------------------------------------------
  STEAM & HEAT TRANSFER
  -------------------------------------------------------
  Calandria pressure                            21.7  psia
  Calandria T_sat                              232.3  °F
  h_fg calandria                               957.1  BTU/lb
  Steam flow                                54,046.5  lb/hr
  Steam/evaporation ratio                        1.2  lb/lb
  dT (calandria - masse)                        69.3  °F
  U (back-calc)                                 33.9  BTU/hr·ft²·°F

===========================================================
```

`U_btu_hr_ft2_F` is *back-calculated* (`Q / (A × ΔT)`), not looked up — it's a diagnostic on how the pan is actually performing given the current calandria pressure, not a design input. Update `calandria_pressure_psia` to the real header pressure and re-read it any time without touching anything else:

```python
>>> pan.calandria_pressure_psia = 20.5   # actual measured V1 header pressure
>>> pan.U_btu_hr_ft2_F
35.5   # up from 33.9 at the original 21.696 psia assumption
```

**One gotcha worth knowing before you rely on it:** `crys_yld_frac_brix` is computed once in `__init__` from `masse_purity` and `ml_purity` at that moment, and stored as a plain attribute — it does **not** recompute if you mutate a feed stream's brix or purity afterward, even though `masse_purity` itself is a live property and will show the new value. If you change feed composition after building the `Pan`, `crys_yld_frac_brix` is stale until you rebuild the `Pan` instance. `properties()`/`display_properties()` (a flat dict/printout of everything above, without the section headers) are also available if `neat_display()`'s formatting isn't what you want. That is because it is meant to be fed into one of the boiling schemes and it handles the rebuild. To handle this manually, simply press the up arrow key (in a terminal) until the prompt for your pan class reappears, from there adjust the parameters you want, then repeat the `neat_display()` method. If you customize your own Pan Floor balances, generally you will nest building of the Pan class in a loop for iterative solving, this will rebuild the Pan class automatically in python.

`Pan` has no `to_excel()` or `generate_pfd()`.

---

## Centrifugal

`Centrifugal` takes a massecuite off the pan (or crystallizer/reheater) and splits it into sugar and molasses — the SJM (Sugar/Juice/Molasses) purity balance. Hand it a `Massecuite` instance plus the flow reaching the centrifugal (`pan.massecuite_flow_lb_hr`, or the crystallizer/reheater's `massecuite_out` flow if it's gone through those first):

```python
>>> from Massecuite import Massecuite
>>> from Centrifugal import Centrifugal
>>> masse_A = Massecuite(ml_purity=70, masse_purity=90, masse_brix=92,
...                      inches_vacuum=23.5, supersaturation=1.2, head_ft=2)
>>> cent_A = Centrifugal(
...     massecuite=masse_A,
...     massecuite_flow_lb_hr=226_630,
...     target_molasses_brix=78.0,
...     purity_rise=1.1,   # molasses purity = ml_purity + rise = 71.1%
...     sugar_purity=99.5,
...     sugar_moisture=0.5,
... )
>>> cent_A.neat_display()
```

```
═══════════════════════════════════════════════════════════
  Centrifugal  |  J=90.0%  S=99.5%  M=71.1%
═══════════════════════════════════════════════════════════

  ───────────────────────────────────────────────────────
  MASSECUITE FEED
  ───────────────────────────────────────────────────────
  Massecuite flow                          226,630.0  lb/hr
  Massecuite solids                        208,499.6  lb/hr
  Massecuite brix                               92.0  %
  Massecuite purity (J)                         90.0  %
  Mother liquor purity                          70.0  %
  Pol in                                   187,649.6  lb/hr

  ───────────────────────────────────────────────────────
  SUGAR PRODUCT
  ───────────────────────────────────────────────────────
  Sugar solids (dry)                       138,755.0  lb/hr
  Sugar flow (wet)                         139,452.3  lb/hr
  Sugar brix                                    99.5  %
  Sugar purity (S)                              99.5  %
  Sugar pol %                                   99.0  %
  Sugar moisture                                 0.5  %
  Moisture lb/hr                               697.3  lb/hr
  Pol to sugar                             138,061.2  lb/hr

  ───────────────────────────────────────────────────────
  MOLASSES
  ───────────────────────────────────────────────────────
  Molasses flow                             89,416.1  lb/hr
  Molasses solids                           69,744.6  lb/hr
  Molasses brix                                 78.0  %
  Molasses purity (M)                           71.1  %
  Purity rise                                    1.1  %
  Pol to molasses                           49,588.4  lb/hr
  Molasses density                              11.6  lb/gal
  Molasses flow                                128.5  gal/min

  ───────────────────────────────────────────────────────
  WASH WATER & YIELD
  ───────────────────────────────────────────────────────
  Wash water required                        2,238.4  lb/hr
  Crystal yield (% brix)                        65.4  %
  Crystal yield (% masse)                       60.2  %

═══════════════════════════════════════════════════════════
```

Two things worth flagging before you trust the numbers:

- **`purity_rise` drives the whole molasses side, not a two-step crystal-loss model.** The module's own header comment describes a more elaborate SJM derivation — an "ideal split" at the mother-liquor purity, then a second pass where dissolved crystal (`crystal_loss_pct`) raises the molasses purity. That's *not* what's implemented: there's no `crystal_loss_pct` parameter or crystal-loss step in the code at all. What actually runs is a single-pass SJM balance where you specify `molasses_purity = ml_purity + purity_rise` directly — `purity_rise` is your one dial for "how much higher than mother-liquor purity does the molasses end up," lumping crystal loss, wash dilution, and everything else into one number you set from experience.
- **`target_molasses_brix` back-calculates wash water**, not the other way around — pick a target brix, and `wash_water_lb_hr` is solved to hit it. If the target is *higher* than the molasses would naturally sit at with zero wash water, `wash_water_lb_hr` raises a `ValueError` telling you to lower the target (you can't un-add water that's already there).

`molasses_stream` hands you a ready-made `SugarStream` for feeding straight into the next lower pan grade (e.g. A molasses → B pan feed):

```python
>>> next_grade_feed = cent_A.molasses_stream
```

`properties()` and `display_properties()` are also available for a flat dict/printout without the section headers. `Centrifugal` has no `to_excel()` or `generate_pfd()`.

---

## Crystallizer

`Crystallizer` and `Reheater` (below) share a module — both are non-contact water heat exchangers for low-grade (C) massecuite between the pan and the centrifugals, and both conserve massecuite mass flow (nothing mixes in or out, unlike the pan or centrifugal). `Crystallizer` cools the massecuite with cold water after it drops from the pan, driving further crystal growth as the mother liquor exhausts:

```python
>>> from Massecuite import Massecuite
>>> from Crystallizer_and_Reheater import Crystallizer, Reheater
>>> c_masse = Massecuite(ml_purity=33, masse_purity=54, masse_brix=95.5,
...                      inches_vacuum=26.5, supersaturation=1.2, head_ft=2)
>>> crys = Crystallizer(c_masse, 100_000,
...                     masse_temp_out_deg_F=120, ml_purity_out=30,
...                     water_temp_in_deg_F=85, water_temp_out_deg_F=105,
...                     name='C Crystallizer')
>>> crys.neat_display()
=== C Crystallizer ===
  Massecuite : 100,000 lb/hr, 173.0 → 120.0 °F
  ML purity  : 33.0 → 30.0 %   crystal content 29.9 → 32.7 %  (+2,810 lb/hr crystal)
  Duty       : 2,417,070 BTU/hr removed
  Cooling water: 120,854 lb/hr (242 gpm), 85 → 105 °F
```

A few things to know:

- **`massecuite_in` must already be a solved `Massecuite`** — boiling mode straight off a pan, or set-temperature mode from a prior unit. `masse_temp_in_deg_F` just reads `massecuite_in.massecuite_temp`, whichever mode produced it.
- **`ml_purity_out` is optional** — leave it `None` and the mother liquor purity carries through unchanged; set it lower to model the exhaustion (further crystal growth) that cooling actually causes, as in the example above (33 → 30).
- **The heat balance is sensible-only** — heat of crystallization is neglected as small, per the module's own comment. Don't expect it to reconcile against a rigorous crystallization-energy balance.
- **`massecuite_out`** is a *new* set-temperature-mode `Massecuite` (via `.copy()`), ready to feed the `Reheater` or `Centrifugal` directly — it doesn't mutate `massecuite_in`.
- Construction raises a `ValueError` immediately if `water_temp_out_deg_F <= water_temp_in_deg_F` — cooling water has to leave hotter than it enters, or the inputs are physically wrong.

`Crystallizer` has `properties()` and `neat_display()`, but no `display_properties()`, `to_excel()`, or `generate_pfd()`.

---

## Reheater

`Reheater` is `Crystallizer`'s mirror image: it warms the cooled, exhausted massecuite back up with hot water before the centrifugals, to cut viscosity for spinning. Hot water rather than steam avoids local overheating that would redissolve crystal, so mother liquor purity is assumed unchanged by default:

```python
>>> reheat = Reheater(crys.massecuite_out, 100_000,
...                   masse_temp_out_deg_F=130,
...                   water_temp_in_deg_F=150, water_temp_out_deg_F=135,
...                   name='C Reheater')
>>> reheat.neat_display()
=== C Reheater ===
  Massecuite : 100,000 lb/hr, 120.0 → 130.0 °F
  Duty       : 456,252 BTU/hr added
  Hot water  : 30,417 lb/hr (61 gpm), 150 → 135 °F

>>> reheat.massecuite_out
Massecuite(ml_purity=30, masse_purity=54, masse_brix=95.5, temp_F=130)
```

Same shape as `Crystallizer`, flipped:

- **`water_temp_in_deg_F` must exceed `water_temp_out_deg_F`** (hot water supply cooler than its return is backwards) — construction raises `ValueError` otherwise.
- **`ml_purity_out`** defaults to unchanged, same as `Crystallizer`; the class docstring's rationale is that reheating with hot water (rather than steam) avoids the local overheating that would redissolve crystal in the first place, which is why "unchanged" is the default rather than the exception. You can still pass a value slightly above the inlet purity if you want to model some redissolution happening anyway.
- **`massecuite_out`** feeds straight into `Centrifugal`'s `massecuite=` argument — see `crys.massecuite_out` → `reheat` → `reheat.massecuite_out` → `Centrifugal(...)` chained in `Crystallizer_and_Reheater.py`'s own `__main__` block.

Same method set as `Crystallizer`: `properties()` and `neat_display()`, no `display_properties()`, `to_excel()`, or `generate_pfd()`.

---

## Condenser

`Condenser` models a barometric condenser — the injection-water spray that condenses vapor pulled off the last evaporator effect or a vacuum pan, using cold water rather than a surface exchanger. Give it a vapor stream with a flow set (either `EvaporatorSteam` or `SteamStream` — it duck-types between them) and the injection water's supply temperature:

```python
>>> from SteamStream import EvaporatorSteam
>>> from Condenser import Condenser
>>> vapor = EvaporatorSteam(P_psia=14.696 - 26.5 * 0.491154, flow_lb_per_hr=50_000)  # 26.5 inHg vacuum
>>> cond = Condenser(vapor, water_inlet_temp_F=75, water_outlet_temp_drop_F=5)
>>> cond.neat_display()
Condenser Summary:
  Vapor Saturation Temp (°F): 119.68
  Vapor h_fg (BTU/lb): 1,025.00
  Vapor Flow (lb/hr): 50,000.00
  Heat Load (BTU/hr): 51,499,829.24
  Injection Water Inlet (°F): 75.00
  Water Outlet Temp (°F): 114.68
  Injection Water Flow (lb/hr): 1,297,773.94
  Total Outlet Flow (lb/hr): 1,347,773.94
```

Key assumption, straight from the module comment: **the outlet water/condensate mixture is assumed to leave at (vapor saturation temp − `water_outlet_temp_drop_F`)** — perfect mixing, no sub-cooling beyond that fixed approach. `water_outlet_temp_drop_F` defaults to 5°F and is *your* approach-temperature assumption, not something solved for.

`injection_water_flow_lb_hr` raises `ValueError` if the water inlet temperature is at or above the vapor's (drop-adjusted) saturation temperature — there's no physical solution if the injection water can't absorb the heat.

`Condenser` has `properties()`, `display_properties()`, and `neat_display()`.

---

## CoolingTower

`CoolingTower` is the leanest class in the project — a bare-bones evaporative cooling-tower balance with no `properties()`, `display_properties()`, `neat_display()`, or even a custom `__repr__`. Read its attributes and properties directly:

```python
>>> from CoolingTower import CoolingTower
>>> tower = CoolingTower(
...     hot_water_temp=105,
...     hot_water_lb_hr=1_500_000,
...     cool_water_temp=85,
...     percent_blowdown=3,
... )
>>> tower.blowdown_lb_hr
45000.0
>>> tower.evaporated
29100.0
>>> tower.cool_water_lb_hr
1425900.0
>>> tower.cool_water_gpm
2863.2530120481924
```

How the balance works, in order:

1. **`blowdown_lb_hr`** — `hot_water_lb_hr × percent_blowdown / 100`.
2. **`water_to_tower`** — hot return flow minus blowdown.
3. **`evaporated`** — heat rejected (`water_to_tower × (hot_water_temp − cool_water_temp)`, Cp assumed 1.0) divided by a flat **1,000 BTU/lb** latent heat approximation, noted directly in the code (`# about 1000 btu / lb evaporated`) rather than pulled from a steam table — a deliberately simple stand-in, not IAPWS-grade.
4. **`cool_water_lb_hr`** — what's left after evaporation losses (`water_to_tower − evaporated`) — this is the flow returning to the process, *not* `hot_water_lb_hr`; makeup water to replace blowdown and evaporation isn't modeled by this class at all.

For a fuller system model — makeup water, blended delivery temperature to multiple condensers — see `CoolingTowerSystem.py`, which wraps a `CoolingTower` instance internally (`self.tower`) rather than duplicating its math.

---

## Other equipment classes

The pattern above — take streams (or the parameters to build them), run the material and energy balance, expose `properties()`/`display_properties()` and usually `neat_display()` — carries through the rest of the project: boilers, mills, clarifiers, turbines, deaerators, and the mill-floor/pan-floor station assemblies (`Boiler.py`, `MillFloor.py`, `Clarification.py`, `Turbine.py`, `Deaerator.py`, `FourBoilingDoubleMagma.py`, `ThreeBoilingDoubleMagma.py`, `TwoBoiling.py`, and so on).

These aren't yet individually documented here. Until the worked examples are finished, the best reference is **`main.py`**, which drives the full factory and shows each class being constructed and chained. `examples.py` also shows a compact end-to-end run of the mill floor.

_Individual equipment sections and worked examples: in progress._
