# -*- mode: python ; coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

project_root = Path.cwd()

datas = [
    (str(project_root / "app" / "web" / "templates"), "app/web/templates"),
    (str(project_root / "app" / "web" / "static"), "app/web/static"),
    (str(project_root / "config.example.yaml"), "."),
]
bundled_tiny_model = project_root / "models" / "faster-whisper-tiny"
if bundled_tiny_model.exists():
    datas.append((str(bundled_tiny_model), "models/faster-whisper-tiny"))
datas += collect_data_files("faster_whisper", includes=["assets/*"])

binaries = []
ffmpeg_dir = project_root / "tools" / "ffmpeg" / "bin"
if ffmpeg_dir.exists():
    for binary_name in ("ffmpeg.exe", "ffprobe.exe"):
        binary_path = ffmpeg_dir / binary_name
        if binary_path.exists():
            binaries.append((str(binary_path), "tools/ffmpeg/bin"))

hiddenimports = [
    "app.web.main",
    "app.core.celery_app",
    "app.core.task_runner",
    "app.translate.gemini_backend",
    "app.translate.llm_http_backend",
    "app.translate.libretranslate_backend",
    "app.translate.mymemory_backend",
    "app.tts.edge_tts_backend",
    "faster_whisper.assets",
]

a = Analysis(
    [str(project_root / "app" / "runtime" / "web_launcher.py")],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "matplotlib", "notebook", "IPython"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AutoTranslateVideo",
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
    icon=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AutoTranslateVideo",
)
