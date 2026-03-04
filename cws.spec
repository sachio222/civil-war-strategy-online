# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for CWS: Civil War Strategy Online

import sys

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['src'],
    binaries=[],
    datas=[
        ('data/CITIES.GRD', '.'),
        ('data/CWS.INI', '.'),
        ('data/CWS.CFG', '.'),
        ('data/CWSLEAD.DAT', '.'),
        ('data/ALTLEAD.DAT', '.'),
        ('data/ALTMAP.GRD', '.'),
        ('data/ALTMAP.INI', '.'),
        ('data/MTN.VGA', '.'),
        ('data/CWSICON.VGA', '.'),
        ('data/FACE1.VGA', '.'),
        ('data/FACE2.VGA', '.'),
        ('data/FACE3.VGA', '.'),
        ('data/FACE4.VGA', '.'),
        ('data/FACE5.VGA', '.'),
        ('data/FORT0.VGA', '.'),
        ('data/FORT1.VGA', '.'),
        ('data/FORT2.VGA', '.'),
        ('data/HISCORE.CWS', '.'),
        ('data/cws.ico', '.'),
    ],
    hiddenimports=['pygame', 'pygame.mixer'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='CWS Civil War Strategy Online',
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
    icon='data/cws.ico',
)

# Mac .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='CWS Civil War Strategy Online.app',
        icon='data/cws.ico',
        bundle_identifier='com.cws.civilwarstrategy',
        info_plist={
            'CFBundleDisplayName': 'CWS: Civil War Strategy Online',
            'CFBundleShortVersionString': '1.7',
            'NSHighResolutionCapable': 'True',
        },
    )
