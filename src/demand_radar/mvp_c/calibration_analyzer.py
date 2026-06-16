"""MVP-C: Calibration analyzer - derives findings from human reviews."""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import Counter

from demand_radar.mvp_c.review_schema import PainSignalReview


@dataclass
class CalibrationFinding:
    finding_id: str
    finding_type: str
    severity: str
    description_zh: str
    affected_items: list[str] = field(default_factory=list)
    recommended_fix_zh: str = ""
    target_artifact: str | None = None


def analyze_reviews(reviews: list[PainSignalReview]) -> list[CalibrationFinding]:
    """Derive calibration findings from completed reviews."""
    findings: list[CalibrationFinding] = []
    n = 0

    if not reviews:
        return findings

    # Count patterns
    extraction_bad = [r for r in reviews if r.extraction_quality == "bad"]
    extraction_partial = [r for r in reviews if r.extraction_quality == "partial"]
    domain_too_loose = [r for r in reviews if r.domain_relevance_quality == "too_loose"]
    domain_too_strict = [r for r in reviews if r.domain_relevance_quality == "too_strict"]
    evidence_fake = [r for r in reviews if r.evidence_quality == "fake_or_insufficient"]
    false_pains = [r for r in reviews if r.true_pain is False]

    error_counter: Counter = Counter()
    for r in reviews:
        error_counter.update(r.error_labels)

    # Prompt issue: extraction quality bad >= 2
    if len(extraction_bad) >= 2:
        n += 1
        findings.append(CalibrationFinding(
            finding_id=f"finding_{n:03d}",
            finding_type="prompt_issue",
            severity="high",
            description_zh=f"{len(extraction_bad)} 条抽取质量被标为 bad，说明提取 prompt 对输出格式或内容理解不够。",
            affected_items=[r.pain_item_id for r in extraction_bad],
            recommended_fix_zh='强化 acquired_signal_pain_extraction_prompt_v1.md 中对 evidence_quote 真实性和 persona 精准度的约束。考虑增加 few-shot 示例。',
            target_artifact="docs/prompts/acquired_signal_pain_extraction_prompt_v1.md",
        ))

    # Prompt issue: bad_quote label
    if error_counter.get("bad_quote", 0) >= 1:
        n += 1
        findings.append(CalibrationFinding(
            finding_id=f"finding_{n:03d}",
            finding_type="prompt_issue",
            severity="high",
            description_zh=f"发现 {error_counter['bad_quote']} 条 bad_quote 标注，说明 LLM 输出的 evidence_quote 不够真实或脱离原文。",
            affected_items=[r.pain_item_id for r in reviews if "bad_quote" in r.error_labels],
            recommended_fix_zh='在 prompt 中更强调 evidence_quote 必须是原文逐字摘录，并在 pain_extraction_runner 中加强 quote 校验逻辑。',
            target_artifact="docs/prompts/acquired_signal_pain_extraction_prompt_v1.md",
        ))

    # Prompt issue: missed_commercial_signal
    if error_counter.get("missed_commercial_signal", 0) >= 1:
        n += 1
        findings.append(CalibrationFinding(
            finding_id=f"finding_{n:03d}",
            finding_type="prompt_issue",
            severity="medium",
            description_zh=f"发现 {error_counter['missed_commercial_signal']} 条 missed_commercial_signal 标注，说明 prompt 对商业信号提取不足。",
            affected_items=[r.pain_item_id for r in reviews if "missed_commercial_signal" in r.error_labels],
            recommended_fix_zh='在 prompt 中增加对 paid_alternative、budget_signal、订阅、采购意图的敏感度要求。',
            target_artifact="docs/prompts/acquired_signal_pain_extraction_prompt_v1.md",
        ))

    # Prompt issue: hallucinated_field
    if error_counter.get("hallucinated_field", 0) >= 1:
        n += 1
        findings.append(CalibrationFinding(
            finding_id=f"finding_{n:03d}",
            finding_type="prompt_issue",
            severity="high",
            description_zh=f"发现 {error_counter['hallucinated_field']} 条 hallucinated_field 标注，说明 LLM 编造了原文中不存在的内容。",
            affected_items=[r.pain_item_id for r in reviews if "hallucinated_field" in r.error_labels],
            recommended_fix_zh='在 prompt 系统指令中加强「禁止编造，只提取原文支持的内容」的约束，并在 pipeline 中增加字段级别的来源校验。',
            target_artifact="docs/prompts/acquired_signal_pain_extraction_prompt_v1.md",
        ))

    # Domain relevance rule issue: too_loose >= 2
    if len(domain_too_loose) >= 2:
        n += 1
        findings.append(CalibrationFinding(
            finding_id=f"finding_{n:03d}",
            finding_type="relevance_rule_issue",
            severity="medium",
            description_zh=f"{len(domain_too_loose)} 条被标为 domain_relevance_quality=too_loose，说明领域相关性过滤规则放行了过多域外内容。",
            affected_items=[r.pain_item_id for r in domain_too_loose],
            recommended_fix_zh='提高 domain_relevance_config.yaml 中 include 阈值（当前 0.65），或增强 negative_keywords 列表。',
            target_artifact="configs/domain_relevance_config.yaml",
        ))

    # Domain relevance rule issue: too_strict >= 2
    if len(domain_too_strict) >= 2:
        n += 1
        findings.append(CalibrationFinding(
            finding_id=f"finding_{n:03d}",
            finding_type="relevance_rule_issue",
            severity="medium",
            description_zh=f"{len(domain_too_strict)} 条被标为 domain_relevance_quality=too_strict，说明领域相关性规则过于严格，漏掉了有价值信号。",
            affected_items=[r.pain_item_id for r in domain_too_strict],
            recommended_fix_zh='降低 include 阈值（0.65→0.55），或扩展 weak_positive_keywords 列表。',
            target_artifact="configs/domain_relevance_config.yaml",
        ))

    # Source weight issue: evidence_quality=fake_or_insufficient >= 2
    if len(evidence_fake) >= 2:
        n += 1
        findings.append(CalibrationFinding(
            finding_id=f"finding_{n:03d}",
            finding_type="source_weight_issue",
            severity="high",
            description_zh=f"{len(evidence_fake)} 条证据质量被标为 fake_or_insufficient，说明来源权重配置可能过度信任某类来源。",
            affected_items=[r.pain_item_id for r in evidence_fake],
            recommended_fix_zh='检查 source_weighting_v1.md 中该来源类型的权重，考虑降低 rss 或 manual_url 类来源权重，优先 community_discussion 和 github_issue。',
            target_artifact="docs/rules/source_weighting_v1.md",
        ))

    # Source weak label
    if error_counter.get("source_too_weak", 0) >= 2:
        n += 1
        findings.append(CalibrationFinding(
            finding_id=f"finding_{n:03d}",
            finding_type="source_weight_issue",
            severity="medium",
            description_zh=f"{error_counter['source_too_weak']} 条被标为 source_too_weak，说明部分来源质量不足以支撑痛点判断。",
            affected_items=[r.pain_item_id for r in reviews if "source_too_weak" in r.error_labels],
            recommended_fix_zh='优化 acquisition query，减少纯 RSS/marketing 来源，提高 HN/GitHub issue/product_review 的占比。',
            target_artifact="configs/source_registry_ai_investment_tracking.yaml",
        ))

    # False pain rate high
    total = len(reviews)
    if total > 0 and len(false_pains) / total >= 0.5:
        n += 1
        findings.append(CalibrationFinding(
            finding_id=f"finding_{n:03d}",
            finding_type="evidence_quality_issue",
            severity="high",
            description_zh=f"{len(false_pains)}/{total} 条被标为 false_pain（占比 {100*len(false_pains)//total}%），说明整体信号质量偏低。",
            affected_items=[r.pain_item_id for r in false_pains],
            recommended_fix_zh='检查 acquisition query 和 domain relevance filter，提高入池门槛；同时检查 pain extraction prompt 是否过度 include 产品描述页面。',
            target_artifact="configs/domain_relevance_config.yaml",
        ))

    # Generic / too_generic error
    if error_counter.get("too_generic", 0) >= 2:
        n += 1
        findings.append(CalibrationFinding(
            finding_id=f"finding_{n:03d}",
            finding_type="prompt_issue",
            severity="low",
            description_zh=f"{error_counter['too_generic']} 条被标为 too_generic，说明抽取出的痛点描述不够具体。",
            affected_items=[r.pain_item_id for r in reviews if "too_generic" in r.error_labels],
            recommended_fix_zh='在 prompt 中要求痛点描述必须包含具体场景、任务和结果，不得只写泛泛的"信息过多"或"效率低"。',
            target_artifact="docs/prompts/acquired_signal_pain_extraction_prompt_v1.md",
        ))

    # Positive signal: no findings
    if not findings:
        findings.append(CalibrationFinding(
            finding_id="finding_001",
            finding_type="no_issues",
            severity="low",
            description_zh='暂无明显校准问题。当前 review 数量较少，建议完成全部 pain signals 的人工审核后再运行。',
            recommended_fix_zh='完成所有 pain signals 的 review 后重新生成 calibration_recommendations。',
        ))

    return findings
