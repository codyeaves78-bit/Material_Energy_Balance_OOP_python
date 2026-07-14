# Sugar Factory Balance — Caveman Guide

This code build sugar factory. Not real factory. Number factory.

You put in cane. Code do math. Code tell you: how much juice, how much steam,
how much sugar, how much water, how much everything. This how big raw sugar
mill run its numbers before spending real money on real steel.

Code not one big blob. Code is many small machine. Each machine is one
Python file. Each machine is one class. You pick machine you need, you feed
it numbers, machine give you answer back. Then you feed THAT answer into
next machine. Just like real factory — juice flow mill to mill, steam flow
turbine to turbine.

This guide caveman-simple on purpose. Read whole thing, you understand whole
factory.

---

## 1. Big Idea

Two kind of "stuff that flows" in this factory:

- **SugarStream** (`SugarStream.py`) — juice, syrup, molasses, sugar. Has
  brix (how sweet), purity (how clean sweet is), flow (lb/hr), temperature,
  pressure.
- **SteamStream** (`SteamStream.py`) — steam or water. Uses real steam-table
  physics (IAPWS-97) so numbers are accurate, not guessed. There is also a
  faster cousin, **EvaporatorSteam** — same file, see Section 2 below.

Every machine class takes some Stream object IN, does math in `__init__`,
and gives you Stream object(s) OUT (usually as a property like
`.juice_out` or `.steam_stream`). You chain machines by passing one
machine's output stream into the next machine's input.

Almost every machine also give you:

- `.neat_display()` — print nice report to screen
- `.to_excel(workbook)` — write nice page into Excel file
- `.generate_pfd()` — draw picture of the machine (many machines only)

**Every machine file has its own worked example.** Scroll to the bottom of
almost any file — `MillFloor.py`, `Pan.py`, `Turbine.py`, `EvaporatorSet.py`,
all of them — and you find an `if __name__ == "__main__":` block that builds
a real one, prints it, and exports it to its own little Excel file. Run that
file straight from the terminal (`python Pan.py`) and you see it work, all
by itself, no factory needed. This is the fastest way to learn one machine —
don't just read the class, run the bottom of the file. (A few files are pure
math/plumbing helpers — `excel_export.py`, the `*_diagram.py` picture
files, `sugar_stream_properties.py`, `evaporator_functions.py` — those don't
stand alone, they're only ever called BY a machine file, so they skip this
pattern.)

Machine solve itself the moment you build it (in `__init__`). No separate
"go" button needed, except two machines that need extra iteration:
`EvaporatorSet` (call `.adjust_pressure_profile()` after building it) and
the pan-floor classes (already loop internally, just build them).

---

## 2. Every File, What It Do

### The stuff that flows

| File | What it is |
|---|---|
| `SugarStream.py` | Juice/syrup/sugar stream. Brix, purity, flow, temp, pressure. The most-used object in whole codebase. |
| `SteamStream.py` (class `SteamStream`) | Steam or water stream, built on real steam tables (IAPWS-97). Give it any 2 of T/P/h/s/x, it solve the rest. Slow-ish, because IAPWS-97 does real iterative root-finding under the hood. |
| `SteamStream.py` (class `EvaporatorSteam`, same file) | A stripped-down, saturated-steam-only stream — just pressure and flow in, `sat_temp_deg_F` and `h_fg` out, using fast polynomial fits instead of IAPWS-97. Built for the hundreds of times an iterative solver (`EvaporatorSet`, `Pan`, `PreEvaporator`, `Condenser`) has to re-check steam properties every loop — see `EvaporatorSetIAPWS.py` below for exactly how much faster this is. |
| `Massecuite.py` | Special stream for the sugar-crystal slurry inside a pan (has crystal content, boiling point rise). Built automatically by `Pan.py` — you rarely touch it directly. |
| `Bagasse.py` | The fiber waste stream that comes out of the mills. Feeds the boiler. |
| `sugar_stream_properties.py` | The physics formulas behind `SugarStream` (boiling point rise, specific heat, specific gravity). You don't call this — `SugarStream` calls it for you. |
| `evaporator_functions.py` | Small helper math: psig ↔ psia, inHg vacuum ↔ psia, first-guess steam estimate. |
| `condensate_utils.py` | One function, `flash_condensate()` — how much hot condensate flashes to steam when it drops to atmosphere. Used by every machine that returns condensate. |

### Cane in, clean juice out (front of factory)

| File | What it is |
|---|---|
| `MillFloor.py` | The mills. Cane goes in, mixed juice + bagasse come out. Give it cane tons/day, pol%, fiber%, number of mills, imbibition% — it solves the whole train. |
| `Clarification.py` | Cleans the juice with lime + polymer. Mixed juice in, clarified juice + filter cake out. |
| `JuiceHeater.py` (class `JuiceHeaterShellTube`) | One shell-and-tube heater. Juice in one side, steam in the other, hot juice out. |
| `JuiceHeatingStation.py` | Wires several `JuiceHeaterShellTube` together — series (one after another) or parallel (split the juice flow). This is what you actually build in `main.py`, not the single heater. |

### Water out of juice (evaporators — makes syrup)

This is the one corner of the codebase with THREE worked examples instead of
one, because it's the trickiest part to learn — read them in this order:

1. **`EvaporatorSet.py`** own `if __name__` block — the simplest possible
   case, one hand-built set, no factory around it.
2. **`multi_effect_solver_vers_2.py`** own `if __name__` block — shows the
   smart multi-set helper solving several sets side by side, still with no
   factory around it.
3. **`main.py`** — the same helper, but now wired into a real, full factory
   balance (juice comes from `Clarification`, a `PreEvaporator` bleeds V1
   off the top first, and the syrup that comes out feeds the pan floor).

| File | What it is |
|---|---|
| `Evaporator.py` | One single evaporator effect. You almost never build this alone. |
| `EvaporatorSet.py` | Chains several `Evaporator.py` effects into one multi-effect set, and iterates the pressure profile + steam flow until it converges (Birkett method). |
| `PreEvaporator.py` | One evaporator body that runs BEFORE the main set, stealing a fixed vapor bleed early (used to feed V1 heaters/pans). |
| `multi_effect_solver_vers_2.py` (function `solve_evaporator_sets`) | The smart helper. Builds MULTIPLE `EvaporatorSet` objects at once, splits your juice flow between them, and balances them so every set works equally hard. This is what `main.py` actually calls — not `EvaporatorSet` by hand. |
| `EvaporatorSetIAPWS.py` | Not a real machine — a **benchmark/demo file**. It rebuilds `EvaporatorSet` using full IAPWS-97 `SteamStream` everywhere instead of the fast `EvaporatorSteam`, solves the same case both ways, and prints the difference. Last recorded run: same case, steam required came out 97,300 lb/hr (fast `EvaporatorSteam`) vs 97,316 lb/hr (full IAPWS-97) — about a 0.02% difference — but the IAPWS-97 version took **185x longer** to solve (77.7 seconds vs 0.4 seconds for 30 runs). That's the whole reason `EvaporatorSteam` exists and why every iterative solver in this codebase (`EvaporatorSet`, `Pan`, `PreEvaporator`, `Condenser`) uses it instead of full `SteamStream`. Not used by `main.py` — it's here to prove the design choice, not to run your factory. |

### Syrup to sugar (the pan floor / boiling house)

| File | What it is |
|---|---|
| `Pan.py` | One vacuum pan. Syrup (+ footing/seed) in, massecuite (sugar-crystal slurry) out. |
| `Centrifugal.py` | Spins massecuite apart into wet sugar crystals + molasses. |
| `Crystallizer_and_Reheater.py` (classes `Crystallizer`, `Reheater`) | Cools then reheats low-grade (C) massecuite before its final centrifugal spin — non-contact water, no mixing. |
| `FourBoilingDoubleMagma.py` | Wires a whole 4-boiling-scheme sugar house together (A1, A2, B, C pans + grain pans + all their centrifugals/crystallizers/reheaters). Feed it syrup and `Pan`/`Centrifugal` "recipe" objects, it builds and solves the whole floor. |
| `ThreeBoilingDoubleMagma.py` | Same idea, 3-boiling scheme (A, B, C pans + grain pans) instead of 4. |
| `pan_floor_excel.py` | Shared table-drawing helpers used by both boiling-scheme files' `.to_excel()`. You don't call this yourself. |

Pick ONE of `FourBoilingDoubleMagma` or `ThreeBoilingDoubleMagma` — whichever
matches the boiling scheme your factory actually runs.

### Steam users and steam makers

| File | What it is |
|---|---|
| `Deaerator.py` | Heats/de-airs boiler feedwater with a bit of live steam before it goes to the boiler. |
| `Turbine.py` | One steam turbine. Live steam in, shaft HP out, exhaust steam out — real isentropic-efficiency math. |
| `MillTurbines.py` | A whole set of mill-drive turbines, solved and reported together, sized from HP-per-ton-fiber. |
| `CanePrepTurbines.py` | Same idea for shredder/knife turbines. |
| `AuxillaryTurbines.py` | Same idea for anything else on a turbine (ID fans, FD fans, pumps) — you give HP directly instead of HP-per-ton-fiber. |
| `Boiler.py` | Burns the bagasse from `MillFloor`, tells you how much live steam the boiler room can make. |

### The water side

| File | What it is |
|---|---|
| `Condenser.py` | One barometric condenser — make vacuum on a pan or evaporator's vapor using cold injection water. |
| `CoolingTower.py` | Very small, simple cooling tower math (blowdown, evaporation, cool water out). |
| `CoolingTowerSystem.py` | Collects EVERY `Condenser` in the whole factory (from the pan floor + every evaporator set) and balances them against ONE shared cooling tower. |
| `condensate_balance.py` (classes `CondensateBalance`, `CondensateDemand`) | Lists how much clean/dirty condensate you HAVE (from all the units that make it) next to how much water you NEED (boiler feed, imbibition, wash water...). It does **not** auto-plumb anything — it just lays both lists side by side so you reconcile them yourself. |

### Report makers

| File | What it is |
|---|---|
| `excel_export.py` (class `SheetWriter`) | The shared Excel page-builder. Every `.to_excel()` method in this whole project uses `SheetWriter` for consistent look (title bar, section headers, tables, PFD image, page setup). |
| `steam_summary_excel.py` | One function — dumps a live-steam dictionary and an exhaust-steam dictionary onto their own summary sheet. |
| `mill_floor_diagram.py`, `clarification_diagram.py`, `juice_heater_diagram.py`, `four_boiling_diagram.py`, `three_boiling_diagram.py`, `evaporator_diagram.py`, `deaerator_diagram.py`, `cooling_tower_diagram.py`, `turbine_diagram.py` | The picture-drawers. Each one draws the process-flow-diagram (PFD) for its matching machine, in matplotlib. Called internally by that machine's `.generate_pfd()` / `.to_excel()` — you don't usually import these yourself. |

### Test and example

| File | What it is |
|---|---|
| `EvaporationOOP_testing.py` | Regression test suite for the evaporator math — 13 known cases checked against reference numbers from Birkett's book. Run it after touching evaporator code to make sure you didn't break the math. |
| `main.py` | **The author's own factory balance (St Mary Sugar).** This is a full worked example wiring every machine above into one real run. It is *not* a template you edit in place — it's here so you can see how a real factory chains all these pieces together, in the right order, with real-looking numbers. Read it, copy ideas from it, but build your OWN file for your OWN factory (see Section 3). |

---

## 3. Build Your Own `material_energy_balance.py`

Do not edit `main.py`. Make your own file (call it whatever you want — the
title just says `material_energy_balance.py` as an example name). Import
only the machines your factory actually has, in the order below, because
each machine needs the OUTPUT of the machine before it.

```python
from excel_export import new_workbook
wb = new_workbook()          # one Excel workbook, every machine writes its own sheet into it
```

**Step 1 — Mills.** Cane in, juice + bagasse out.

```python
from MillFloor import MillFloor
mills = MillFloor(cane_tpd=19000, cane_pol_pct=13.5, cane_fiber_pct=14,
                  imbibition_pct_on_cane=30, bagasse_pol_pct=2.1,
                  last_roll_purity=72, bagasse_moisture_pct=49.5,
                  mix_juice_purity=88, number_of_mills=6, juice_temp_F=90)
mills.to_excel(wb)
```

**Step 2 — Clarification.** Feed it `mills.mixed_juice_stream`.

```python
from Clarification import Clarification
clar = Clarification(mixed_juice_stream=mills.mixed_juice_stream,
                     cane_tpd=mills.cane_tpd, filter_wash_water_pct_on_cane=5,
                     filter_cake_pct_on_cane=5, filter_cake_pol_pct=2.4,
                     clarified_juice_purity=88.5)
clar.to_excel(wb)
```

**Step 3 — Juice heaters (optional).** Feed it `clar.limed_juice_cold_stream`.

```python
from SteamStream import SteamStream
from JuiceHeater import JuiceHeaterShellTube
from JuiceHeatingStation import JuiceHeatingStation

htr = JuiceHeaterShellTube(cold_stream=clar.limed_juice_cold_stream,
                           hot_stream=SteamStream(x=1, P=30),
                           juice_out_temp_degF=220, installed_area_ft2=11000,
                           steam_type=0)  # 0=Exhaust, 1=V1, 2=V2, 3=V3, 4=V4
station = JuiceHeatingStation(cold_stream=clar.limed_juice_cold_stream,
                              heaters=[htr], mode='series')
station.to_excel(wb)
```

**Step 4 — Make syrup, boil the pan floor.** You decide the target syrup
brix, back-calculate the syrup stream from clarified juice, then feed it
into whichever boiling scheme your factory runs.

```python
from SugarStream import SugarStream
from Pan import Pan
from Centrifugal import Centrifugal
from ThreeBoilingDoubleMagma import ThreeBoilingDoubleMagma  # or FourBoilingDoubleMagma

syrup = SugarStream.copy(clar.clarified_juice_stream)
syrup.brix = 65
syrup.flow_lb_per_hr = clar.clarified_juice_stream.flow_lb_per_hr * clar.clarified_juice_stream.brix / 65

pan_floor = ThreeBoilingDoubleMagma(
    syrup=syrup,
    A_pans=Pan(feed_streams=None, heating_surface_ft2=22500, inches_vacuum=23.5,
              supersaturation=1.2, head_ft=2, masse_brix=92, ml_purity=73,
              calandria_pressure_psia=21.696, steam_type=1, name='A Pans'),
    # ...B_pans, grain_pans, C_pans, and each centrifugal — same pattern,
    # see ThreeBoilingDoubleMagma.py's docstring / main.py for the full list
)
pan_floor.to_excel(wb)
```

**Step 5 — Evaporators.** Feed clarified (or pre-evaporated) juice in, get
syrup at your target brix out. Use `solve_evaporator_sets` — don't wire
`EvaporatorSet` by hand unless you only have one set.

```python
from multi_effect_solver_vers_2 import solve_evaporator_sets
from EvaporatorSet import sets_to_excel

evap_station = solve_evaporator_sets(
    juice_brix=clar.clarified_juice_stream.brix,
    juice_purity=clar.clarified_juice_stream.purity,
    juice_flow_lb_per_hr=clar.clarified_juice_stream.flow_lb_per_hr,
    juice_temp_deg_F=clar.clarified_juice_stream.temp_deg_F,
    target_brix_out=syrup.brix,
    set_configs=[
        {"name": "Set 1", "effect_areas_ft2": [25000]*4,
         "supply_steam_psia": 30, "last_effect_psia": 2.4},
    ],
)
sets_to_excel(evap_station, workbook=wb)
```

**Step 6 — Steam side.** Deaerator, turbines, boiler — in that order,
because the boiler needs feedwater temperature FROM the deaerator, and
turbines need a live steam source you define yourself.

```python
from Deaerator import Deaerator
from MillTurbines import MillTurbines
from Boiler import Boiler

da = Deaerator(deaerator_psig=10, water_in_deg_F=200, water_in_lb_hr=800_000)
da.to_excel(wb)

trbs = MillTurbines(hp_ton_fiber_hr=[18,16,16,16,16,18],
                    isentropic_efficiency=[50]*6,
                    live_steam_object=SteamStream(P=180, x=1),
                    exhaust_psia=30, tons_fiber_hr=mills.cane_fiber_pct/100*mills.cane_tph)
trbs.to_excel(wb)

blrs = Boiler(bagasse=mills.bagasse_stream, efficiency=60, pressure_psig=185,
             feed_water_temp=da.water_out.T, capacity=900_000)
blrs.to_excel(wb)
```

**Step 7 — Cooling tower.** Collect every `Condenser` in the factory (pan
floor gives you a ready list, evaporator sets each carry their own).

```python
from CoolingTowerSystem import CoolingTowerSystem

condensers = pan_floor.pan_condensers + [(s.name, s.condenser) for s in evap_station]
ctwrs = CoolingTowerSystem(condensers=condensers, cool_water_temp_F=85, percent_blowdown=10)
ctwrs.to_excel(wb)
```

**Step 8 — Condensate balance.** Gather `clean_condensate`/`dirty_condensate`
off every unit that has it, list your water demands, and let it lay them
side by side.

```python
from condensate_balance import CondensateBalance, CondensateDemand

clean = {'Pan Floor': pan_floor.clean_condensate, 'Juice Heaters': station.clean_condensate}
dirty = {'Pan Floor': pan_floor.dirty_condensate, 'Juice Heaters': station.dirty_condensate}
demands = [CondensateDemand('Boiler Feed Water', flow_lb_hr=da.water_in_lb_hr,
                            temp_F=da.water_in_deg_F, method='blended')]

cb = CondensateBalance(clean, dirty, demands, well_water_temp_F=70)
cb.to_excel(wb)
```

**Step 9 — Save it.**

```python
wb.save("my_factory_balance.xlsx")
```

That's the whole recipe. `main.py` does exactly this, just with the author's
own numbers and every optional extra (steam summary sheet, both juice
heaters, exhaust/live steam bookkeeping) filled in — read it side by side
with this guide once you're stuck.

---

## 4. Rules Of The Cave

- **Order matters.** A machine needs its input stream to already exist.
  Can't clarify juice that hasn't been milled yet.
- **`steam_type`** (used on `Pan` and `JuiceHeaterShellTube`) is just an
  integer tag: `0=Exhaust, 1=V1, 2=V2, 3=V3, 4=V4`. It doesn't change the
  heat-transfer math — it's how `clean_condensate`/`dirty_condensate` and
  the `total_V1_steam_lb_hr`-style properties know which steam source a
  unit used.
- **Most machines solve themselves at construction.** No `.solve()` call
  needed. The two exceptions: call `.adjust_pressure_profile()` on an
  `EvaporatorSet` you built by hand, and use `solve_evaporator_sets()`
  instead of building `EvaporatorSet` by hand whenever you have more than
  one set.
- **`.to_excel(wb)` always shares one workbook.** Every class takes the
  same `wb` object and adds its own sheet — call it on everything you want
  in the final report, then `wb.save(...)` once at the very end.
- **Copy a stream before mutating it** if the original is still needed
  elsewhere — use `SugarStream.copy(stream)` rather than editing a stream
  object another machine already holds a reference to.

---

## 5. Install

```
pip install -r requirements.txt
```

Needs: `numpy`, `iapws`, `matplotlib`, `openpyxl`, `pillow`, Python 3.10+.

## 6. Run Things

```
python EvaporationOOP_testing.py     # check the evaporator math still passes its 13 known cases
python main.py                       # run the author's own factory example end to end
```

## 7. Units

| Quantity | Unit |
|---|---|
| Flow | lb/hr (tons/hr = flow / 2000) |
| Pressure | psia internally; psig / inHg vacuum for display |
| Temperature | °F |
| Heat duty | BTU/hr |
| Heating/heat-transfer surface | ft² |
| Brix | % (mass dissolved solids / total mass) |
| Purity | % (pol / brix × 100) |
