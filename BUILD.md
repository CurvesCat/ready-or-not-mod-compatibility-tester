# Building the Windows executable

The v0.3 GUI is built with **PySide6 (Qt for Python)** and process monitoring
uses `psutil`. There is no tkinter dependency anymore.

```powershell
python -m pip install -r requirements.txt pyinstaller

# GUI executable (windowed, one file)
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --icon assets\icon.ico ^
  --name ReadyOrNot-ModCompatTester ^
  --add-data "assets;assets" ^
  --hidden-import ron_mod_tester.pipeline.v2_gui ^
  run_gui.py
```

The output executable is placed in `dist/`.

For a release zip, place the following next to the executable:

- `tools\repak\repak.exe`
- `tools\dotnet\dotnet.exe`
- `tools\uassetcli\UAssetCLI.dll`

The legacy CLI source (`run_cli.py`, `ron_mod_tester/cli.py`) is kept as history
but is not built or shipped with releases.
