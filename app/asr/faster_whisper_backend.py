from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

from app.asr.base import ASRBackend
from app.config import ASRConfig
from app.config import PROJECT_ROOT
from app.core.exceptions import DependencyError, JobCancelledError
from app.models import TranscriptDocument, TranscriptSegment

logger = logging.getLogger(__name__)
ENABLE_CUDA_ASR_ENV_VAR = "AUTOTRANSLATE_ENABLE_CUDA_ASR"


class FasterWhisperBackend(ASRBackend):
    def __init__(self, config: ASRConfig, model_size: str | None = None) -> None:
        self.config = config
        self.model_size = model_size or config.model_size
        self.selected_device: str | None = None
        self.selected_compute_type: str | None = None
        self.warnings: list[str] = []

    def _add_warning(self, message: str) -> None:
        if message not in self.warnings:
            self.warnings.append(message)

    def _model_reference(self) -> str:
        model_name = str(self.model_size or "tiny").strip()
        bundled_tiny = Path(sys.executable).resolve().parent / "models" / "faster-whisper-tiny"
        bundle_root = Path(getattr(sys, "_MEIPASS", PROJECT_ROOT))
        candidates = [
            PROJECT_ROOT / "models" / f"faster-whisper-{model_name}",
            PROJECT_ROOT / "models" / model_name,
            Path(sys.executable).resolve().parent / "models" / f"faster-whisper-{model_name}",
            Path(sys.executable).resolve().parent / "models" / model_name,
            bundle_root / "models" / f"faster-whisper-{model_name}",
            bundle_root / "models" / model_name,
        ]
        for candidate in candidates:
            if (candidate / "model.bin").exists() and (candidate / "config.json").exists():
                return str(candidate)
        if getattr(sys, "frozen", False):
            fallback_candidates = [bundled_tiny, bundle_root / "models" / "faster-whisper-tiny"]
            for candidate in fallback_candidates:
                if (candidate / "model.bin").exists() and (candidate / "config.json").exists():
                    message = (
                        f"Không có sẵn model ASR '{model_name}' trong bản EXE, tự dùng model tiny local để tránh kẹt tải model."
                    )
                    self._add_warning(message)
                    return str(candidate)
        return model_name

    def _compute_type_for_device(self, device: str) -> str:
        compute_type = str(self.config.compute_type or "auto").strip().lower()
        if compute_type == "auto":
            return "float16" if device == "cuda" else "int8"
        if device == "cpu" and compute_type in {"float16", "int8_float16"}:
            return "int8"
        return compute_type

    def _device_candidates(self) -> list[tuple[str, str]]:
        configured_device = str(self.config.device or "auto").strip().lower()
        if configured_device == "cpu":
            return [("cpu", self._compute_type_for_device("cpu"))]
        if getattr(sys, "frozen", False) and not self._cuda_asr_explicitly_enabled():
            self._add_warning(
                "Bản EXE mặc định dùng CPU cho ASR để tránh kẹt 48% trên máy thiếu CUDA/cuDNN. "
                f"Muốn thử ASR GPU, đặt {ENABLE_CUDA_ASR_ENV_VAR}=1 trước khi mở EXE."
            )
            return [("cpu", self._compute_type_for_device("cpu"))]
        if configured_device == "cuda":
            return [("cuda", self._compute_type_for_device("cuda")), ("cpu", self._compute_type_for_device("cpu"))]
        if self._has_usable_cuda():
            return [("cuda", self._compute_type_for_device("cuda")), ("cpu", self._compute_type_for_device("cpu"))]
        return [("cpu", self._compute_type_for_device("cpu"))]

    def _cuda_asr_explicitly_enabled(self) -> bool:
        return str(os.getenv(ENABLE_CUDA_ASR_ENV_VAR, "")).strip().lower() in {"1", "true", "yes", "on"}

    def _has_usable_cuda(self) -> bool:
        try:
            import ctranslate2

            return int(ctranslate2.get_cuda_device_count()) > 0
        except Exception as exc:
            logger.info("CUDA ASR không khả dụng, dùng CPU. Chi tiết: %s", exc)
            return False

    def _has_nvidia_gpu_name(self) -> bool:
        nvidia_smi = shutil.which("nvidia-smi")
        if nvidia_smi:
            return True
        gpu_names = self._read_windows_gpu_names().lower()
        return any(keyword in gpu_names for keyword in ("nvidia", "geforce", "quadro", "rtx", "gtx"))

    def _read_windows_gpu_names(self) -> str:
        command = [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            "(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join [Environment]::NewLine",
        ]
        try:
            completed = subprocess.run(command, capture_output=True, text=True, timeout=3, check=False)
        except (OSError, subprocess.TimeoutExpired):
            return ""
        if completed.returncode != 0:
            return ""
        return completed.stdout or ""

    def transcribe(
        self,
        audio_path: Path,
        job_id: str,
        video_path: Path,
        duration_sec: float,
        progress_hook: Callable[[float], None] | None = None,
    ) -> TranscriptDocument:
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        try:
            from faster_whisper import WhisperModel
        except (ImportError, OSError) as exc:
            raise DependencyError(
                "Không tải được faster-whisper/ctranslate2 để nhận dạng giọng nói. "
                f"Python hiện tại: {sys.executable}. "
                "Trên Windows hãy chạy app bằng tools\\Python312\\python.exe, không dùng Python 3.14 hệ thống."
            ) from exc

        errors: list[str] = []
        for device, compute_type in self._device_candidates():
            try:
                return self._transcribe_with_device(
                    WhisperModel,
                    audio_path=audio_path,
                    job_id=job_id,
                    video_path=video_path,
                    duration_sec=duration_sec,
                    progress_hook=progress_hook,
                    device=device,
                    compute_type=compute_type,
                )
            except JobCancelledError:
                raise
            except Exception as exc:
                if device != "cuda":
                    if errors:
                        raise RuntimeError("\n\n".join([*errors, str(exc)])) from exc
                    raise
                message = (
                    "ASR không dùng được NVIDIA/CUDA nên tự chuyển sang CPU. "
                    f"Chi tiết: {exc}"
                )
                self._add_warning(message)
                errors.append(message)
                logger.warning(message, exc_info=exc)

        raise RuntimeError("Không nhận diện được giọng nói bằng GPU hoặc CPU.")

    def _transcribe_with_device(
        self,
        WhisperModel,
        audio_path: Path,
        job_id: str,
        video_path: Path,
        duration_sec: float,
        progress_hook: Callable[[float], None] | None,
        device: str,
        compute_type: str,
    ) -> TranscriptDocument:
        self.selected_device = device
        self.selected_compute_type = compute_type
        logger.info("Đang nhận diện ASR bằng %s (%s).", device.upper(), compute_type)
        if progress_hook:
            progress_hook(0.01)
        model = WhisperModel(
            self._model_reference(),
            device=device,
            compute_type=compute_type,
            cpu_threads=self.config.cpu_threads,
            num_workers=self.config.num_workers,
        )
        if progress_hook:
            progress_hook(0.03)
        segments, info = model.transcribe(
            str(audio_path),
            beam_size=self.config.beam_size,
            vad_filter=self.config.vad_filter,
            word_timestamps=self.config.word_timestamps,
        )
        rows = []
        last_reported_progress = 0.0
        for index, segment in enumerate(segments, start=1):
            text = " ".join(segment.text.split())
            if not text:
                continue
            rows.append(
                TranscriptSegment(
                    id=index,
                    start=float(segment.start),
                    end=float(segment.end),
                    text=text,
                )
            )
            if progress_hook and duration_sec > 0:
                current_progress = min(float(segment.end) / duration_sec, 0.98)
                if current_progress - last_reported_progress >= 0.02:
                    progress_hook(current_progress)
                    last_reported_progress = current_progress
        return TranscriptDocument(
            job_id=job_id,
            video_path=str(video_path),
            detected_language=getattr(info, "language", "unknown") or "unknown",
            duration_sec=duration_sec or float(getattr(info, "duration", 0.0) or 0.0),
            segments=rows,
        )
