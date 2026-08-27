# Material & Energy Balance (OOP Python)

Object-oriented material and energy balance tools for raw cane sugar factories, plus a Streamlit app for the calculations Louisiana cane sugar engineers reach for most.

**Requires:** Python 3.12+
Older versions may work, but I haven't tested them.

This repo has two purposes.

## Reason 1
To give other sugar mill engineers easy-to-use Python objects (classes) for material and energy balances — either around a single part of the factory, or chained together for a full-factory calculation.

## Reason 2
To host an easy-to-use Streamlit application covering most of what cane sugar engineers in Louisiana need to calculate. The app is live here: [Material & Energy Balance app](https://materialenergybalanceooppython-5l9b6soqkfns37wsgf9wvf.streamlit.app/). You're also welcome to clone the repo and run it locally.

## Installation

### macOS / Linux (bash)

```bash
git clone https://github.com/codyeaves78-bit/Material_Energy_Balance_OOP_python
cd Material_Energy_Balance_OOP_python

# create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install requirements, then launch the app
pip install -r requirements.txt
streamlit run streamlit_app.py
```

### Windows (PowerShell)

```powershell
git clone https://github.com/codyeaves78-bit/Material_Energy_Balance_OOP_python
cd Material_Energy_Balance_OOP_python

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
