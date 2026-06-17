"""D5 source classifier tests."""
from __future__ import annotations

from demand_radar.d5.source_classifier import classify_source, source_weight


def test_reddit_is_first_hand_community() -> None:
    category, weight = classify_source({"source_url": "https://www.reddit.com/r/vc/comments/1", "result_domain": "www.reddit.com"})

    assert category == "first_hand_community"
    assert weight == 1.0


def test_vendor_blog_is_auxiliary_even_when_it_mentions_spreadsheets() -> None:
    category, weight = classify_source(
        {
            "source_url": "https://www.marvin-labs.com/resources/equity-research-automation",
            "result_domain": "www.marvin-labs.com",
            "evidence_quote": "Stop using spreadsheets and manual workflows.",
        }
    )

    assert category == "content_marketing"
    assert weight < source_weight("workaround_discussion")


def test_job_page_is_job_description() -> None:
    category, _ = classify_source({"source_url": "https://nvca.org/careers/analyst", "result_domain": "nvca.org"})

    assert category == "job_description"
