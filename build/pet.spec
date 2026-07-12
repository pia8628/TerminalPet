# -*- mode: python ; coding: utf-8 -*-
# GUI 桌寵本體：TerminalPet.exe（onedir，無主控台）

a = Analysis(
    ['../pet.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../assets/wolf_thinking.png', 'assets'),
        ('../assets/wolf_working.png', 'assets'),
        ('../assets/wolf_waiting.png', 'assets'),
        ('../assets/wolf_done.png', 'assets'),
        ('../assets/wolf_sleeping.png', 'assets'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='TerminalPet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='TerminalPet',
)
