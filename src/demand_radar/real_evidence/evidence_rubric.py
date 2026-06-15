"""Stage R1: Evidence scoring rubric."""
from __future__ import annotations

# Keywords that indicate a paid/budget signal
PAY_KW = [
    "pay", "paid", "price", "pricing", "subscription", "budget", "cost", "fee",
    "purchase", "procure", "vendor", "contract", "saas", "annual",
    "\u4ed8\u8d39", "\u8ba2\u9605", "\u9884\u7b97", "\u91c7\u8d2d",
    "\u8d2d\u4e70", "\u5e74\u8d39", "\u6708\u8d39", "\u5b9a\u4ef7",
    "\u5408\u540c", "\u62a5\u4ef7",
]

# Keywords indicating manual workaround / current solution
WORKAROUND_KW = [
    "manual", "spreadsheet", "excel", "workaround", "outsource", "script",
    "copy paste", "copy-paste", "hand", "manually", "ad hoc", "ad-hoc",
    "\u4eba\u5de5", "\u624b\u5de5", "\u8868\u683c", "\u5916\u5305",
    "\u624b\u52a8", "\u811a\u672c", "\u95ee\u540c\u4e8b",
]

# Keywords indicating business impact / time cost
IMPACT_KW = [
    "hours", "time", "delay", "miss", "slow", "inefficient", "waste",
    "cost", "expensive", "labor", "productivity", "bottleneck",
    "\u65f6\u95f4", "\u4eba\u529b", "\u5ef6\u8bef", "\u6d6a\u8d39",
    "\u6548\u7387", "\u91cd\u590d\u52b3\u52a8", "\u6210\u672c",
]

# Marketing-only indicators (reduce credibility)
MARKETING_KW = [
    "leading", "best-in-class", "enterprise-grade", "cutting-edge",
    "revolutionary", "game-changing", "next-generation", "world-class",
]


def _has(text: str, kws: list[str]) -> bool:
    lo = text.lower()
    return any(k.lower() in lo for k in kws)


def score_evidence_strength(raw_text: str, source_type: str) -> dict:
    """Return a rubric score dict for an evidence item."""
    if len(raw_text.strip()) < 80:
        return {"rubric_score": 0.0, "tier": "reject", "has_pay_signal": False, "has_workaround_signal": False, "has_impact_signal": False, "has_marketing_noise": False}
    has_pay = _has(raw_text, PAY_KW)
    has_workaround = _has(raw_text, WORKAROUND_KW)
    has_impact = _has(raw_text, IMPACT_KW)
    has_marketing = _has(raw_text, MARKETING_KW)
    long_enough = len(raw_text.strip()) >= 120

    high_value_sources = {
        "product_review", "community_discussion", "github_issue",
        "interview_note", "case_study",
    }

    score = 0.0
    if source_type in high_value_sources:
        score += 0.3
    if has_pay:
        score += 0.25
    if has_workaround:
        score += 0.25
    if has_impact:
        score += 0.15
    if long_enough:
        score += 0.05
    if has_marketing and source_type not in {"product_review", "case_study"}:
        score -= 0.15

    tier = "strong" if score >= 0.55 else "medium" if score >= 0.30 else "weak"

    return {
        "rubric_score": round(max(0.0, min(1.0, score)), 3),
        "tier": tier,
        "has_pay_signal": has_pay,
        "has_workaround_signal": has_workaround,
        "has_impact_signal": has_impact,
        "has_marketing_noise": has_marketing,
    }
