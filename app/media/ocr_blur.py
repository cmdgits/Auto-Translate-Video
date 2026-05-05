from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Callable

from app.config import PROJECT_ROOT, RenderConfig
from app.core.exceptions import DependencyError, ProcessError
from app.media.ffmpeg import ensure_binary


Box = tuple[int, int, int, int]


def blur_text_in_video_with_ocr(
    input_video: Path,
    output_video: Path,
    ffmpeg_bin: str,
    render_config: RenderConfig,
    video_encode_args: list[str],
    progress_callback: Callable[[float], None] | None = None,
) -> Path:
    cv2 = _load_cv2()
    detector = _build_ocr_detector(render_config)

    capture = cv2.VideoCapture(str(input_video))
    if not capture.isOpened():
        raise ProcessError(f"Không mở được video để OCR blur: {input_video}")

    try:
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0) or 25.0
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if width <= 0 or height <= 0:
            raise ProcessError("Không đọc được kích thước video để OCR blur.")

        output_video.parent.mkdir(parents=True, exist_ok=True)
        command = [
            ensure_binary(ffmpeg_bin),
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "-s",
            f"{width}x{height}",
            "-r",
            f"{fps:.6f}",
            "-i",
            "-",
            "-i",
            str(input_video),
            "-map",
            "0:v:0",
            "-map",
            "1:a?",
            *video_encode_args,
            "-c:a",
            "copy",
            "-shortest",
            "-movflags",
            "+faststart",
            str(output_video),
        ]
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        if process.stdin is None:
            raise ProcessError("Không mở được stdin FFmpeg để ghi frame OCR blur.")

        frame_index = 0
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                for x1, y1, x2, y2 in detector.detect(frame):
                    _blur_roi(frame, x1, y1, x2, y2, int(render_config.ocr_blur_kernel_size))
                process.stdin.write(frame.tobytes())
                frame_index += 1
                if progress_callback and frame_count > 0:
                    progress_callback(min(frame_index / frame_count, 0.995))
        except BrokenPipeError as exc:
            raise ProcessError("FFmpeg dừng khi đang ghi frame OCR blur.") from exc
        finally:
            process.stdin.close()

        stderr = process.stderr.read().decode("utf-8", errors="ignore") if process.stderr else ""
        return_code = process.wait()
        if return_code != 0:
            raise ProcessError(f"OCR Gaussian Blur thất bại. FFmpeg trả mã {return_code}: {stderr.strip()}")
        if progress_callback:
            progress_callback(1.0)
        return output_video
    finally:
        capture.release()


class TesseractTextDetector:
    def __init__(self, render_config: RenderConfig) -> None:
        self.render_config = render_config
        self.pytesseract = _load_pytesseract()
        self.languages = str(render_config.ocr_languages or "eng").strip() or "eng"
        self.config = str(render_config.ocr_tesseract_config or "--psm 11").strip() or "--psm 11"
        self.min_confidence = float(render_config.ocr_min_confidence)
        self.padding = max(0, int(render_config.ocr_box_padding))

    def detect(self, frame) -> list[Box]:
        cv2 = _load_cv2()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        try:
            data = self.pytesseract.image_to_data(
                rgb_frame,
                lang=self.languages,
                config=self.config,
                output_type=self.pytesseract.Output.DICT,
            )
        except Exception:
            if self.languages == "eng":
                raise
            data = self.pytesseract.image_to_data(
                rgb_frame,
                lang="eng",
                config=self.config,
                output_type=self.pytesseract.Output.DICT,
            )
        frame_height, frame_width = frame.shape[:2]
        boxes: list[Box] = []
        for index, text in enumerate(data.get("text", [])):
            if not str(text or "").strip():
                continue
            try:
                confidence = float(data["conf"][index])
            except (KeyError, TypeError, ValueError):
                confidence = 0.0
            if confidence < self.min_confidence:
                continue
            left = int(data["left"][index])
            top = int(data["top"][index])
            width = int(data["width"][index])
            height = int(data["height"][index])
            if width <= 0 or height <= 0:
                continue
            boxes.append(
                _clip_box(
                    left - self.padding,
                    top - self.padding,
                    left + width + self.padding,
                    top + height + self.padding,
                    frame_width,
                    frame_height,
                )
            )
        return boxes


def _build_ocr_detector(render_config: RenderConfig) -> TesseractTextDetector:
    backend = str(render_config.ocr_backend or "tesseract").strip().lower()
    if backend != "tesseract":
        raise DependencyError("Hiện OCR Gaussian Blur đang hỗ trợ backend 'tesseract'.")
    return TesseractTextDetector(render_config)


def _blur_roi(frame, x1: int, y1: int, x2: int, y2: int, kernel_size: int) -> None:
    cv2 = _load_cv2()
    if x2 <= x1 or y2 <= y1:
        return
    safe_kernel = max(3, int(kernel_size) | 1)
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return
    frame[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (safe_kernel, safe_kernel), 0)


def _clip_box(x1: int, y1: int, x2: int, y2: int, frame_width: int, frame_height: int) -> Box:
    return (
        max(0, min(x1, frame_width - 1)),
        max(0, min(y1, frame_height - 1)),
        max(1, min(x2, frame_width)),
        max(1, min(y2, frame_height)),
    )


def _load_cv2():
    try:
        import cv2
    except ImportError as exc:
        raise DependencyError("Chưa cài opencv-python. Hãy chạy lại install_all.bat để dùng OCR Gaussian Blur.") from exc
    return cv2


def _load_pytesseract():
    try:
        import pytesseract
    except ImportError as exc:
        raise DependencyError("Chưa cài pytesseract. Hãy chạy lại install_all.bat để dùng OCR Gaussian Blur.") from exc

    tesseract_cmd = os.getenv("TESSERACT_CMD") or os.getenv("AUTOTRANSLATE_TESSERACT_CMD")
    if not tesseract_cmd:
        tesseract_cmd = shutil.which("tesseract")
    if not tesseract_cmd:
        for candidate in (
            PROJECT_ROOT / "tools" / "Tesseract-OCR" / "tesseract.exe",
            Path(os.environ.get("ProgramFiles", "C:/Program Files")) / "Tesseract-OCR" / "tesseract.exe",
            Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)")) / "Tesseract-OCR" / "tesseract.exe",
        ):
            if candidate.exists():
                tesseract_cmd = str(candidate)
                break
    if not tesseract_cmd:
        raise DependencyError(
            "Chưa tìm thấy Tesseract OCR. Hãy cài Tesseract OCR rồi đặt biến TESSERACT_CMD nếu cần."
        )
    pytesseract.pytesseract.tesseract_cmd = str(tesseract_cmd)
    return pytesseract
