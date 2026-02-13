# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for CWS: Civil War Strategy Online

import sys

block_cipher = None

a = Analysis(
    ['dev/python/main.py'],
    pathex=['dev/python'],
    binaries=[],
    datas=[
        ('CITIES.GRD', '.'),
        ('CWS.INI', '.'),
        ('CWS.CFG', '.'),
        ('CWSLEAD.DAT', '.'),
        ('ALTLEAD.DAT', '.'),
        ('ALTMAP.GRD', '.'),
        ('ALTMAP.INI', '.'),
        ('MTN.VGA', '.'),
        ('CWSICON.VGA', '.'),
        ('FACE1.VGA', '.'),
        ('FACE2.VGA', '.'),
        ('FACE3.VGA', '.'),
        ('FACE4.VGA', '.'),
        ('FACE5.VGA', '.'),
        ('FORT0.VGA', '.'),
        ('FORT1.VGA', '.'),
        ('FORT2.VGA', '.'),
        ('HISCORE.CWS', '.'),
        ('cws.ico', '.'),
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
    icon='cws.ico',
)

# Mac .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='CWS Civil War Strategy Online.app',
        icon='cws.ico',
        bundle_identifier='com.cws.civilwarstrategy',
        info_plist={
            'CFBundleDisplayName': 'CWS: Civil War Strategy Online',
            'CFBundleShortVersionString': '1.7',
            'NSHighResolutionCapable': 'True',
        },
    )
