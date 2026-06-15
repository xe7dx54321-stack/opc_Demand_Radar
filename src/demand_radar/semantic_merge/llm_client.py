"""LLM client abstractions for Stage 2.9 semantic merge pilot.

Supports openai_compatible and anthropic_compatible providers.
A FakeLLMClient is provided for unit tests without network calls.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Protocol


class BaseLLMClient(Protocol):
    """Minimal interface all LLM clients must satisfy."""

    provider: str

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return the raw text response from the LLM."""
        ...


class OpenAICompatibleClient:
    """Calls any OpenAI-compatible /chat/completions endpoint."""

    provider = "openai_compatible"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 60,
        max_retries: int = 2,
        temperature: float = 0.0,
        max_tokens: int = 4000,
    ) -> None:
        # Normalise: strip trailing slash but keep the path as-is so that
        # both "https://api.openai.com/v1" and "https://api.openai.com/v1/"
        # work without accidentally producing /v1/v1/chat/completions.
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }
        ).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }
        return self._send(url, payload, headers)

    def _send(self, url: str, payload: bytes, headers: dict[str, str]) -> str:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        last_error: Exception | None = None
        for _ in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    return str(body["choices"][0]["message"]["content"])
            except Exception as exc:
                last_error = exc
        raise RuntimeError(
            f"OpenAI-compatible API failed after {self.max_retries + 1} attempts: {last_error}"
        )


class AnthropicCompatibleClient:
    """Calls an Anthropic-compatible /messages endpoint."""

    provider = "anthropic_compatible"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 60,
        max_retries: int = 2,
        temperature: float = 0.0,
        max_tokens: int = 4000,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        url = f"{self.base_url}/messages"
        payload = json.dumps(
            {
                "model": self.model,
                "max_tokens": self.max_tokens,
                "temperature": self.temperature,
                "system": system_prompt,
                "messages": [
                    {"role": "user", "content": user_prompt},
                ],
            }
        ).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        return self._send(url, payload, headers)

    def _send(self, url: str, payload: bytes, headers: dict[str, str]) -> str:
        req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
        last_error: Exception | None = None
        for _ in range(self.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    # Anthropic: content is a list of blocks
                    content = body.get("content", [])
                    if isinstance(content, list) and content:
                        return str(content[0].get("text", ""))
                    return str(body)
            except Exception as exc:
                last_error = exc
        raise RuntimeError(
            f"Anthropic-compatible API failed after {self.max_retries + 1} attempts: {last_error}"
        )


class FakeLLMClient:
    """Deterministic fake client for unit tests — never makes network calls."""

    provider = "fake"

    def __init__(self, responses: list[str] | None = None, default: str | None = None) -> None:
        self._responses = list(responses or [])
        self._call_count = 0
        self._default = default or json.dumps(
            {
                "decision": "maybe_merge",
                "confidence": 0.55,
                "reason_zh": "测试占位判断理由（中文）",
                "evidence_alignment_zh": "测试证据对齐说明",
                "workflow_judgment_zh": "测试工作流判断说明",
                "suggested_group_title_zh": "",
                "suggested_group_summary_zh": "",
                "conflict_flags": [],
            }
        )

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        idx = self._call_count
        self._call_count += 1
        if idx < len(self._responses):
            return self._responses[idx]
        return self._default

    @property
    def call_count(self) -> int:
        return self._call_count




class ResponsesCompatibleClient:
    """Calls an OpenAI Responses API endpoint (/v1/responses format).

    Used with providers like ailinkmax that expose the Responses API wire format
    rather than the Chat Completions format.
    """

    provider = "responses_compatible"

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int = 60,
        max_retries: int = 2,
        temperature: float = 0.0,
        max_tokens: int = 4000,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.temperature = temperature
        self.max_tokens = max_tokens

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Send a Responses API request with truncation-aware retry (Stage 2.9E).

        On truncated JSON output, retries with boosted max_output_tokens.
        """
        from demand_radar.semantic_merge.llm_output_parser import is_truncated_output
        combined = f"{system_prompt}\n\n{user_prompt}"
        url = f"{self.base_url}/responses"
        current_max_tokens = self.max_tokens
        last_error: Exception | None = None
        last_text: str = ""

        for attempt in range(self.max_retries + 1):
            payload = json.dumps(
                {
                    "model": self.model,
                    "input": combined,
                    "max_output_tokens": current_max_tokens,
                    "temperature": self.temperature,
                }
            ).encode("utf-8")
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                    output = body.get("output", [])
                    for item in output:
                        if item.get("type") == "message":
                            for block in item.get("content", []):
                                if block.get("type") == "output_text":
                                    last_text = str(block["text"])
                                    if not is_truncated_output(last_text):
                                        return last_text
                                    # Truncated: boost tokens and retry
                                    current_max_tokens = min(current_max_tokens * 2, 12000)
            except Exception as exc:
                last_error = exc

        # Return whatever we got (may be truncated; parser will attempt repair)
        if last_text:
            return last_text
        raise RuntimeError(
            f"Responses API failed after {self.max_retries + 1} attempts: {last_error}"
        )
def make_llm_client(provider: str, config: dict[str, Any]) -> BaseLLMClient:
    """Factory: create the appropriate LLM client from config.

    ``provider`` can be ``openai_compatible``, ``anthropic_compatible``, or ``fake``.
    For ``fake``, an optional list of ``fake_responses`` may be passed in config.
    """
    llm_conf = config.get("llm", config)
    base_url = os.environ.get(str(llm_conf.get("base_url_env", "DEMAND_RADAR_LLM_BASE_URL")), "")
    api_key = os.environ.get(str(llm_conf.get("api_key_env", "DEMAND_RADAR_LLM_API_KEY")), "")
    # Allow model override via env
    model = (
        os.environ.get("DEMAND_RADAR_LLM_MODEL", "")
        or str(llm_conf.get("model", ""))
    )
    timeout_seconds = int(llm_conf.get("timeout_seconds", 60))
    max_retries = int(llm_conf.get("max_retries", 2))
    temperature = float(llm_conf.get("temperature", 0.0))
    max_tokens = int(llm_conf.get("max_tokens", 4000))

    if provider == "fake":
        fake_responses = config.get("fake_responses", [])
        fake_default = config.get("fake_default", None)
        return FakeLLMClient(responses=fake_responses, default=fake_default)
    if provider == "anthropic_compatible":
        return AnthropicCompatibleClient(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    if provider == "responses_compatible":
        return ResponsesCompatibleClient(
            base_url=base_url,
            api_key=api_key,
            model=model,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
            temperature=temperature,
            max_tokens=max_tokens,
        )
    # Default: openai_compatible
    return OpenAICompatibleClient(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        temperature=temperature,
        max_tokens=max_tokens,
    )



