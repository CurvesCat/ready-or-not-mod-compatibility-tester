# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the RoNCT Windows GUI."""

from pathlib import Path


project_root = Path(SPECPATH).resolve().parent  # type: ignore[name-defined]

a = Analysis(
    [str(project_root / "run_gui.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[(str(project_root / "assets"), "assets")],
    hiddenimports=[
        "ron_mod_tester.pipeline.v2_gui",
        "ron_mod_tester.planner.planner",
        "ron_mod_tester.planner.rules",
        "ron_mod_tester.static.analyzer",
        "ron_mod_tester.static.deps",
        "ron_mod_tester.nexus.client",
        "ron_mod_tester.nexus.cache",
        "ron_mod_tester.nexus.identify",
        "ron_mod_tester.nexus.mapping",
        "ron_mod_tester.nexus.requirements",
        "ron_mod_tester.calibrate",
        "ron_mod_tester.tutorial",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ReadyOrNot-ModCompatTester",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(project_root / "assets" / "icon.ico")],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    name="ReadyOrNot-ModCompatTester",
)
