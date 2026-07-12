# -*- mode: python ; coding: utf-8 -*-
# 安裝／解除安裝程式：Setup-TerminalPet.exe（onefile，僅執行一次，保留主控台方便顯示文字回饋）

a = Analysis(
    ['../installer/setup.py'],
    pathex=[],
    binaries=[],
    datas=[],
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
    a.binaries,
    a.datas,
    [],
    name='Setup-TerminalPet',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    icon='icon.ico',
)
