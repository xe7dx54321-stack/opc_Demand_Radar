"""Tests for the semantic merge audit report."""
from __future__ import annotations

from pathlib import Path


def test_semantic_merge_audit_exists():
    audit_path = Path("outputs/semantic_merge_audit.md")
    assert audit_path.exists(), "outputs/semantic_merge_audit.md should be generated"
    content = audit_path.read_text(encoding="utf-8")
    assert "Existing Capabilities" in content
    assert "Missing Capabilities" in content
    assert "Recommended Implementation Path" in content
    assert "Compatibility Risks" in content


def test_semantic_merge_audit_covers_key_topics():
    audit_path = Path("outputs/semantic_merge_audit.md")
    if not audit_path.exists():
        import pytest
        pytest.skip("Audit file not yet generated")
    content = audit_path.read_text(encoding="utf-8")
    assert "LLM" in content
    assert "run-stage28" in content
    assert "Review UI" in content or "UI" in content
