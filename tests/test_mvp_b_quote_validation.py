"""Tests for evidence_quote validation logic."""
import pytest
from demand_radar.mvp_b.pain_extraction_runner import _check_quote_in_raw_text, _normalize_text


SAMPLE_RAW = (
    "Hi HN, I spent the last 10+ years working as an equity portfolio manager. "
    "For a long time I was obsessed with finding a tool to automate investment research. "
    "The current solution is spreadsheets and manual tracking which is terribly inefficient. "
    "We pay for multiple data subscriptions but still spend hours compiling information."
)


def test_exact_substring_match():
    quote = "The current solution is spreadsheets and manual tracking"
    assert _check_quote_in_raw_text(quote, SAMPLE_RAW) is True


def test_case_insensitive_match():
    quote = "THE CURRENT SOLUTION IS SPREADSHEETS AND MANUAL TRACKING"
    assert _check_quote_in_raw_text(quote, SAMPLE_RAW) is True


def test_quote_not_present():
    quote = "We use machine learning to automatically generate reports"
    assert _check_quote_in_raw_text(quote, SAMPLE_RAW) is False


def test_empty_quote():
    assert _check_quote_in_raw_text("", SAMPLE_RAW) is False


def test_none_quote():
    assert _check_quote_in_raw_text(None, SAMPLE_RAW) is False


def test_very_short_quote_rejected():
    assert _check_quote_in_raw_text("abc", SAMPLE_RAW) is False


def test_html_entities_in_raw_normalised():
    raw_html = "I&#x27;ve been building this platform for years &amp; it&#x27;s finally ready."
    quote = "I've been building this platform for years & it's finally ready."
    assert _check_quote_in_raw_text(quote, raw_html) is True


def test_normalise_whitespace():
    raw = "We  spend   many   hours   on   this   work."
    quote = "We spend many hours on this work."
    assert _check_quote_in_raw_text(quote, raw) is True


def test_partial_first_60_chars_match():
    """Only first 60 chars of quote are checked in the implementation."""
    # If first 60 chars match, it passes
    long_quote = "We pay for multiple data subscriptions but still spend hours"[:60]
    assert _check_quote_in_raw_text(long_quote, SAMPLE_RAW) is True


def test_normalize_html_tags():
    raw_html = "<p>Investment research is <strong>time consuming</strong> and tedious.</p>"
    norm = _normalize_text(raw_html)
    assert "investment research" in norm
    assert "<" not in norm
