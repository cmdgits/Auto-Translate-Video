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
local_config = project_root / "config.yaml"
if local_config.exists():
    datas.append((str(local_config), "."))
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

cuda_dll_names = {
    "cublas64_12.dll",
    "cublasLt64_12.dll",
    "cudart64_12.dll",
    "cudnn64_8.dll",
    "cudnn64_9.dll",
    "cudnn_ops_infer64_8.dll",
    "cudnn_cnn_infer64_8.dll",
    "nvrtc64_120_0.dll",
    "nvrtc64_120_0.alt.dll",
    "nvrtc-builtins64_129.dll",
}
for search_dir in [
    project_root / "tools" / "Python312" / "Lib" / "site-packages" / "ctranslate2",
    project_root / "tools" / "Python312" / "Lib" / "site-packages" / "nvidia" / "cuda_runtime" / "bin",
    project_root / "tools" / "Python312" / "Lib" / "site-packages" / "nvidia" / "cuda_nvrtc" / "bin",
    project_root / "tools" / "Python312" / "Lib" / "site-packages" / "nvidia" / "cublas" / "bin",
    project_root / "tools" / "Python312" / "Lib" / "site-packages" / "nvidia" / "cudnn" / "bin",
]:
    if search_dir.exists():
        for dll_path in search_dir.glob("*.dll"):
            if dll_path.name in cuda_dll_names or dll_path.name.startswith("cudnn_"):
                binaries.append((str(dll_path), "."))

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
