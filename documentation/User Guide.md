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
>>> my_stream.brix = 65
>>> my_stream.properties()
{'stream_id': 2, 'brix': 65, 'purity': 90, 'flow_lb_per_hr': 100, 'temp_deg_F': 225, 'pressure_psia': 50, 'level_ft': 2, 'pol': 58.5, 'boiling_point_elevation_deg_F': 8.923810142857143, 'cp_btu_per_lb_deg_F': 0.62876, 'specific_gravity': 1.3158810906176885, 'cu_ft_hr': 1.2178639194608702, 'latent_heat_btu_per_lb': np.float64(924.1472739021877), 'vapor_saturation_temp_deg_F': np.float64(280.9818423397531), 'solids_flow': 65.0, 'pol_flow': 58.5}
```

### SteamStream and EvaporatorSteam

_Documentation in progress._
