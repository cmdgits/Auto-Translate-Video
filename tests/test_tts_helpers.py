from app.tts.edge_tts_backend import estimate_edge_tts_rate
from app.tts.edge_tts_backend import sanitize_tts_text


def test_estimate_edge_tts_rate_clamps_upper_bound() -> None:
    rate = estimate_edge_tts_rate(
        "mot doan van ban kha dai de ep vao mot khoang thoi gian cuc ngan",
        0.0,
        0.8,
        floor=-35,
        ceil=45,
    )
    assert rate == 45


def test_estimate_edge_tts_rate_can_slow_down() -> None:
    rate = estimate_edge_tts_rate(
        "xin chao",
        0.0,
        6.0,
        floor=-35,
        ceil=45,
    )
    assert rate < 0


def test_sanitize_tts_text_removes_control_characters() -> None:
    assert sanitize_tts_text("xin\n\tchao\x00 ban") == "xin chao ban"
