# Building the Windows executable

The GUI uses the standard-library `tkinter`, and process monitoring uses
`psutil`. There are no other runtime dependencies.

```powershell
python -m pip install psutil pyinstaller

# GUI executable (windowed)
python -m PyInstaller --onefile --windowed --icon assets\icon.ico --name ReadyOrNot-ModCompatTester run_gui.py

# CLI executable (console)
python -m PyInstaller --onefile --console --name ReadyOrNot-ModCompatTester-cli run_cli.py
```

The output executables are placed in `dist/`.
