# -*- mode: python ; coding: utf-8 -*-
import os
import sys

project_root = os.path.abspath(SPECPATH) if 'SPECPATH' in locals() else os.path.abspath(os.getcwd())

datas = [
    ('assets', 'assets'),
    ('.env.example', '.'),
]

# If QuizAssistant.exe exists in dist, bundle it inside the installer
quiz_exe = os.path.join(project_root, 'dist', 'QuizAssistant.exe')
if os.path.exists(quiz_exe):
    datas.append(('dist/QuizAssistant.exe', '.'))

a = Analysis(
    ['installer.py'],
    pathex=['src', '.'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'shortcut_manager',
        'src.shortcut_manager',
        'constants',
        'src.constants',
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AI-Quiz-Assistant-Setup',
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
    icon=os.path.join(project_root, 'assets', 'icon.ico'),
    version=os.path.join(project_root, 'packaging', 'version_info.txt'),
)
