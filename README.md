# Cane Sugar Factory Material & Energy Balance

Python tools for calculating first-pass material and energy balances around a
raw cane sugar factory — milling, clarification, multiple-effect evaporation,
pan boiling, and steam/cogeneration — built with Louisiana mills in mind.

Use it as an object-oriented library for your own calculations, or through the
Streamlit app (linked below), which runs online or locally on your own machine.

Built by a sugar mill engineer for sugar mill engineers. It's meant for
screening and first-pass estimates — calibrate against your own plant data
before trusting any single number.

**Requires:** Python 3.12+
Older versions may work, but I haven't tested them.

This repo has two purposes.

## Reason 1
To give other sugar mill engineers easy-to-use Python objects (classes) for material and energy balances — either around a single part of the factory, or chained together for a full-factory calculation.

## Reason 2
To host an easy-to-use Streamlit application covering most of what cane sugar engineers in Louisiana need to calculate. The app is live here: https://cane-sugar-mill-material-energy-balance-fbl69dwu8opxateg3jsgnn.streamlit.app/ You're also welcome to clone the repo and run it locally.

## Installation

### macOS / Linux (bash)

```bash
git clone https://github.com/codyeaves78-bit/cane-sugar-mill-material-energy-balance
cd cane-sugar-mill-material-energy-balance

# create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install requirements, then launch the app
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### Windows (PowerShell)

```powershell
git clone https://github.com/codyeaves78-bit/cane-sugar-mill-material-energy-balance
cd cane-sugar-mill-material-energy-balance

# create and activate a virtual environment
python -m venv .venv
.venv\Scripts\Activate.ps1

# install requirements, then launch the app
pip install -r requirements.txt
streamlit run streamlit_app.py
```

If activation fails with a "running scripts is disabled on this system" error, allow scripts for your user once, then re-run the activate line:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Windows users may also need Git installed first: [git-scm.com/downloads](https://git-scm.com/downloads).

## Documentation
See the [Documentation](documentation/) folder for the User Guide and worked examples.
