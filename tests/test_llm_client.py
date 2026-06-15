"""Tests for Stage 2.9 LLM client implementations."""
from __future__ import annotations

import json

import pytest

from demand_radar.semantic_merge.llm_client import (
    AnthropicCompatibleClient,
    FakeLLMClient,
    OpenAICompatibleClient,
    make_llm_client,
)


class TestOpenAICompatibleClient:
    def test_base_url_trailing_slash_stripped(self):
        client = OpenAICompatibleClient(
            base_url="https://api.openai.com/v1/",
            api_key="sk-test",
            model="gpt-4o",
        )
        assert not client.base_url.endswith("/")

    def test_request_format_correct(self, monkeypatch):
        """Verify the request body contains expected fields."""
        captured: list[dict] = []

        def fake_urlopen(req, timeout=None):
            import io
            captured.append(json.loads(req.data.decode("utf-8")))
            class FakeResp:
                def __enter__(self): return self
                def __exit__(self, *a): pass
                def read(self):
                    return json.dumps({"choices": [{"message": {"content": '{"decision":"maybe_merge","confidence":0.5,"reason_zh":"测试"}'}}]}).encode()
            return FakeResp()

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        client = OpenAICompatibleClient(base_url="http://fake", api_key="key", model="gpt-test")
        client.complete("system prompt", "user prompt")
        assert len(captured) == 1
        body = captured[0]
        assert body["model"] == "gpt-test"
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["role"] == "user"
        assert "temperature" in body
        assert "max_tokens" in body

    def test_retry_on_failure(self, monkeypatch):
        calls = [0]
        def fail_urlopen(req, timeout=None):
            calls[0] += 1
            raise Exception("network error")
        monkeypatch.setattr("urllib.request.urlopen", fail_urlopen)
        client = OpenAICompatibleClient(
            base_url="http://fake", api_key="key", model="m", max_retries=2
        )
        with pytest.raises(RuntimeError, match="failed after"):
            client.complete("sys", "user")
        assert calls[0] == 3  # 1 initial + 2 retries


class TestAnthropicCompatibleClient:
    def test_request_format_correct(self, monkeypatch):
        captured: list[dict] = []

        def fake_urlopen(req, timeout=None):
            captured.append({
                "headers": dict(req.headers),
                "body": json.loads(req.data.decode("utf-8")),
            })
            class FakeResp:
                def __enter__(self): return self
                def __exit__(self, *a): pass
                def read(self):
                    return json.dumps({"content": [{"text": '{"decision":"reject_merge","confidence":0.9,"reason_zh":"不同需求"}'}]}).encode()
            return FakeResp()

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        client = AnthropicCompatibleClient(base_url="http://fake", api_key="ant-key", model="claude-3-5")
        result = client.complete("sys prompt", "user prompt")
        assert len(captured) == 1
        headers = captured[0]["headers"]
        body = captured[0]["body"]
        # Anthropic uses x-api-key header (note: urllib capitalises first letter)
        assert any("api-key" in k.lower() or "x-api-key" in k.lower() for k in headers)
        assert body["model"] == "claude-3-5"
        assert body["messages"][0]["role"] == "user"
        assert "system" in body

    def test_anthropic_endpoint_is_messages(self, monkeypatch):
        urls_called = []

        def fake_urlopen(req, timeout=None):
            urls_called.append(req.full_url)
            class FakeResp:
                def __enter__(self): return self
                def __exit__(self, *a): pass
                def read(self): return json.dumps({"content": [{"text": "{}"}]}).encode()
            return FakeResp()

        monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
        client = AnthropicCompatibleClient(base_url="http://fake.api", api_key="k", model="m")
        try:
            client.complete("s", "u")
        except Exception:
            pass
        assert any("/messages" in url for url in urls_called)


class TestFakeLLMClient:
    def test_returns_predefined_responses(self):
        responses = ['{"decision":"confirm_merge","confidence":0.9,"reason_zh":"相同需求","evidence_alignment_zh":"一致","workflow_judgment_zh":"相同","suggested_group_title_zh":"需求组标题","suggested_group_summary_zh":"需求组摘要","conflict_flags":[]}']
        client = FakeLLMClient(responses=responses)
        result = client.complete("sys", "user")
        assert "confirm_merge" in result

    def test_falls_back_to_default_after_responses_exhausted(self):
        client = FakeLLMClient(responses=["first"])
        _ = client.complete("s", "u")
        result = client.complete("s", "u")
        data = json.loads(result)
        assert data["decision"] == "maybe_merge"

    def test_call_count_increments(self):
        client = FakeLLMClient()
        assert client.call_count == 0
        client.complete("s", "u")
        client.complete("s", "u")
        assert client.call_count == 2

    def test_no_network_calls(self, monkeypatch):
        called = []
        monkeypatch.setattr("urllib.request.urlopen", lambda *a, **kw: called.append(True))
        client = FakeLLMClient()
        client.complete("s", "u")
        assert len(called) == 0


class TestMakeLLMClient:
    def test_openai_compatible_default(self, monkeypatch):
        monkeypatch.setenv("DEMAND_RADAR_LLM_BASE_URL", "http://test")
        monkeypatch.setenv("DEMAND_RADAR_LLM_API_KEY", "key")
        client = make_llm_client("openai_compatible", {"llm": {"model": "gpt-4o"}})
        assert isinstance(client, OpenAICompatibleClient)

    def test_anthropic_compatible(self, monkeypatch):
        monkeypatch.setenv("DEMAND_RADAR_LLM_BASE_URL", "http://test")
        monkeypatch.setenv("DEMAND_RADAR_LLM_API_KEY", "ant-key")
        client = make_llm_client("anthropic_compatible", {"llm": {"model": "claude-3-5"}})
        assert isinstance(client, AnthropicCompatibleClient)

    def test_fake_provider(self):
        client = make_llm_client("fake", {"fake_responses": []})
        assert isinstance(client, FakeLLMClient)

    def test_env_model_override(self, monkeypatch):
        monkeypatch.setenv("DEMAND_RADAR_LLM_MODEL", "env-model")
        monkeypatch.setenv("DEMAND_RADAR_LLM_BASE_URL", "http://x")
        monkeypatch.setenv("DEMAND_RADAR_LLM_API_KEY", "k")
        client = make_llm_client("openai_compatible", {"llm": {"model": "config-model"}})
        assert isinstance(client, OpenAICompatibleClient)
        assert client.model == "env-model"
