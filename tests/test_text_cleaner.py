from pathlib import Path

from demand_radar.cleaning.text_cleaner import clean_text, normalize_signals
from demand_radar.state.raw_store import write_jsonl


def test_clean_text_removes_extra_whitespace_and_markup() -> None:
    text = clean_text("<p>Hello   [world](https://example.com)</p>\n\n# Title")

    assert text == "Hello world Title"


def test_clean_text_truncates_long_text() -> None:
    assert clean_text("abcdef", max_chars=3) == "abc"


def test_normalize_filters_empty_text(tmp_path: Path) -> None:
    raw_path = tmp_path / "raw.jsonl"
    output_path = tmp_path / "normalized.jsonl"
    quarantine_path = tmp_path / "quarantine.jsonl"
    config_path = tmp_path / "extraction_config.yaml"
    config_path.write_text("pain_extraction:\n  max_text_chars: 8000\n", encoding="utf-8")
    write_jsonl(
        raw_path,
        [
            {
                "raw_signal_id": "sig_000001",
                "source_name": "manual_import",
                "source_type": "manual",
                "title": "Only markup",
                "raw_text": "<br><br>",
                "url": None,
                "published_at": None,
                "collected_at": "2026-06-10T00:00:00Z",
                "language": "en",
                "domain_tags": [],
                "metadata": {},
                "content_hash": "abc",
            }
        ],
    )

    normalized = normalize_signals(raw_path, output_path, quarantine_path, config_path)

    assert normalized == []
    assert "empty_text" in quarantine_path.read_text(encoding="utf-8")

