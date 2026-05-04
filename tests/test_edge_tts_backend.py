import sys
import shutil
import types
import uuid
from pathlib import Path
from unittest.mock import patch

from app.config import TTSConfig
from app.models import TranscriptSegment
from app.tts.edge_tts_backend import EdgeTTSBackend


def test_edge_tts_backend_skips_empty_audio() -> None:
    output_dir = Path("workspace_data") / "test_runs" / f"edge_tts_{uuid.uuid4().hex}"

    class FakeCommunicate:
        def __init__(self, text: str, voice: str, rate: str) -> None:
            self.text = text

        async def save(self, path: str) -> None:
            open(path, "wb").close()

    try:
        with patch.dict(sys.modules, {"edge_tts": types.SimpleNamespace(Communicate=FakeCommunicate)}):
            backend = EdgeTTSBackend(TTSConfig())
            clips = backend.synthesize_segments(
                [TranscriptSegment(id=1, start=0.0, end=1.0, text="xin chao")],
                output_dir,
            )

        assert clips == []
        assert "audio" in backend.warnings[0]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)
