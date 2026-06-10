from pathlib import Path

from demand_radar.intake.manual_import import import_file
from demand_radar.state.quarantine_store import load_quarantine
from demand_radar.state.raw_store import load_raw_signals


def test_csv_import_generates_ids_and_hashes(tmp_path: Path) -> None:
    input_path = tmp_path / "signals.csv"
    raw_path = tmp_path / "raw.jsonl"
    quarantine_path = tmp_path / "quarantine.jsonl"
    input_path.write_text(
        "title,raw_text,url,source_name,source_type,language,domain_tags\n"
        "Tracking AI infra,Manual tracking is hard and scattered.,https://example.com,manual_import,manual,en,ai_investment_research\n",
        encoding="utf-8",
    )

    imported = import_file(input_path, raw_path, quarantine_path)

    assert len(imported) == 1
    assert imported[0].raw_signal_id == "sig_000001"
    assert imported[0].content_hash
    assert imported[0].domain_tags == ["ai_investment_research"]
    assert load_raw_signals(raw_path)[0].title == "Tracking AI infra"


def test_jsonl_import_works(tmp_path: Path) -> None:
    input_path = tmp_path / "signals.jsonl"
    raw_path = tmp_path / "raw.jsonl"
    quarantine_path = tmp_path / "quarantine.jsonl"
    input_path.write_text(
        '{"title":"API pain","raw_text":"Developer API docs are incomplete and slow to use.","source_name":"manual_import","source_type":"manual"}\n',
        encoding="utf-8",
    )

    imported = import_file(input_path, raw_path, quarantine_path)

    assert len(imported) == 1
    assert imported[0].raw_signal_id == "sig_000001"


def test_empty_raw_text_is_quarantined(tmp_path: Path) -> None:
    input_path = tmp_path / "signals.csv"
    raw_path = tmp_path / "raw.jsonl"
    quarantine_path = tmp_path / "quarantine.jsonl"
    input_path.write_text("title,raw_text\nEmpty,\n", encoding="utf-8")

    imported = import_file(input_path, raw_path, quarantine_path)
    quarantine = load_quarantine(quarantine_path)

    assert imported == []
    assert quarantine[0].reason == "empty_text"


def test_duplicate_signal_is_quarantined(tmp_path: Path) -> None:
    input_path = tmp_path / "signals.csv"
    raw_path = tmp_path / "raw.jsonl"
    quarantine_path = tmp_path / "quarantine.jsonl"
    input_path.write_text(
        "title,raw_text\n"
        "Same,Manual tracking is hard and scattered.\n"
        "Same,Manual tracking is hard and scattered.\n",
        encoding="utf-8",
    )

    imported = import_file(input_path, raw_path, quarantine_path)
    quarantine = load_quarantine(quarantine_path)

    assert len(imported) == 1
    assert quarantine[0].reason == "duplicate_signal"

