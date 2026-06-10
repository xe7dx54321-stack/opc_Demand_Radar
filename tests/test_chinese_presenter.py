from demand_radar.ui.chinese_presenter import build_chinese_review_view, looks_like_english
from demand_radar.ui.review_service import ReviewItem


def test_english_pain_point_is_presented_as_chinese_summary() -> None:
    item = ReviewItem(
        raw_signal_id="sig_000001",
        normalized_signal_id="norm_000001",
        pain_point_id="pain_000001",
        item_type="pain_point",
        title="Tracking AI infra is too scattered",
        raw_text=(
            "I spend hours every week tracking AI infrastructure companies across blogs, "
            "GitHub, filings and newsletters. Paid databases miss many technical updates."
        ),
        normalized_text=(
            "I spend hours every week tracking AI infrastructure companies across blogs, "
            "GitHub, filings and newsletters. Paid databases miss many technical updates."
        ),
        source_name="manual_import",
        source_type="manual",
        language="en",
        domain_tags=["ai_investment_research"],
        persona="investor",
        scenario="tracking AI infrastructure companies",
        job_to_be_done="monitor company and technical updates",
        current_workaround="manual spreadsheet",
        pain_description="information is scattered and paid databases miss updates",
        evidence_quote=(
            "I spend hours every week tracking AI infrastructure companies across blogs, "
            "GitHub, filings and newsletters."
        ),
        confidence=0.82,
    )

    view = build_chinese_review_view(item)
    visible_text = "\n".join(
        [
            view.title,
            view.summary,
            view.scenario,
            view.job_to_be_done,
            view.pain_description,
            view.current_workaround,
            view.evidence_summary,
        ]
    )

    assert "I spend hours" not in visible_text
    assert "tracking AI infrastructure" not in visible_text
    assert "人工智能" in visible_text
    assert "投资团队" in visible_text or "投资人" in visible_text


def test_chinese_text_is_kept_readable() -> None:
    item = ReviewItem(
        raw_signal_id="sig_000002",
        item_type="raw_only",
        title="内容团队选题效率低",
        raw_text="内容团队每天找选题很费时间，信息太分散，最后还是人工整理到表格里。",
        language="zh",
        domain_tags=["content_production"],
    )

    view = build_chinese_review_view(item)

    assert "内容团队" in view.evidence_summary
    assert not looks_like_english(view.evidence_summary)
