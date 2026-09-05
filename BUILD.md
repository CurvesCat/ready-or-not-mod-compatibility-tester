# Building a release

RoNCT's GUI is a PySide6/Qt application that is packaged with PyInstaller as a
single executable. repak, UAssetCLI, and a portable .NET runtime are shipped
next to the executable under `tools/`.

## Prerequisites

- Windows 10/11
- Python 3.10+ with the dependencies in `requirements.txt`
- `pyinstaller` (tested with 6.x)

```powershell
python -m pip install -r requirements.txt pyinstaller
```

## Build the executable

From the repository root:

```powershell
python -m PyInstaller packaging\RoNCT.spec --noconfirm --clean
```

The onedir output is `dist\ReadyOrNot-ModCompatTester\`; the entry point is
`dist\ReadyOrNot-ModCompatTester\ReadyOrNot-ModCompatTester.exe`.

`packaging/build_release.ps1` automates the rest:

```powershell
.\packaging\build_release.ps1 -RepoRoot C:\path\to\repo -ToolsRoot C:\path\to\tools
```

It creates a clean release folder and a versioned ZIP containing:

```text
ReadyOrNot-ModCompatTester.exe
README.md
CHANGELOG.md
LICENSE
THIRD_PARTY_NOTICES.txt
tools\repak\
tools\uassetcli\
tools\dotnet\
```

No Python, PySide6 source tree, tests, caches, reports, backups, or user
configuration are included in the release.

## Notes

- The legacy CLI (`run_cli.py`, `ron_mod_tester/cli.py`) is kept as history and
  is intentionally not packaged.
- The executable stores generated files next to itself:
  `reports/`, `quarantine/`, `backup/`, `cache/`, and `debug.log`.
