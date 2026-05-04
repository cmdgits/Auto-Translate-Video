from __future__ import annotations

import json
from pathlib import Path

from app.models import VideoMetadata
from app.media.ffmpeg import ensure_binary, run_process


def probe_video(input_path: Path, ffprobe_bin: str) -> VideoMetadata:
    command = [
        ensure_binary(ffprobe_bin),
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=index,codec_type,codec_name,width,height,sample_rate,channels",
        "-of",
        "json",
        str(input_path),
    ]
    payload = json.loads(run_process(command))
    streams = payload.get("streams", [])
    format_data = payload.get("format", {})
    video_stream = next((stream for stream in streams if stream.get("codec_type") == "video"), {})
    audio_stream = next((stream for stream in streams if stream.get("codec_type") == "audio"), {})
    return VideoMetadata(
        duration_sec=float(format_data.get("duration", 0.0) or 0.0),
        width=video_stream.get("width"),
        height=video_stream.get("height"),
        audio_stream_index=audio_stream.get("index"),
        audio_codec=audio_stream.get("codec_name"),
        sample_rate=int(audio_stream["sample_rate"]) if audio_stream.get("sample_rate") else None,
        channels=audio_stream.get("channels"),
    )

