# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['/Users/theodorelau/Desktop/apollo/client/extractor/obfuscated/apollo_extractor.py'],
    pathex=[],
    binaries=[],
    datas=[('/Users/theodorelau/Desktop/apollo/client/extractor/obfuscated/pyarmor_runtime_000000', 'pyarmor_runtime_000000')],
    hiddenimports=['pyarmor_runtime_000000', 'json', 'os', 'platform', 'sqlite3', 'hashlib', 'urllib.request', 'urllib.error', 'tkinter', 'tkinter.ttk', 'tkinter.messagebox', 'tkinter.scrolledtext', 'pathlib', 'secrets', 'uuid'],
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
    name='ApolloExtractor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['/Users/theodorelau/Desktop/apollo/client/extractor/icon.icns'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ApolloExtractor',
)
app = BUNDLE(
    coll,
    name='ApolloExtractor.app',
    icon='/Users/theodorelau/Desktop/apollo/client/extractor/icon.icns',
    bundle_identifier=None,
)
