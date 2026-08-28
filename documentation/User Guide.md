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

## SugarStream, SteamStream, and EvaporatorSteam

These three classes are the foundation everything else is built on.

### SugarStream

`SugarStream` covers every water–sugar–non-sugar mixture in the factory: juice, syrup, molasses, massecuite, and magma. There is a dedicated `Massecuite` class for pan material and energy balances, but `SugarStream` gives you the basic properties engineers typically look for.

```python
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

### SteamStream and EvaporatorSteam

#### SteamStream

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
 'is_superheater': 'YES! Steam is superheated. T=350.00 °F > saturation temp 280.99 °F at P=50.00 psia.'}
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
is_superheater: YES! Steam is superheated. T=350.00 °F > saturation temp 280.99 °F at P=50.00 psia.
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
is_superheater: NO! Steam is not superheated. T=467.05 °F <= saturation temp 467.05 °F at P=500.00 psia.
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
is_superheater: NO! Steam is not superheated. T=467.05 °F <= saturation temp 467.05 °F at P=500.00 psia.
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
is_superheater: YES! Steam is superheated. T=750.00 °F > saturation temp 476.98 °F at P=550.00 psia.
```

#### EvaporatorSteam

_Documentation in progress._
