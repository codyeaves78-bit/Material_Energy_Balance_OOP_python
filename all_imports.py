r"""
Convenience import for ad-hoc ipython/notebook sessions.

Usage
-----
From inside this repo:
    from all_imports import *

From anywhere else on disk:
    import sys
    sys.path.insert(0, r"C:\cane-sugar-mill-material-energy-balance")
    from all_imports import *

Or import one name specifically, e.g.:
    from all_imports import Turbine

This pulls every public class/function out of the "library" modules in this
folder (equipment models, stream objects, helper functions) into one
namespace. Scripts that run real work at import time -- main.py,
streamlit_app.py, the *_balance.py drivers, examples.py, test files, etc. --
are deliberately left out; import those directly if you need them.
"""

import importlib
import warnings

# Modules whose top level is safe to import (only def/class/constants --
# no top-level computation, plotting, or file I/O side effects).
_MODULES = [
    # equipment / process models
    "AuxillaryTurbines",
    "Bagasse",
    "Boiler",
    "CanePrepTurbines",
    "Centrifugal",
    "Clarification",
    "Condenser",
    "CoolingTower",
    "CoolingTowerSystem",
    "Crystallizer_and_Reheater",
    "Deaerator",
    "EvaporatorSet",
    "EvaporatorSetIAPWS",
    "FourBoilingDoubleMagma",
    "JuiceHeater",
    "JuiceHeatingStation",
    "Massecuite",
    "MillFloor",
    "MillTurbines",
    "Pan",
    "PreEvaporator",
    "ThreeBoiling",
    "ThreeBoilingDoubleMagma",
    "Turbine",
    "TwoBoiling",
    "condensate_balance",
    "multi_effect_solver_scipy",
    "multi_effect_solver_vers_2",
    # streams / streams helpers
    "SteamStream",
    "SugarStream",
    "condensate_utils",
    "evaporator_functions",
    "sugar_stream_properties",
    # excel / diagram helpers
    "excel_export",
    "steam_summary_excel",
    "boiler_streamlit_tables",
    "clarification_diagram",
    "cooling_tower_diagram",
    "cooling_tower_streamlit_tables",
    "deaerator_diagram",
    "evaporator_diagram",
    "evaporator_streamlit_tables",
    "four_boiling_diagram",
    "juice_heater_diagram",
    "mill_floor_diagram",
    "three_boiling_diagram",
    "three_boiling_single_magma_diagram",
    "turbine_diagram",
    "two_boiling_diagram",
]

# Deliberately excluded (run real work / have side effects at import time,
# or are one-off scripts rather than reusable modules):
#   Birkett_Balance_11032017, SMSC_Balance, Evaporator, SteamStream demo bits,
#   evaporator_scipy_testing, examples, main, pan_floor_excel,
#   pan_floor_streamlit_table, streamlit_app, test_evaps,
#   EvaporationOOP_testing, exhaustive_test

_seen = {}  # name -> module it came from, for collision warnings

for _modname in _MODULES:
    try:
        _mod = importlib.import_module(_modname)
    except Exception as exc:  # noqa: BLE001 - surface but don't abort the rest
        warnings.warn(f"all_imports: skipped '{_modname}' ({exc!r})")
        continue

    _names = getattr(_mod, "__all__", None)
    if _names is None:
        # Only grab classes/functions actually defined in this module --
        # not stuff it imported (numpy as np, classes from other project
        # files, etc.), which would otherwise flood this with false
        # "collision" warnings for names that are really the same object.
        _names = [
            n for n in dir(_mod)
            if not n.startswith("_")
            and getattr(getattr(_mod, n), "__module__", None) == _modname
        ]

    for _name in _names:
        _obj = getattr(_mod, _name)
        if _name in _seen and _seen[_name][1] is not _obj:
            warnings.warn(
                f"all_imports: '{_name}' from '{_modname}' shadows the one "
                f"already imported from '{_seen[_name][0]}'"
            )
        _seen[_name] = (_modname, _obj)
        globals()[_name] = _obj

for _tmp in ("_modname", "_mod", "_names", "_name", "_obj", "_tmp"):
    globals().pop(_tmp, None)
