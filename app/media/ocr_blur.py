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
        detection_interval = max(1, int(getattr(render_config, "ocr_frame_interval", 10) or 10))
        cached_boxes: list[Box] = []
        try:
            while True:
                ok, frame = capture.read()
                if not ok:
                    break
                if frame_index % detection_interval == 0:
                    cached_boxes = detector.detect(frame)
                for x1, y1, x2, y2 in cached_boxes:
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
        self.min_confidence = max(0.0, min(100.0, float(render_config.ocr_min_confidence)))
        self.padding = max(0, int(render_config.ocr_box_padding))
        self.scan_region = str(getattr(render_config, "ocr_scan_region", "subtitle") or "subtitle").strip().lower()

    def detect(self, frame) -> list[Box]:
        cv2 = _load_cv2()
        frame_height, frame_width = frame.shape[:2]
        region_left, region_top, region_right, region_bottom = self._scan_box(frame_width, frame_height)
        scan_frame = frame[region_top:region_bottom, region_left:region_right]
        if scan_frame.size == 0:
            return []
        visual_boxes = _detect_visual_subtitle_boxes(
            scan_frame,
            region_left,
            region_top,
            frame_width,
            frame_height,
            self.render_config,
            self.padding,
        )
        if visual_boxes:
            return visual_boxes
        ocr_frame, scale = _prepare_ocr_frame(scan_frame)
        try:
            data = self.pytesseract.image_to_data(
                ocr_frame,
                lang=self.languages,
                config=self.config,
                output_type=self.pytesseract.Output.DICT,
            )
        except Exception:
            if self.languages == "eng":
                raise
            data = self.pytesseract.image_to_data(
                ocr_frame,
                lang="eng",
                config=self.config,
                output_type=self.pytesseract.Output.DICT,
            )
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
            left = int(round(int(data["left"][index]) / scale))
            top = int(round(int(data["top"][index]) / scale))
            width = int(round(int(data["width"][index]) / scale))
            height = int(round(int(data["height"][index]) / scale))
            if not _is_plausible_text_box(width, height, frame_width, frame_height):
                continue
            boxes.append(
                _clip_box(
                    region_left + left,
                    region_top + top,
                    region_left + left + width,
                    region_top + top + height,
                    frame_width,
                    frame_height,
                )
            )
        return _filter_subtitle_position_boxes(
            _merge_subtitle_line_boxes(boxes, frame_width, frame_height, self.render_config, self.padding),
            frame_width,
            frame_height,
            self.render_config,
        )

    def _scan_box(self, frame_width: int, frame_height: int) -> Box:
        if self.scan_region in {"full", "all", "frame"}:
            return 0, 0, frame_width, frame_height
        subtitle_bottom_ratio = max(0.0, min(float(self.render_config.subtitle_position_y) / 100, 0.60))
        subtitle_x_ratio = max(0.08, min(float(self.render_config.subtitle_position_x) / 100, 0.92))
        cover_width_ratio = max(0.42, min(float(self.render_config.subtitle_cover_width_ratio) + 0.08, 0.96))
        region_height = max(0.22, min(float(self.render_config.subtitle_cover_height_ratio) * 4.6, 0.34))
        left_ratio = max(0.0, min(subtitle_x_ratio - cover_width_ratio / 2, 1.0 - cover_width_ratio))
        top_ratio = max(0.0, min(1.0 - subtitle_bottom_ratio - region_height, 1.0 - region_height))
        return _clip_box(
            int(frame_width * left_ratio),
            int(frame_height * top_ratio),
            int(frame_width * (left_ratio + cover_width_ratio)),
            frame_height,
            frame_width,
            frame_height,
        )


def _build_ocr_detector(render_config: RenderConfig) -> TesseractTextDetector:
    backend = str(render_config.ocr_backend or "tesseract").strip().lower()
    if backend != "tesseract":
        raise DependencyError("Hiện OCR Gaussian Blur đang hỗ trợ backend 'tesseract'.")
    return TesseractTextDetector(render_config)


def _prepare_ocr_frame(scan_frame):
    cv2 = _load_cv2()
    frame_height, frame_width = scan_frame.shape[:2]
    scale = 1.0
    if frame_width < 1600:
        scale = min(2.0, 1600 / max(1, frame_width))
        scan_frame = cv2.resize(scan_frame, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(scan_frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    threshold = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        9,
    )
    return threshold, scale


def _detect_visual_subtitle_boxes(
    scan_frame,
    region_left: int,
    region_top: int,
    frame_width: int,
    frame_height: int,
    render_config: RenderConfig,
    padding: int,
) -> list[Box]:
    cv2 = _load_cv2()
    gray = cv2.cvtColor(scan_frame, cv2.COLOR_BGR2GRAY)
    hsv = cv2.cvtColor(scan_frame, cv2.COLOR_BGR2HSV)
    scan_height, scan_width = scan_frame.shape[:2]
    saturation = hsv[:, :, 1]
    value = hsv[:, :, 2]
    bright = cv2.inRange(value, 195, 255)
    low_saturation = cv2.inRange(saturation, 0, 80)
    white_mask = cv2.bitwise_and(bright, low_saturation)
    dark_outline = cv2.inRange(gray, 0, 125)
    dark_outline = cv2.dilate(dark_outline, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)), iterations=1)
    text_mask = cv2.bitwise_and(white_mask, dark_outline)
    text_mask = cv2.morphologyEx(
        text_mask,
        cv2.MORPH_OPEN,
        cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)),
        iterations=1,
    )
    return _projection_subtitle_boxes(
        text_mask,
        region_left,
        region_top,
        frame_width,
        frame_height,
        scan_width,
        scan_height,
        render_config,
        padding,
    )


def _projection_subtitle_boxes(
    text_mask,
    region_left: int,
    region_top: int,
    frame_width: int,
    frame_height: int,
    scan_width: int,
    scan_height: int,
    render_config: RenderConfig,
    padding: int,
) -> list[Box]:
    cv2 = _load_cv2()
    if text_mask.size == 0:
        return []
    row_scores = (text_mask > 0).sum(axis=1)
    max_row_score = int(row_scores.max()) if row_scores.size else 0
    if max_row_score < max(55, int(scan_width * 0.04)):
        return []
    row_threshold = max(int(max_row_score * 0.35), int(scan_width * 0.018), 8)
    row_groups = _active_index_groups(row_scores, row_threshold, min_length=6, gap_tolerance=2)

    candidates: list[tuple[float, Box]] = []
    for row_start, row_end in row_groups:
        absolute_center_y = region_top + (row_start + row_end) / 2
        absolute_bottom_y = region_top + row_end
        if absolute_center_y < frame_height * 0.58 or absolute_bottom_y < frame_height * 0.83:
            continue
        row_height = row_end - row_start
        if row_height > frame_height * 0.13:
            continue
        band_top = max(0, row_start - 2)
        band_bottom = min(scan_height, row_end + 2)
        band_mask = text_mask[band_top:band_bottom, :]
        if band_mask.size == 0:
            continue
        band_mask = cv2.dilate(band_mask, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 3)), iterations=1)
        column_scores = (band_mask > 0).sum(axis=0)
        column_threshold = max(3, int((band_bottom - band_top) * 0.16))
        column_groups = _active_index_groups(column_scores, column_threshold, min_length=5, gap_tolerance=2)
        column_groups = _merge_index_groups(column_groups, max_gap=max(24, int(frame_width * 0.025)))
        if not column_groups:
            continue
        expected_center_x = frame_width * max(0.08, min(float(render_config.subtitle_position_x) / 100, 0.92))
        max_center_distance = frame_width * 0.30
        scored_column_groups: list[tuple[float, tuple[int, int]]] = []
        for group in column_groups:
            group_width = group[1] - group[0]
            group_center_x = region_left + (group[0] + group[1]) / 2
            center_distance = abs(group_center_x - expected_center_x)
            if center_distance > max_center_distance:
                continue
            min_line_width = max(64, int(frame_width * (0.05 if center_distance < frame_width * 0.12 else 0.11)))
            if group_width < min_line_width:
                continue
            content_score = float(column_scores[group[0] : group[1]].sum())
            score = content_score + group_width * 3.0 - center_distance * 10.0
            scored_column_groups.append((score, group))
        if not scored_column_groups:
            continue
        best_column_group = max(scored_column_groups, key=lambda item: item[0])[1]
        column_start, column_end = best_column_group
        line_width = column_end - column_start
        extra_x = max(padding * 2, int(frame_width * 0.02))
        extra_y = max(padding, int(row_height * 0.38), int(frame_height * 0.014))
        box = _clip_box(
            region_left + column_start - extra_x,
            region_top + row_start - extra_y,
            region_left + column_end + extra_x,
            region_top + row_end + extra_y,
            frame_width,
            frame_height,
        )
        score = float(line_width * 2 + row_scores[row_start:row_end].sum() + absolute_center_y)
        candidates.append((score, box))
    if not candidates:
        return []
    candidates.sort(key=lambda item: item[0], reverse=True)
    selected: list[Box] = []
    for _, box in candidates:
        if len(selected) >= 2:
            break
        if any(_box_overlap_ratio(box, existing) > 0.18 for existing in selected):
            continue
        selected.append(box)
    return sorted(selected, key=lambda box: box[1])


def _active_index_groups(scores, threshold: int, min_length: int = 1, gap_tolerance: int = 0) -> list[tuple[int, int]]:
    groups: list[tuple[int, int]] = []
    start: int | None = None
    last_active: int | None = None
    for index, value in enumerate(scores):
        if int(value) >= threshold:
            if start is None:
                start = index
            last_active = index
            continue
        if start is not None and last_active is not None and index - last_active <= gap_tolerance:
            continue
        if start is not None and last_active is not None and last_active + 1 - start >= min_length:
            groups.append((start, last_active + 1))
        start = None
        last_active = None
    if start is not None and last_active is not None and last_active + 1 - start >= min_length:
        groups.append((start, last_active + 1))
    return groups


def _merge_index_groups(groups: list[tuple[int, int]], max_gap: int) -> list[tuple[int, int]]:
    if not groups:
        return []
    merged: list[tuple[int, int]] = [groups[0]]
    for start, end in groups[1:]:
        previous_start, previous_end = merged[-1]
        if start - previous_end <= max_gap:
            merged[-1] = (previous_start, max(previous_end, end))
        else:
            merged.append((start, end))
    return merged


def _box_overlap_ratio(first: Box, second: Box) -> float:
    x1 = max(first[0], second[0])
    y1 = max(first[1], second[1])
    x2 = min(first[2], second[2])
    y2 = min(first[3], second[3])
    if x2 <= x1 or y2 <= y1:
        return 0.0
    overlap = (x2 - x1) * (y2 - y1)
    first_area = max(1, (first[2] - first[0]) * (first[3] - first[1]))
    second_area = max(1, (second[2] - second[0]) * (second[3] - second[1]))
    return overlap / min(first_area, second_area)


def _is_plausible_text_box(box_width: int, box_height: int, frame_width: int, frame_height: int) -> bool:
    if box_width < max(8, frame_width * 0.006) or box_height < max(8, frame_height * 0.012):
        return False
    if box_width > frame_width * 0.92 or box_height > frame_height * 0.22:
        return False
    return True


def _filter_subtitle_position_boxes(boxes: list[Box], frame_width: int, frame_height: int, render_config: RenderConfig) -> list[Box]:
    if not boxes:
        return []
    expected_center_x = frame_width * max(0.08, min(float(render_config.subtitle_position_x) / 100, 0.92))
    max_center_distance = frame_width * 0.36
    filtered: list[Box] = []
    for box in boxes:
        box_width = box[2] - box[0]
        box_height = box[3] - box[1]
        center_x = (box[0] + box[2]) / 2
        center_y = (box[1] + box[3]) / 2
        if box_width < max(180, int(frame_width * 0.16)):
            continue
        if box_width > frame_width * 0.88 or box_height > frame_height * 0.18:
            continue
        if center_y < frame_height * 0.68 or box[3] < frame_height * 0.83:
            continue
        if abs(center_x - expected_center_x) > max_center_distance:
            continue
        filtered.append(box)
    return filtered[:2]


def _merge_subtitle_line_boxes(
    boxes: list[Box],
    frame_width: int,
    frame_height: int,
    render_config: RenderConfig,
    padding: int,
) -> list[Box]:
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda box: ((box[1] + box[3]) / 2, box[0]))
    line_threshold = max(18, int(frame_height * 0.045))
    lines: list[list[Box]] = []
    for box in boxes:
        center_y = (box[1] + box[3]) / 2
        for line in lines:
            line_center_y = sum((item[1] + item[3]) / 2 for item in line) / len(line)
            if abs(center_y - line_center_y) <= line_threshold:
                line.append(box)
                break
        else:
            lines.append([box])

    merged: list[Box] = []
    min_line_width = max(80, int(frame_width * 0.12))
    for line in lines:
        x1 = min(box[0] for box in line)
        y1 = min(box[1] for box in line)
        x2 = max(box[2] for box in line)
        y2 = max(box[3] for box in line)
        if x2 - x1 < min_line_width and len(line) < 2:
            continue
        extra_x = max(padding * 2, int(frame_width * 0.018))
        extra_y = max(padding * 2, int((y2 - y1) * 0.55), int(frame_height * 0.018))
        merged.append(_clip_box(x1 - extra_x, y1 - extra_y, x2 + extra_x, y2 + extra_y, frame_width, frame_height))
    return _merge_overlapping_boxes(merged, frame_width, frame_height)


def _merge_visual_text_components(boxes: list[Box], frame_width: int, frame_height: int, padding: int) -> list[Box]:
    if not boxes:
        return []
    boxes = sorted(boxes, key=lambda box: ((box[1] + box[3]) / 2, box[0]))
    line_threshold = max(16, int(frame_height * 0.04))
    lines: list[list[Box]] = []
    for box in boxes:
        center_y = (box[1] + box[3]) / 2
        for line in lines:
            line_center_y = sum((item[1] + item[3]) / 2 for item in line) / len(line)
            if abs(center_y - line_center_y) <= line_threshold:
                line.append(box)
                break
        else:
            lines.append([box])

    candidates: list[tuple[float, Box, float]] = []
    min_line_width = max(120, int(frame_width * 0.16))
    for line in lines:
        if len(line) < 5:
            continue
        x1 = min(box[0] for box in line)
        y1 = min(box[1] for box in line)
        x2 = max(box[2] for box in line)
        y2 = max(box[3] for box in line)
        line_width = x2 - x1
        center_y = (y1 + y2) / 2
        if line_width < min_line_width or center_y < frame_height * 0.58:
            continue
        median_height = sorted(box[3] - box[1] for box in line)[len(line) // 2]
        extra_x = max(padding * 2, int(frame_width * 0.02))
        extra_y = max(padding * 2, int(median_height * 1.1), int(frame_height * 0.024))
        box = _clip_box(x1 - extra_x, y1 - extra_y, x2 + extra_x, y2 + extra_y, frame_width, frame_height)
        score = len(line) * 16 + line_width / 8 + center_y / 6
        candidates.append((score, box, center_y))
    if not candidates:
        return []
    candidates.sort(key=lambda item: item[0], reverse=True)
    best_score, _, best_center_y = candidates[0]
    selected: list[Box] = []
    for score, box, center_y in candidates:
        if len(selected) >= 2:
            break
        if score < best_score * 0.48:
            continue
        if abs(center_y - best_center_y) > frame_height * 0.13:
            continue
        selected.append(box)
    return sorted(selected, key=lambda box: box[1])


def _merge_overlapping_boxes(boxes: list[Box], frame_width: int, frame_height: int) -> list[Box]:
    merged: list[Box] = []
    for box in sorted(boxes, key=lambda item: (item[1], item[0])):
        for index, existing in enumerate(merged):
            if _boxes_close(existing, box, frame_width, frame_height):
                merged[index] = _clip_box(
                    min(existing[0], box[0]),
                    min(existing[1], box[1]),
                    max(existing[2], box[2]),
                    max(existing[3], box[3]),
                    frame_width,
                    frame_height,
                )
                break
        else:
            merged.append(box)
    return merged


def _boxes_close(first: Box, second: Box, frame_width: int, frame_height: int) -> bool:
    horizontal_gap = max(0, max(first[0], second[0]) - min(first[2], second[2]))
    vertical_gap = max(0, max(first[1], second[1]) - min(first[3], second[3]))
    vertical_overlap = min(first[3], second[3]) - max(first[1], second[1])
    return (
        vertical_gap <= frame_height * 0.025
        and horizontal_gap <= frame_width * 0.08
        and vertical_overlap > -frame_height * 0.01
    )


def _blur_roi(frame, x1: int, y1: int, x2: int, y2: int, kernel_size: int) -> None:
    cv2 = _load_cv2()
    if x2 <= x1 or y2 <= y1:
        return
    safe_kernel = max(21, int(kernel_size) | 1)
    roi = frame[y1:y2, x1:x2]
    if roi.size == 0:
        return
    blurred = roi
    for _ in range(3):
        blurred = cv2.GaussianBlur(blurred, (safe_kernel, safe_kernel), 0)
    frame[y1:y2, x1:x2] = blurred


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
