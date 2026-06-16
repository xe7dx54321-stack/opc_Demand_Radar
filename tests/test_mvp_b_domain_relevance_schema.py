"""Tests for DomainRelevanceResult schema."""
import pytest
from demand_radar.mvp_b.domain_relevance_schema import DomainRelevanceResult


def _base(**kw):
    defaults = dict(
        result_id="rel_001",
        candidate_id="cand_001",
        relevance_decision="include",
        relevance_score=0.75,
        domain_reason_zh="Strong investment research signal",
        created_at="2026-01-01T00:00:00Z",
    )
    defaults.update(kw)
    return defaults


def test_valid_include():
    r = DomainRelevanceResult(**_base())
    assert r.relevance_decision == "include"
    assert r.relevance_score == 0.75


def test_valid_exclude():
    r = DomainRelevanceResult(**_base(
        relevance_decision="exclude",
        relevance_score=0.1,
        domain_reason_zh=None,
        exclude_reason_zh="Recipe app - not investment domain",
    ))
    assert r.relevance_decision == "exclude"


def test_valid_uncertain():
    r = DomainRelevanceResult(**_base(
        relevance_decision="uncertain",
        relevance_score=0.5,
        domain_reason_zh=None,
    ))
    assert r.relevance_decision == "uncertain"


def test_score_out_of_range_raises():
    with pytest.raises(Exception):
        DomainRelevanceResult(**_base(relevance_score=1.5))


def test_score_negative_raises():
    with pytest.raises(Exception):
        DomainRelevanceResult(**_base(relevance_score=-0.1))


def test_exclude_needs_reason():
    with pytest.raises(Exception):
        DomainRelevanceResult(**_base(
            relevance_decision="exclude",
            relevance_score=0.1,
            domain_reason_zh=None,
            exclude_reason_zh=None,
        ))


def test_include_needs_domain_reason():
    with pytest.raises(Exception):
        DomainRelevanceResult(**_base(domain_reason_zh=None))


def test_optional_fields_default_none():
    r = DomainRelevanceResult(**_base())
    assert r.matched_persona is None
    assert r.matched_workflow is None
    assert r.model is None
