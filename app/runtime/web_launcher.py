from __future__ import annotations

import sys
import threading
import webbrowser
from pathlib import Path
from socket import socket

import uvicorn


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def bundled_config_path() -> Path | None:
    candidates = [
        runtime_root() / "config.yaml",
        runtime_root() / "config.example.yaml",
        Path(getattr(sys, "_MEIPASS", runtime_root())) / "config.yaml",
        Path(getattr(sys, "_MEIPASS", runtime_root())) / "config.example.yaml",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def add_bundled_ffmpeg_to_path() -> None:
    import os

    bundle_root = Path(getattr(sys, "_MEIPASS", runtime_root()))
    candidates = [
        runtime_root() / "tools" / "ffmpeg" / "bin",
        bundle_root / "tools" / "ffmpeg" / "bin",
    ]
    for candidate in candidates:
        if (candidate / "ffmpeg.exe").exists():
            os.environ["PATH"] = f"{candidate}{os.pathsep}{os.environ.get('PATH', '')}"
            break


def add_runtime_dll_dirs() -> None:
    import os

    candidates = [runtime_root(), Path(getattr(sys, "_MEIPASS", runtime_root()))]
    python_root = runtime_root() / "tools" / "Python312" / "Lib" / "site-packages" / "nvidia"
    candidates.extend([
        python_root / "cublas" / "bin",
        python_root / "cudnn" / "bin",
        python_root / "cuda_runtime" / "bin",
        python_root / "cuda_nvrtc" / "bin",
    ])
    for candidate in candidates:
        if not candidate.exists():
            continue
        os.environ["PATH"] = f"{candidate}{os.pathsep}{os.environ.get('PATH', '')}"
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(str(candidate))
            except OSError:
                pass


def choose_available_port(host: str, preferred_port: int) -> int:
    for port in range(preferred_port, preferred_port + 20):
        with socket() as probe:
            if probe.connect_ex((host, port)) != 0:
                return port
    return preferred_port


def main() -> None:
    import multiprocessing
    import os

    multiprocessing.freeze_support()
    host = "127.0.0.1"
    port = choose_available_port(host, 8001)
    add_runtime_dll_dirs()
    add_bundled_ffmpeg_to_path()
    os.environ.setdefault("AUTOTRANSLATE_WORKER_BACKEND", "thread")
    config_path = bundled_config_path()
    if config_path:
        os.environ.setdefault("AUTOTRANSLATE_CONFIG", str(config_path))
    threading.Timer(1.2, lambda: webbrowser.open(f"http://{host}:{port}/")).start()
    uvicorn.run("app.web.main:app", host=host, port=port, reload=False, factory=False)


if __name__ == "__main__":
    main()
