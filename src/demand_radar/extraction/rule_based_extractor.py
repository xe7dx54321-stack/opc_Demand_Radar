"""Rule-based pain extractor used by default in Stage 1."""

from __future__ import annotations

import re

from demand_radar.config.schemas import NormalizedSignal
from demand_radar.extraction.base import PainPointCandidate


PAIN_KEYWORDS_EN = [
    "pain",
    "problem",
    "hard",
    "difficult",
    "frustrating",
    "waste time",
    "manual",
    "scattered",
    "miss",
    "incomplete",
    "expensive",
    "slow",
    "broken",
    "struggle",
    "can't keep up",
    "too much time",
    "hard to track",
    "hard to verify",
    "manual process",
    "scattered across",
    "miss important updates",
    "not reliable",
    "too noisy",
    "no good way",
    "hard to compare",
    "hard to summarize",
    "hard to find",
]

PAIN_KEYWORDS_ZH = [
    "\u75db\u70b9",
    "\u9ebb\u70e6",
    "\u5f88\u96be",
    "\u56f0\u96be",
    "\u4f4e\u6548",
    "\u8017\u65f6",
    "\u624b\u52a8",
    "\u5206\u6563",
    "\u9057\u6f0f",
    "\u4e0d\u5b8c\u6574",
    "\u592a\u8d35",
    "\u592a\u6162",
    "\u4e0d\u597d\u7528",
    "\u8ddf\u4e0d\u4e0a",
    "\u592a\u5206\u6563",
    "\u4e0d\u597d\u8ffd\u8e2a",
    "\u4e0d\u597d\u9a8c\u8bc1",
    "\u4eba\u5de5\u6574\u7406",
    "\u4fe1\u606f\u592a\u4e71",
    "\u566a\u97f3\u592a\u591a",
    "\u5bb9\u6613\u6f0f",
    "\u6ca1\u6709\u597d\u529e\u6cd5",
    "\u96be\u6bd4\u8f83",
    "\u96be\u603b\u7ed3",
    "\u96be\u7b5b\u9009",
    "\u8d39\u65f6\u95f4",
    "\u6548\u7387\u4f4e",
]

SENTENCE_BOUNDARY_RE = re.compile(r"[^.!?\u3002\uff01\uff1f]+[.!?\u3002\uff01\uff1f]?")
MAX_EVIDENCE_QUOTE_CHARS = 300


class RuleBasedPainExtractor:
    extraction_mode = "rule_based"

    def extract(
        self,
        signal: NormalizedSignal,
        pain_point_id: str,
        working_context: dict[str, object],
    ) -> list[PainPointCandidate]:
        text = signal.normalized_text
        evidence_quote = _find_evidence_quote(text)
        if not evidence_quote:
            return [{
                "pain_point_id": pain_point_id,
                "raw_signal_id": signal.raw_signal_id,
                "normalized_signal_id": signal.normalized_signal_id,
                "persona": _infer_persona(text),
                "scenario": signal.title,
                "job_to_be_done": None,
                "current_workaround": None,
                "pain_description": "",
                "pain_intensity": None,
                "frequency_signal": None,
                "payment_signal": None,
                "evidence_quote": "",
                "evidence_span": None,
                "confidence": 0.2,
                "extraction_mode": self.extraction_mode,
                "extraction_notes": "No pain keyword matched.",
            }]

        return [{
            "pain_point_id": pain_point_id,
            "raw_signal_id": signal.raw_signal_id,
            "normalized_signal_id": signal.normalized_signal_id,
            "persona": _infer_persona(text),
            "scenario": signal.title,
            "job_to_be_done": _infer_job_to_be_done(text),
            "current_workaround": _infer_workaround(text),
            "pain_description": _summarize_pain(evidence_quote),
            "pain_intensity": _infer_intensity(evidence_quote),
            "frequency_signal": _infer_frequency(text),
            "payment_signal": _infer_payment_signal(text),
            "evidence_quote": evidence_quote,
            "evidence_span": evidence_quote,
            "confidence": _infer_confidence(evidence_quote),
            "extraction_mode": self.extraction_mode,
            "extraction_notes": "Matched pain keyword with local rule-based extractor.",
        }]


def _find_evidence_quote(text: str) -> str:
    spans = _sentence_spans(text)
    for index, (sentence, _, _) in enumerate(spans):
        lowered = sentence.lower()
        if any(keyword in lowered for keyword in PAIN_KEYWORDS_EN) or any(keyword in sentence for keyword in PAIN_KEYWORDS_ZH):
            return _expand_sentence_quote(text, spans, index)
    return ""


def _sentences(text: str) -> list[str]:
    return [sentence for sentence, _, _ in _sentence_spans(text)]


def _sentence_spans(text: str) -> list[tuple[str, int, int]]:
    spans: list[tuple[str, int, int]] = []
    for match in SENTENCE_BOUNDARY_RE.finditer(text):
        raw_sentence = match.group(0)
        leading = len(raw_sentence) - len(raw_sentence.lstrip())
        trailing = len(raw_sentence.rstrip())
        sentence = raw_sentence.strip()
        if sentence:
            start = match.start() + leading
            end = match.start() + trailing
            spans.append((sentence, start, end))
    return spans


def _expand_sentence_quote(text: str, spans: list[tuple[str, int, int]], index: int) -> str:
    quote, start, end = spans[index]
    if len(quote) < 40:
        if index > 0:
            prev_start = spans[index - 1][1]
            candidate = text[prev_start:end].strip()
            if len(candidate) <= MAX_EVIDENCE_QUOTE_CHARS:
                return candidate
        if index + 1 < len(spans):
            next_end = spans[index + 1][2]
            candidate = text[start:next_end].strip()
            if len(candidate) <= MAX_EVIDENCE_QUOTE_CHARS:
                return candidate
    return quote[:MAX_EVIDENCE_QUOTE_CHARS]


def _infer_persona(text: str) -> str | None:
    lowered = text.lower()
    mapping = {
        "investor": ["investor", "vc", "fund", "investment", "\u6295\u8d44\u4eba", "\u57fa\u91d1", "\u6295\u8d44", "\u5c3d\u8c03"],
        "researcher": ["researcher", "analyst", "research", "\u7814\u7a76\u5458", "\u5206\u6790\u5e08", "\u7814\u7a76"],
        "founder": ["founder", "startup", "ceo", "\u521b\u59cb\u4eba", "\u521b\u4e1a\u8005", "\u521b\u4e1a"],
        "content_team": ["content", "newsletter", "media", "article", "creator", "\u5185\u5bb9", "\u9009\u9898", "\u516c\u4f17\u53f7", "\u521b\u4f5c\u8005"],
        "developer": ["developer", "api", "github", "issue", "sdk", "code", "\u5f00\u53d1\u8005", "\u63a5\u53e3", "\u4ee3\u7801"],
        "operator": ["operator", "ops", "workflow", "sop", "\u8fd0\u8425", "\u6d41\u7a0b"],
        "strategy_bd": ["sales", "bd", "lead", "crm", "\u6218\u7565", "\u9500\u552e", "\u7ebf\u7d22", "\u5546\u52a1"],
    }
    best_persona: str | None = None
    best_count = 0
    for persona, keywords in mapping.items():
        count = sum(1 for keyword in keywords if _keyword_matches(lowered, keyword))
        if count > best_count:
            best_persona = persona
            best_count = count
    return best_persona


def _keyword_matches(lowered_text: str, keyword: str) -> bool:
    if keyword.isascii() and keyword.replace(" ", "").isalnum():
        return re.search(rf"(?<![a-z0-9]){re.escape(keyword.lower())}(?![a-z0-9])", lowered_text) is not None
    return keyword in lowered_text


def _infer_job_to_be_done(text: str) -> str | None:
    lowered = text.lower()
    if any(word in lowered for word in ["track", "monitor", "\u8ddf\u8e2a", "\u76d1\u63a7"]):
        return "track and monitor high-value information across sources"
    if any(word in lowered for word in ["write", "content", "newsletter", "article", "\u5185\u5bb9", "\u9009\u9898"]):
        return "produce reliable content from scattered inputs"
    if any(word in lowered for word in ["agent", "workflow", "\u81ea\u52a8\u5316", "\u6d41\u7a0b"]):
        return "run a repeated AI-assisted workflow reliably"
    if any(word in lowered for word in ["api", "github", "code", "\u5f00\u53d1\u8005"]):
        return "complete developer workflow with less friction"
    return None


def _infer_workaround(text: str) -> str | None:
    lowered = text.lower()
    if any(word in lowered for word in ["spreadsheet", "excel", "\u8868\u683c"]):
        return "manual spreadsheet tracking"
    if any(word in lowered for word in ["manual", "\u624b\u52a8", "\u4eba\u5de5"]):
        return "manual work"
    if any(word in lowered for word in ["database", "subscription", "paid", "\u6570\u636e\u5e93", "\u4ed8\u8d39"]):
        return "paid database or subscription"
    return None


def _infer_frequency(text: str) -> str | None:
    lowered = text.lower()
    if any(word in lowered for word in ["daily", "every day", "\u6bcf\u5929"]):
        return "daily"
    if any(word in lowered for word in ["weekly", "every week", "\u6bcf\u5468"]):
        return "weekly"
    if any(word in lowered for word in ["monthly", "\u6bcf\u6708"]):
        return "monthly"
    return None


def _infer_payment_signal(text: str) -> str | None:
    lowered = text.lower()
    if any(
        word in lowered
        for word in ["paid", "subscription", "budget", "expensive", "\u6570\u636e\u5e93", "\u4ed8\u8d39", "\u9884\u7b97", "\u592a\u8d35"]
    ):
        return "paid alternative or budget signal mentioned"
    if any(word in lowered for word in ["hours", "manual", "\u8017\u65f6", "\u624b\u52a8", "\u4eba\u5de5"]):
        return "labor/time cost signal mentioned"
    return None


def _infer_intensity(quote: str) -> int:
    lowered = quote.lower()
    if any(word in lowered for word in ["broken", "impossible", "\u4e0d\u597d\u7528", "\u5f88\u96be", "\u75db\u70b9"]):
        return 5
    if any(word in lowered for word in ["frustrating", "waste time", "hard", "difficult", "\u8017\u65f6", "\u4f4e\u6548", "\u9ebb\u70e6"]):
        return 4
    if any(word in lowered for word in ["manual", "scattered", "slow", "\u624b\u52a8", "\u5206\u6563", "\u592a\u6162"]):
        return 3
    return 2


def _infer_confidence(quote: str) -> float:
    lowered = quote.lower()
    if any(keyword in lowered for keyword in ["pain", "problem", "frustrating", "waste time", "broken"]) or any(
        keyword in quote for keyword in ["\u75db\u70b9", "\u9ebb\u70e6", "\u4f4e\u6548", "\u8017\u65f6", "\u4e0d\u597d\u7528"]
    ):
        return 0.82
    return 0.72


def _summarize_pain(quote: str) -> str:
    return quote[:220]
