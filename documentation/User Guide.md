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

From here on, the equipment objects are packaged with `neat_display()`, `to_excel()`, and — for some — `generate_pfd()`.

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

## Other equipment classes

`JuiceHeaterShellTube` above is the pattern for the rest: take streams (or the parameters to build them), run the material and energy balance, and expose `neat_display()`, `to_excel()`, and sometimes `generate_pfd()`. The remaining equipment classes assemble streams into unit operations and whole stations — evaporators, pans, boilers, mills, clarifiers, turbines, deaerators, cooling towers, and so on.

These aren't yet individually documented here. Until the worked examples are finished, the best reference is **`main.py`**, which drives the full factory and shows each class being constructed and chained. `examples.py` also shows a compact end-to-end run of the mill floor.

_Individual equipment sections and worked examples: in progress._
