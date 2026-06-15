"""Schemas for Stage 2.7 semantic merge judgments."""

from __future__ import annotations

from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from demand_radar.state.raw_store import utc_now_iso


SemanticMergeDecision = Literal["confirm_merge", "reject_merge", "maybe_merge"]
SemanticMergeAutoAction = Literal["auto_confirm", "auto_reject", "human_exception"]
SemanticMergeJudgeMode = Literal["rule_based_stub", "llm"]
ExceptionPriority = Literal["high", "medium", "low"]

VALID_SEMANTIC_MERGE_DECISIONS = {"confirm_merge", "reject_merge", "maybe_merge"}
VALID_AUTO_ACTIONS = {"auto_confirm", "auto_reject", "human_exception"}
VALID_JUDGE_MODES = {"rule_based_stub", "llm"}
VALID_CONFLICT_FLAGS = {
    "different_persona",
    "different_workflow",
    "different_pain",
    "weak_evidence",
    "ambiguous_scope",
    "too_broad",
    "too_narrow",
    "title_mismatch",
}
SEVERE_CONFLICT_FLAGS = {
    "different_persona",
    "different_workflow",
    "different_pain",
    "weak_evidence",
    "ambiguous_scope",
}
VALID_SEMANTIC_HUMAN_AUDIT_LABELS = {
    "ai_correct",
    "ai_wrong_confirm",
    "ai_wrong_reject",
    "correct_to_confirm",
    "correct_to_reject",
    "bad_reason",
    "needs_rerun",
}


class SemanticMergeJudgment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid_decisions: ClassVar[set[str]] = VALID_SEMANTIC_MERGE_DECISIONS
    valid_auto_actions: ClassVar[set[str]] = VALID_AUTO_ACTIONS
    valid_judge_modes: ClassVar[set[str]] = VALID_JUDGE_MODES
    valid_conflict_flags: ClassVar[set[str]] = VALID_CONFLICT_FLAGS

    judgment_id: str
    merge_candidate_id: str
    cluster_id_a: str
    cluster_id_b: str
    decision: str
    confidence: float
    reason_zh: str
    evidence_alignment_zh: str | None = None
    workflow_judgment_zh: str | None = None
    suggested_group_title_zh: str | None = None
    suggested_group_summary_zh: str | None = None
    conflict_flags: list[str] = Field(default_factory=list)
    auto_action: str
    judge_mode: str
    created_at: str = Field(default_factory=utc_now_iso)

    @field_validator(
        "judgment_id",
        "merge_candidate_id",
        "cluster_id_a",
        "cluster_id_b",
        "decision",
        "reason_zh",
        "auto_action",
        "judge_mode",
        "created_at",
    )
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value

    @field_validator("decision")
    @classmethod
    def valid_decision(cls, value: str) -> str:
        if value not in cls.valid_decisions:
            raise ValueError(f"unsupported semantic merge decision: {value}")
        return value

    @field_validator("auto_action")
    @classmethod
    def valid_auto_action(cls, value: str) -> str:
        if value not in cls.valid_auto_actions:
            raise ValueError(f"unsupported semantic merge auto_action: {value}")
        return value

    @field_validator("judge_mode")
    @classmethod
    def valid_judge_mode(cls, value: str) -> str:
        if value not in cls.valid_judge_modes:
            raise ValueError(f"unsupported semantic merge judge_mode: {value}")
        return value

    @field_validator("confidence")
    @classmethod
    def confidence_between_zero_and_one(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return value

    @field_validator("reason_zh")
    @classmethod
    def reason_must_be_chinese(cls, value: str) -> str:
        if not any("\u4e00" <= char <= "\u9fff" for char in value):
            raise ValueError("reason_zh must contain Chinese text")
        return value

    @field_validator("conflict_flags")
    @classmethod
    def validate_conflict_flags(cls, values: list[str]) -> list[str]:
        cleaned: list[str] = []
        for value in values:
            flag = value.strip()
            if not flag:
                continue
            if flag not in cls.valid_conflict_flags:
                raise ValueError(f"unsupported semantic merge conflict flag: {flag}")
            if flag not in cleaned:
                cleaned.append(flag)
        return cleaned

    @model_validator(mode="after")
    def validate_pair_and_action(self) -> "SemanticMergeJudgment":
        if self.cluster_id_a == self.cluster_id_b:
            raise ValueError("cluster_id_a and cluster_id_b must be different")
        if self.auto_action == "auto_confirm" and self.decision != "confirm_merge":
            raise ValueError("auto_confirm requires confirm_merge decision")
        if self.auto_action == "auto_reject" and self.decision != "reject_merge":
            raise ValueError("auto_reject requires reject_merge decision")
        return self


class HumanExceptionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exception_id: str
    judgment_id: str
    merge_candidate_id: str
    cluster_id_a: str
    cluster_id_b: str
    exception_reason: str
    priority: ExceptionPriority
    decision: str
    confidence: float
    conflict_flags: list[str] = Field(default_factory=list)
    reason_zh: str
    created_at: str = Field(default_factory=utc_now_iso)

    @field_validator(
        "exception_id",
        "judgment_id",
        "merge_candidate_id",
        "cluster_id_a",
        "cluster_id_b",
        "exception_reason",
        "priority",
        "decision",
        "reason_zh",
        "created_at",
    )
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value

    @field_validator("decision")
    @classmethod
    def valid_decision(cls, value: str) -> str:
        if value not in VALID_SEMANTIC_MERGE_DECISIONS:
            raise ValueError(f"unsupported semantic merge decision: {value}")
        return value

    @field_validator("confidence")
    @classmethod
    def confidence_between_zero_and_one(cls, value: float) -> float:
        if value < 0 or value > 1:
            raise ValueError("confidence must be between 0 and 1")
        return value


class AIReviewedClusterGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group_id: str
    group_title_zh: str
    group_summary_zh: str
    cluster_ids: list[str]
    related_pain_point_ids: list[str]
    personas: list[str] = Field(default_factory=list)
    domain_tags: list[str] = Field(default_factory=list)
    batch_ids: list[str] = Field(default_factory=list)
    evidence_count: int
    source_count: int
    representative_pain_descriptions: list[str] = Field(default_factory=list)
    representative_quotes: list[str] = Field(default_factory=list)
    current_workarounds: list[str] = Field(default_factory=list)
    created_by: str = "ai_semantic_merge"
    created_from_judgment_ids: list[str] = Field(default_factory=list)
    created_from_review_ids: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=utc_now_iso)

    @field_validator("group_id", "group_title_zh", "group_summary_zh", "created_by", "created_at")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value

    @field_validator("group_title_zh", "group_summary_zh")
    @classmethod
    def chinese_text_required(cls, value: str) -> str:
        if not any("\u4e00" <= char <= "\u9fff" for char in value):
            raise ValueError("group title and summary must contain Chinese text")
        return value

    @field_validator("cluster_ids", "related_pain_point_ids")
    @classmethod
    def non_empty_unique_ids(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            text = item.strip()
            if text and text not in cleaned:
                cleaned.append(text)
        if not cleaned:
            raise ValueError("id list must not be empty")
        return cleaned

    @model_validator(mode="after")
    def validate_group_counts(self) -> "AIReviewedClusterGroup":
        if len(self.cluster_ids) < 2:
            raise ValueError("AI reviewed cluster group must include at least two clusters")
        if self.evidence_count < 2:
            raise ValueError("evidence_count must be at least 2")
        if self.source_count < 1:
            raise ValueError("source_count must be at least 1")
        if self.created_by != "ai_semantic_merge":
            raise ValueError("created_by must be ai_semantic_merge")
        if not self.created_from_judgment_ids:
            raise ValueError("created_from_judgment_ids must not be empty")
        return self


class SemanticMergeHumanAudit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid_labels: ClassVar[set[str]] = VALID_SEMANTIC_HUMAN_AUDIT_LABELS

    audit_id: str
    judgment_id: str
    merge_candidate_id: str
    label: str
    reviewer_note: str | None = None
    corrected_decision: str | None = None
    created_at: str = Field(default_factory=utc_now_iso)

    @field_validator("audit_id", "judgment_id", "merge_candidate_id", "label", "created_at")
    @classmethod
    def required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value

    @field_validator("label")
    @classmethod
    def valid_label(cls, value: str) -> str:
        if value not in cls.valid_labels:
            raise ValueError(f"unsupported semantic merge audit label: {value}")
        return value

    @field_validator("corrected_decision")
    @classmethod
    def valid_corrected_decision(cls, value: str | None) -> str | None:
        if value is not None and value not in VALID_SEMANTIC_MERGE_DECISIONS:
            raise ValueError(f"unsupported corrected decision: {value}")
        return value
