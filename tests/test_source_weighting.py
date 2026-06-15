"""Tests for source_weighting module."""
from __future__ import annotations
from demand_radar.real_evidence.source_weighting import (
    SOURCE_WEIGHTS,
    get_source_weight,
    is_high_value_source,
)


def test_product_review_weight():
    assert get_source_weight("product_review") >= 0.90


def test_community_discussion_weight():
    assert get_source_weight("community_discussion") >= 0.85


def test_pricing_page_weight():
    w = get_source_weight("pricing_page")
    assert 0.60 <= w <= 0.80


def test_marketing_article_weight():
    w = get_source_weight("marketing_article")
    assert w <= 0.35


def test_unknown_source_weight():
    w = get_source_weight("completely_unknown")
    assert 0.0 < w < 0.50


def test_source_weights_all_between_0_1():
    for stype, w in SOURCE_WEIGHTS.items():
        assert 0.0 <= w <= 1.0, f"{stype} weight {w} out of range"


def test_product_review_is_high_value():
    assert is_high_value_source("product_review")


def test_interview_note_is_high_value():
    assert is_high_value_source("interview_note")


def test_marketing_article_not_high_value():
    assert not is_high_value_source("marketing_article")


def test_blog_post_not_high_value():
    assert not is_high_value_source("blog_post")