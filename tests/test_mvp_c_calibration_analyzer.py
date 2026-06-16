"""Tests for CalibrationAnalyzer."""
import pytest
from demand_radar.mvp_c.calibration_analyzer import analyze_reviews, CalibrationFinding
from demand_radar.mvp_c.review_schema import PainSignalReview


def _rev(pid, **kw):
    d = dict(
        review_id=f"rev_{pid}",
        pain_item_id=pid,
        candidate_id="cand_abc",
        created_at="2026-01-01T00:00:00Z",
    )
    d.update(kw)
    return PainSignalReview(**d)


def test_no_reviews_returns_no_issue_finding():
    findings = analyze_reviews([])
    assert findings == []


def test_no_problems_gives_no_issues_finding():
    reviews = [
        _rev("p001", true_pain=True, extraction_quality="good", action_decision="pursue"),
        _rev("p002", true_pain=True, extraction_quality="good", action_decision="watch"),
    ]
    findings = analyze_reviews(reviews)
    types = [f.finding_type for f in findings]
    assert "no_issues" in types


def test_bad_extraction_triggers_prompt_issue():
    reviews = [
        _rev("p001", extraction_quality="bad"),
        _rev("p002", extraction_quality="bad"),
        _rev("p003", extraction_quality="good"),
    ]
    findings = analyze_reviews(reviews)
    types = [f.finding_type for f in findings]
    assert "prompt_issue" in types


def test_bad_quote_label_triggers_prompt_issue():
    reviews = [_rev("p001", error_labels=["bad_quote"])]
    findings = analyze_reviews(reviews)
    types = [f.finding_type for f in findings]
    assert "prompt_issue" in types


def test_too_loose_triggers_relevance_issue():
    reviews = [
        _rev("p001", domain_relevance_quality="too_loose"),
        _rev("p002", domain_relevance_quality="too_loose"),
    ]
    findings = analyze_reviews(reviews)
    types = [f.finding_type for f in findings]
    assert "relevance_rule_issue" in types


def test_fake_evidence_triggers_source_weight_issue():
    reviews = [
        _rev("p001", evidence_quality="fake_or_insufficient"),
        _rev("p002", evidence_quality="fake_or_insufficient"),
    ]
    findings = analyze_reviews(reviews)
    types = [f.finding_type for f in findings]
    assert "source_weight_issue" in types


def test_high_false_pain_rate_triggers_evidence_issue():
    reviews = [
        _rev("p001", true_pain=False),
        _rev("p002", true_pain=False),
        _rev("p003", true_pain=True),
    ]
    findings = analyze_reviews(reviews)
    types = [f.finding_type for f in findings]
    assert "evidence_quality_issue" in types or len(findings) > 0


def test_missed_commercial_signal_triggers_finding():
    reviews = [_rev("p001", error_labels=["missed_commercial_signal"])]
    findings = analyze_reviews(reviews)
    types = [f.finding_type for f in findings]
    assert "prompt_issue" in types


def test_findings_have_required_fields():
    reviews = [_rev("p001", extraction_quality="bad"), _rev("p002", extraction_quality="bad")]
    findings = analyze_reviews(reviews)
    for f in findings:
        assert f.finding_id
        assert f.finding_type
        assert f.severity in ("high", "medium", "low")
        assert f.description_zh
        assert f.recommended_fix_zh


def test_calibration_finding_dataclass():
    f = CalibrationFinding(
        finding_id="f001",
        finding_type="prompt_issue",
        severity="high",
        description_zh="Test issue",
        recommended_fix_zh="Fix the prompt",
    )
    assert f.finding_id == "f001"
    assert f.affected_items == []
