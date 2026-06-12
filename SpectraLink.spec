# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all

# Detect the operating system and set the correct icon from the Images folder
if sys.platform == 'win32':
    icon_file = os.path.join('Images', 'SpectraLink_Icon.ico')
elif sys.platform == 'darwin':
    icon_file = os.path.join('Images', 'SpectraLink_Icon.icns')
else:
    icon_file = None


# Collect all hidden dependencies for the scientific stack
datas = [('Images', 'Images'), ('config', 'config')]
binaries = []
hiddenimports = [
    'scipy.signal', 
    'pandas', 
    'PyQt6', 
    'matplotlib.backends.backend_qt6agg', 
    'requests',
    'ui.bug_report_dialog',
    'processors.abs_processor',
    'processors.ea_processor',
    'processors.abs_temp_processor',
    'processors.ea_temp_processor'
]

for pkg in ['scipy', 'pandas', 'matplotlib']:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[os.getcwd()],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# ----------------- 1. ADD THIS SPLASH BLOCK -----------------
splash = None
if sys.platform == 'win32':
    splash = Splash(
        os.path.join('Images', 'SpectraLink Splash Screen.png'), 
        binaries=a.binaries,
        datas=a.datas,
        text=None,
        minify_script=True,
        always_on_top=True,
    )
# ------------------------------------------------------------

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe_args = [pyz, a.scripts]
if splash:
    exe_args.extend([splash, splash.binaries])

exe = EXE(
    *exe_args,
    exclude_binaries=True,
    icon=icon_file,
    name='SpectraLink',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, 
    disable_windowed_traceback=False,
    argv_emulation=True if sys.platform == 'darwin' else False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    *([splash.binaries] if splash else []),
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SpectraLink',
)

if sys.platform == 'darwin':
    app = BUNDLE(
        coll,
        name='SpectraLink.app',
        icon=icon_file,
        bundle_identifier='org.spectralink.app',
    )