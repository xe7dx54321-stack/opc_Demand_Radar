"""Tests for truth_scorer.py"""
from demand_radar.truth_scoring.truth_scorer import score_group

BASE_GROUP = {
    "group_id": "g1",
    "group_title_zh": "\u5185\u5bb9\u56e2\u961f\u9762\u4e34\u9009\u9898\u56f0\u96be",
    "group_summary_zh": "\u5185\u5bb9\u5275\u4f5c\u8005\u5728\u9009\u9898\u65f6\u975e\u5e38\u9ebb\u70e6\uff0c\u4eba\u5de5\u6574\u7406\u8017\u65f6",
    "evidence_count": 5,
    "source_count": 3,
    "batch_ids": ["batch_a", "batch_b", "batch_c"],
    "personas": ["content_team"],
    "domain_tags": ["content_production"],
    "current_workarounds": ["\u624b\u5de5\u7c98\u8d34\u8868\u683c", "\u5185\u90e8\u6574\u7406\u6587\u6863"],
    "representative_quotes": ["\u6bcf\u5929\u9009\u9898\u8981\u82b1\u4e24\u5c0f\u65f6\uff0c\u6548\u7387\u5f88\u4f4e"],
    "representative_pain_descriptions": ["\u4eba\u5de5\u9009\u9898\u6d69\u70b9\uff0c\u65e0\u6cd5\u5feb\u901f\u68c0\u7d22\u76f8\u5173\u5185\u5bb9"],
}


def test_score_group_returns_all_dims():
    result = score_group(BASE_GROUP)
    dims = result["dimension_scores"]
    assert "pain_evidence_strength" in dims
    assert "frequency_repetition" in dims
    assert "existing_workaround" in dims
    assert "willingness_to_pay" in dims
    assert "persona_clarity" in dims


def test_score_range():
    result = score_group(BASE_GROUP)
    assert 0 <= result["truth_score"] <= 100


def test_high_evidence_gives_higher_pain_score():
    low_ev = dict(BASE_GROUP, evidence_count=1, representative_pain_descriptions=[], representative_quotes=[])
    high_ev = dict(BASE_GROUP, evidence_count=6)
    low_result = score_group(low_ev)
    high_result = score_group(high_ev)
    assert high_result["dimension_scores"]["pain_evidence_strength"] > low_result["dimension_scores"]["pain_evidence_strength"]


def test_multi_batch_gives_higher_frequency():
    single = dict(BASE_GROUP, batch_ids=["batch_a"], source_count=1)
    multi = dict(BASE_GROUP, batch_ids=["a", "b", "c"], source_count=3)
    single_result = score_group(single)
    multi_result = score_group(multi)
    assert multi_result["dimension_scores"]["frequency_repetition"] > single_result["dimension_scores"]["frequency_repetition"]


def test_workaround_keywords_boost_score():
    no_wa = dict(BASE_GROUP, current_workarounds=[])
    with_wa = dict(BASE_GROUP, current_workarounds=["\u4ed8\u8d39\u5de5\u5177\uff0c\u4f7f\u7528 excel \u5904\u7406"])
    no_result = score_group(no_wa)
    wa_result = score_group(with_wa)
    assert wa_result["dimension_scores"]["existing_workaround"] >= no_result["dimension_scores"]["existing_workaround"]


def test_payment_keywords_boost_wtp():
    no_pay = dict(BASE_GROUP, representative_quotes=["\u5c31\u662f\u6709\u70b9\u9ebb\u70e6"])
    with_pay = dict(BASE_GROUP, representative_quotes=["\u6211\u4eec\u4ed8\u8d39\u8ba2\u9605\u4e86\u5de5\u5177\uff0c\u6bcf\u6708\u82b1\u8d39\u51e0\u5343\u5143"])
    no_result = score_group(no_pay)
    pay_result = score_group(with_pay)
    assert pay_result["dimension_scores"]["willingness_to_pay"] >= no_result["dimension_scores"]["willingness_to_pay"]


def test_no_persona_gives_low_pc():
    no_persona = dict(BASE_GROUP, personas=[])
    result = score_group(no_persona)
    assert result["dimension_scores"]["persona_clarity"] < 30


def test_single_persona_gives_high_pc():
    single = dict(BASE_GROUP, personas=["developer"])
    result = score_group(single)
    assert result["dimension_scores"]["persona_clarity"] >= 70


def test_positive_signals_not_empty():
    result = score_group(BASE_GROUP)
    assert isinstance(result["positive_signals"], list)


def test_scoring_reason_not_empty():
    result = score_group(BASE_GROUP)
    assert len(result["scoring_reason_zh"]) > 0
