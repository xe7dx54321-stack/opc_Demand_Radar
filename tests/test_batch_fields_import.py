from pathlib import Path

from demand_radar.cleaning.text_cleaner import normalize_signals
from demand_radar.clustering.demand_clusterer import run_demand_clustering
from demand_radar.intake.manual_import import import_file
from demand_radar.loops.pain_extraction_loop import run_pain_extraction
from demand_radar.state.raw_store import load_raw_signals


def test_old_csv_without_batch_fields_still_imports(tmp_path: Path) -> None:
    input_path = tmp_path / "signals.csv"
    raw_path = tmp_path / "raw.jsonl"
    quarantine_path = tmp_path / "quarantine.jsonl"
    input_path.write_text(
        "title,raw_text,url,source_name,source_type,language,domain_tags\n"
        "Legacy sample,Manual tracking is hard and scattered.,https://example.com,manual_import,manual,en,ai_investment_research\n",
        encoding="utf-8",
    )

    imported = import_file(input_path, raw_path, quarantine_path)

    assert len(imported) == 1
    assert imported[0].batch_id is None
    assert imported[0].signal_focus is None
    assert load_raw_signals(raw_path)[0].title == "Legacy sample"


def test_new_csv_batch_fields_are_imported_and_preserved(tmp_path: Path) -> None:
    input_path = tmp_path / "signals.csv"
    raw_path = tmp_path / "raw.jsonl"
    quarantine_path = tmp_path / "quarantine.jsonl"
    input_path.write_text(
        "title,raw_text,url,source_name,source_type,language,domain_tags,batch_id,source_note,signal_focus,expected_quality\n"
        "Batch sample,Investor manual tracking is hard and scattered.,https://example.com,manual_import,manual,en,ai_investment_research,batch_stage26_ai_research,HN excerpt,pain,strong\n",
        encoding="utf-8",
    )

    imported = import_file(input_path, raw_path, quarantine_path)

    assert imported[0].batch_id == "batch_stage26_ai_research"
    assert imported[0].source_note == "HN excerpt"
    assert imported[0].signal_focus == "pain"
    assert imported[0].expected_quality == "strong"


def test_batch_fields_flow_to_normalized_pain_and_cluster(tmp_path: Path) -> None:
    input_path = tmp_path / "signals.csv"
    raw_path = tmp_path / "raw.jsonl"
    normalized_path = tmp_path / "normalized.jsonl"
    pain_path = tmp_path / "pain.jsonl"
    quarantine_path = tmp_path / "quarantine.jsonl"
    clusters_path = tmp_path / "clusters.jsonl"
    invalid_clusters_path = tmp_path / "invalid_clusters.jsonl"
    extraction_config = tmp_path / "extraction_config.yaml"
    domain_config = tmp_path / "domain_config.yaml"
    clustering_config = tmp_path / "clustering_config.yaml"
    input_path.write_text(
        "title,raw_text,url,source_name,source_type,language,domain_tags,batch_id,source_note,signal_focus,expected_quality\n"
        "Batch sample,Investor manual tracking is hard and scattered every week. We use a spreadsheet workaround.,https://example.com,manual_import,manual,en,ai_investment_research,batch_stage26_ai_research,HN excerpt,pain,strong\n",
        encoding="utf-8",
    )
    extraction_config.write_text(
        "pain_extraction:\n  default_mode: rule_based\n  min_confidence: 0.65\n  max_text_chars: 8000\n",
        encoding="utf-8",
    )
    domain_config.write_text("domains: []\npersonas: []\nexclude: []\nsignal_types: []\n", encoding="utf-8")
    clustering_config.write_text(
        "clustering:\n  enabled: true\n  similarity_threshold: 70\n  singleton_clusters: true\n  max_representative_quotes: 3\n",
        encoding="utf-8",
    )

    imported = import_file(input_path, raw_path, quarantine_path)
    normalized = normalize_signals(raw_path, normalized_path, quarantine_path, extraction_config)
    pain_points = run_pain_extraction(
        normalized_path,
        pain_path,
        quarantine_path,
        domain_config,
        extraction_config,
    )
    clusters = run_demand_clustering(pain_path, clusters_path, invalid_clusters_path, clustering_config)

    assert imported[0].batch_id == "batch_stage26_ai_research"
    assert normalized[0].batch_id == "batch_stage26_ai_research"
    assert normalized[0].source_note == "HN excerpt"
    assert pain_points[0].batch_id == "batch_stage26_ai_research"
    assert pain_points[0].signal_focus == "pain"
    assert pain_points[0].expected_quality == "strong"
    assert clusters[0].batch_ids == ["batch_stage26_ai_research"]
    assert clusters[0].signal_focuses == ["pain"]
    assert clusters[0].expected_quality_mix == {"strong": 1}
