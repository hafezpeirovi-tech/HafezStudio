# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
from PyInstaller.utils.hooks import copy_metadata

datas = [('C:/Users/1SKY.IR/.n8n/products/HafezStudio/engine/models', 'models'), ('C:/Users/1SKY.IR/.n8n/products/HafezStudio/engine/src/hermes_video/subtitle_glossary.txt', '.')]
binaries = []
hiddenimports = ['autocut', 'glass_storyboard', 'glass_semantic_cards']
datas += copy_metadata('faster-whisper')
datas += copy_metadata('ctranslate2')
tmp_ret = collect_all('faster_whisper')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('ctranslate2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('arabic_reshaper')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('bidi')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['C:/Users/1SKY.IR/.n8n/products/HafezStudio/engine/src/hermes_video/studio_cli.py'],
    pathex=['C:/Users/1SKY.IR/.n8n/products/HafezStudio/engine/src/hermes_video'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['ctranslate2.converters', 'torch', 'torchvision', 'torchaudio', 'transformers', 'pandas', 'matplotlib', 'jinja2'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='hermes-engine',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='hermes-engine',
)
