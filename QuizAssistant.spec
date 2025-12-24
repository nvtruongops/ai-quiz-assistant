# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['run.pyw', 'src/main.py', 'src/config_manager.py', 'src/logger.py', 'src/screenshot_manager.py', 'src/gemini_client.py', 'src/request_manager.py', 'src/popup_manager.py', 'src/hotkey_listener.py', 'src/system_tray.py', 'src/models.py'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[],
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
    name='QuizAssistant',
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
)
