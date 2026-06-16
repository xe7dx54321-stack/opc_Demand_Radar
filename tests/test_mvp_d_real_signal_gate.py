from demand_radar.mvp_d.real_signal_gate import is_real_signal, run_gate


def test_real_signal_gate_blocks_example_domain():
    result = is_real_signal(
        {
            "candidate_id": "cand_1",
            "source_url": "https://example.com/item/1",
            "title": "Real thing",
            "raw_text": "x" * 200,
            "metadata": {},
        }
    )
    assert result.allow is False
    assert "example.com" in (result.block_reason or "")


def test_real_signal_gate_blocks_placeholder_and_short_text():
    result = is_real_signal(
        {
            "candidate_id": "cand_2",
            "source_url": "https://news.ycombinator.com/item?id=1",
            "title": "placeholder sample",
            "raw_text": "too short",
            "metadata": {},
        }
    )
    assert result.allow is False


def test_real_signal_gate_allows_real_item():
    result = is_real_signal(
        {
            "candidate_id": "cand_3",
            "source_url": "https://news.ycombinator.com/item?id=1",
            "title": "Real item",
            "raw_text": "x" * 200,
            "metadata": {},
        }
    )
    assert result.allow is True

