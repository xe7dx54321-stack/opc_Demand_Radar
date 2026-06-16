import json

from opc_foundation.run.time_utils import utcnow_iso
from opc_foundation.signals.raw_signal_schema import RawSignal
from opc_foundation.sources.source_schema import FetchResult

from demand_radar.mvp_d.seeded_acquisition import run_seeded_acquisition


class _FakeConnector:
    def fetch(self, query, source, context):
        return FetchResult(
            source_id=source.source_id,
            connector=source.connector,
            raw_signals=[
                RawSignal(
                    signal_id="sig_001",
                    source_id=source.source_id,
                    source_type=source.source_type,
                    source_name=source.source_name,
                    source_url="https://news.ycombinator.com/item?id=123",
                    title="Analysts track startups manually",
                    raw_text=(
                        "VC analysts spend hours manually tracking AI startups across newsletters, "
                        "GitHub and funding databases. The workflow is slow and spreadsheet based."
                    ),
                    fetched_at=utcnow_iso(),
                    collection_query=query.query,
                    metadata={},
                )
            ],
            fetched_at=utcnow_iso(),
        )


def test_seeded_acquisition_writes_seed_metadata(tmp_path, monkeypatch):
    plan = tmp_path / "queries.jsonl"
    plan.write_text(
        json.dumps(
            {
                "query_id": "query_001",
                "seed_id": "seed_001",
                "pain_item_id": "pain__000022",
                "connector": "hacker_news",
                "query": "VC analyst workflow",
                "query_type": "persona_workflow",
                "expected_signal_type": "pain",
                "priority": "high",
                "negative_terms": [],
                "created_at": "2026-01-01T00:00:00Z",
                "metadata": {},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    import demand_radar.mvp_d.seeded_acquisition as mod

    monkeypatch.setitem(mod._CONNECTORS, "hacker_news", _FakeConnector)
    rows, summary = run_seeded_acquisition(
        query_plan_path=plan,
        existing_candidates_path=tmp_path / "existing.jsonl",
        output_path=tmp_path / "candidates.jsonl",
        report_path=tmp_path / "report.md",
        max_queries=1,
        max_results=3,
    )

    assert len(rows) == 1
    assert rows[0]["metadata"]["seed_id"] == "seed_001"
    assert rows[0]["metadata"]["pain_item_id"] == "pain__000022"
    assert summary["written_candidates"] == 1
    assert (tmp_path / "report.md").exists()


def test_seeded_acquisition_dedupes_against_existing(tmp_path, monkeypatch):
    plan = tmp_path / "queries.jsonl"
    plan.write_text(
        '{"query_id":"query_001","seed_id":"seed_001","pain_item_id":"pain__000022","connector":"hacker_news","query":"VC analyst workflow","query_type":"persona_workflow","expected_signal_type":"pain","priority":"high","negative_terms":[],"created_at":"2026-01-01T00:00:00Z","metadata":{}}\n',
        encoding="utf-8",
    )
    existing = tmp_path / "existing.jsonl"
    existing.write_text('{"source_url":"https://news.ycombinator.com/item?id=123"}\n', encoding="utf-8")

    import demand_radar.mvp_d.seeded_acquisition as mod

    monkeypatch.setitem(mod._CONNECTORS, "hacker_news", _FakeConnector)
    rows, summary = run_seeded_acquisition(
        query_plan_path=plan,
        existing_candidates_path=existing,
        output_path=tmp_path / "candidates.jsonl",
        report_path=tmp_path / "report.md",
    )

    assert rows == []
    assert summary["deduped_against_existing"] == 1

