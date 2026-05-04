from __future__ import annotations

import json
import math
import wave
from array import array
from pathlib import Path


def build_waveform_payload(wav_path: Path, max_points: int = 2400) -> dict[str, object]:
    with wave.open(str(wav_path), "rb") as wav_file:
        channels = wav_file.getnchannels()
        sample_width = wav_file.getsampwidth()
        sample_rate = wav_file.getframerate()
        total_frames = wav_file.getnframes()
        if sample_width != 2:
            raise ValueError("Waveform chỉ hỗ trợ WAV PCM 16-bit.")
        bucket_size = max(1, math.ceil(total_frames / max(1, max_points)))
        peaks: list[float] = []
        while True:
            frame_data = wav_file.readframes(bucket_size)
            if not frame_data:
                break
            samples = array("h")
            samples.frombytes(frame_data)
            if channels > 1:
                samples = array("h", samples[::channels])
            peak = max((abs(sample) for sample in samples), default=0)
            peaks.append(round(min(1.0, peak / 32768), 4))
    return {
        "version": 1,
        "sample_rate": sample_rate,
        "duration_sec": round(total_frames / sample_rate, 3) if sample_rate else 0,
        "points": len(peaks),
        "peaks": peaks,
    }


def write_waveform_json(wav_path: Path, output_path: Path, max_points: int = 2400) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = build_waveform_payload(wav_path, max_points=max_points)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    return output_path
