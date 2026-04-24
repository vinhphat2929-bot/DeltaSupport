# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PIL import Image
from PyInstaller.utils.hooks import collect_all


PROJECT_ROOT = Path(globals().get("SPECPATH", ".")).resolve()
tzdata_datas, tzdata_binaries, tzdata_hiddenimports = collect_all("tzdata")
zip2tz_datas, zip2tz_binaries, zip2tz_hiddenimports = collect_all("zip2tz")


def resolve_build_icon():
    icon_candidates = [
        PROJECT_ROOT / "data" / "app_v3.ico",
        PROJECT_ROOT / "data" / "app.ico",
    ]
    for candidate in icon_candidates:
        if candidate.exists():
            return [str(candidate)]

    png_icon = PROJECT_ROOT / "data" / "icon.png"
    if not png_icon.exists():
        return None

    generated_icon = PROJECT_ROOT / "build" / "pyinstaller_app_icon.ico"
    generated_icon.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(png_icon) as icon_image:
        icon_image.save(
            generated_icon,
            format="ICO",
            sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)],
        )
    return [str(generated_icon)]


exe_icon = resolve_build_icon()


a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=tzdata_binaries + zip2tz_binaries,
    datas=[('data', 'data'), *tzdata_datas, *zip2tz_datas],
    hiddenimports=[
        'zoneinfo',
        '_zoneinfo',
        *tzdata_hiddenimports,
        *zip2tz_hiddenimports,
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
    a.binaries,
    a.datas,
    [],
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=exe_icon,
)
