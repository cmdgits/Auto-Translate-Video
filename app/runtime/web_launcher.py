from __future__ import annotations

import sys
import threading
import webbrowser
from pathlib import Path

import uvicorn


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[2]


def bundled_config_path() -> Path | None:
    candidates = [
        runtime_root() / "config.yaml",
        runtime_root() / "config.example.yaml",
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


def main() -> None:
    import multiprocessing

    multiprocessing.freeze_support()
    host = "127.0.0.1"
    port = 8001
    add_bundled_ffmpeg_to_path()
    config_path = bundled_config_path()
    if config_path:
        import os

        os.environ.setdefault("AUTOTRANSLATE_CONFIG", str(config_path))
    threading.Timer(1.2, lambda: webbrowser.open(f"http://{host}:{port}/")).start()
    uvicorn.run("app.web.main:app", host=host, port=port, reload=False, factory=False)


if __name__ == "__main__":
    main()
