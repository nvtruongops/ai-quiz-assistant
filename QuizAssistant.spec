# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['run.pyw'],
    pathex=['src'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'src.main',
        'src.config_manager',
        'src.logger',
        'src.screenshot_manager',
        'src.gemini_client',
        'src.request_manager',
        'src.popup_manager',
        'src.hotkey_listener',
        'src.system_tray',
        'src.models',
        'src.settings_manager',
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
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
    icon='icon.ico',
    version='version_info.txt',
)
