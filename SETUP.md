# Getting Started — Run the App Locally

These steps get you from a clean Windows or Mac/Linux machine to the Streamlit
app running in your browser. Pick the section that matches your machine.

Repo: `https://github.com/codyeaves78-bit/Material_Energy_Balance_OOP_python`

---

## Windows (PowerShell)

Open **PowerShell** (Start menu → type `PowerShell` → Enter) and run these in order.

### 1. Install Git

```powershell
winget install --id Git.Git -e --source winget
```

Close and reopen PowerShell after this finishes, so it picks up the new `git`
command. Check it worked:

```powershell
git --version
```

No `winget`? Download the installer from https://git-scm.com/download/win and
run it, accepting the defaults.

### 2. Install Python

```powershell
winget install --id Python.Python.3.12 -e --source winget
```

Close and reopen PowerShell again, then check:

```powershell
python --version
```

If that prints a version (e.g. `Python 3.12.x`), you're good. No `winget`?
Download from https://www.python.org/downloads/ — on the first install
screen, **check the "Add python.exe to PATH" box** before clicking Install.

### 3. Clone the repo

Pick (or create) a folder to work in, then:

```powershell
cd $HOME\Documents
git clone https://github.com/codyeaves78-bit/Material_Energy_Balance_OOP_python.git
cd Material_Energy_Balance_OOP_python
```

### 4. Create a virtual environment and install requirements

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If `Activate.ps1` is blocked with a script-execution error, run this once
(only for the current window, doesn't change any system setting) and then
retry the activate line:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Your prompt should now start with `(.venv)` — that means the virtual
environment is active.

### 5. Launch the app

```powershell
streamlit run streamlit_app.py
```

Streamlit prints a `Local URL` (usually `http://localhost:8501`) and should
open it in your default browser automatically. If not, copy that URL into
your browser.

To stop the app later, click back in the PowerShell window and press
`Ctrl+C`. Next time you come back, you only need to redo steps 4's
`.venv\Scripts\Activate.ps1` line (skip the `pip install`) and step 5.

---

## macOS / Linux (Bash)

Open a terminal and run these in order.

### 1. Install Git

**macOS** — Git ships with the Xcode Command Line Tools:

```bash
git --version
```

If it's not installed, this command itself will prompt you to install the
Command Line Tools — accept and wait for it to finish.

**Linux (Debian/Ubuntu)**:

```bash
sudo apt update && sudo apt install -y git
```

**Linux (Fedora/RHEL)**:

```bash
sudo dnf install -y git
```

### 2. Install Python

Check what you already have first — most Macs and modern Linux distros ship
Python 3:

```bash
python3 --version
```

You need 3.10 or newer. If it's missing or too old:

**macOS** (using [Homebrew](https://brew.sh)):

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"   # if you don't have brew yet
brew install python
```

**Linux (Debian/Ubuntu)**:

```bash
sudo apt install -y python3 python3-venv python3-pip
```

**Linux (Fedora/RHEL)**:

```bash
sudo dnf install -y python3 python3-pip
```

### 3. Clone the repo

```bash
cd ~/Documents
git clone https://github.com/codyeaves78-bit/Material_Energy_Balance_OOP_python.git
cd Material_Energy_Balance_OOP_python
```

### 4. Create a virtual environment and install requirements

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Your prompt should now start with `(.venv)` — that means the virtual
environment is active.

### 5. Launch the app

```bash
streamlit run streamlit_app.py
```

Streamlit prints a `Local URL` (usually `http://localhost:8501`) and should
open it in your default browser automatically. If not, copy that URL into
your browser.

To stop the app later, click back in the terminal and press `Ctrl+C`. Next
time you come back, you only need to redo step 4's `source
.venv/bin/activate` line (skip the `pip install`) and step 5.

---

## Quick reference — every time after the first setup

Once steps 1–4 above are done once, coming back later is just:

**Windows (PowerShell)**

```powershell
cd $HOME\Documents\Material_Energy_Balance_OOP_python
.venv\Scripts\Activate.ps1
streamlit run streamlit_app.py
```

**macOS/Linux (Bash)**

```bash
cd ~/Documents/Material_Energy_Balance_OOP_python
source .venv/bin/activate
streamlit run streamlit_app.py
```
