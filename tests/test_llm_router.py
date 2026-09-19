"""Unit tests for the provider-agnostic LLM router fallback chain."""

from __future__ import annotations

import importlib
import json
from unittest import mock

import pytest

from orchestrator import llm_router


@pytest.fixture(autouse=True)
def _reset_router_cache():
    llm_router._CLIENTS = None
    yield
    llm_router._CLIENTS = None


def _make_resp(text: str, finish_reason: str = "stop"):
    choice = mock.Mock()
    choice.message.content = text
    choice.finish_reason = finish_reason
    resp = mock.Mock()
    resp.choices = [choice]
    return resp


class _FakeClient:
    def __init__(self, responses, calls=None):
        self._responses = list(responses)
        self._calls = calls if calls is not None else []
        self.chat = mock.Mock()
        self.chat.completions.create = mock.Mock(side_effect=self._create)

    def _create(self, **kwargs):
        self._calls.append(kwargs["model"])
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_is_configured_false_without_keys(monkeypatch):
    for var in ("NVIDIA_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    assert llm_router.is_configured() is False


def test_chain_builds_in_priority_order(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "nv")
    monkeypatch.setenv("GOOGLE_API_KEY", "gg")
    monkeypatch.setenv("GROQ_API_KEY", "gq")
    clients = llm_router._build_clients()
    labels = [label for _, _, label in clients]
    assert labels[0].startswith("NVIDIA NIM (nemotron-3.5-lightning")
    assert labels[1].startswith("NVIDIA NIM (nemotron-3-ultra")
    assert labels[2] == "Gemini"
    assert labels[3] == "Groq"


def test_chat_json_parses_fenced_json():
    good = _make_resp('```json\n{"actions": [{"tool": "add_task"}], "reasoning": "r"}\n```')
    client = _FakeClient([good])
    with mock.patch.object(llm_router, "_get_clients", return_value=[(client, "m", "Test")]):
        result = llm_router.chat_json("sys", "user")
    assert result["actions"][0]["tool"] == "add_task"


def test_fallback_on_rate_limit_then_success():
    rl = __import__("openai").RateLimitError(
        "rate limited", response=mock.Mock(status_code=429), body=None
    )
    good = _make_resp('{"actions": [1], "reasoning": "ok"}')
    c1 = _FakeClient([rl])
    c2 = _FakeClient([good])
    with mock.patch.object(
        llm_router, "_get_clients", return_value=[(c1, "m1", "Primary"), (c2, "m2", "Backup")]
    ):
        result = llm_router.chat_json("sys", "user")
    assert result["reasoning"] == "ok"
    assert c1._calls == ["m1"]
    assert c2._calls == ["m2"]


def test_fallback_on_truncated_response():
    bad = _make_resp('{"actions": [', finish_reason="length")
    good = _make_resp('{"actions": [], "reasoning": "ok"}')
    c1 = _FakeClient([bad])
    c2 = _FakeClient([good])
    with mock.patch.object(
        llm_router, "_get_clients", return_value=[(c1, "m1", "Primary"), (c2, "m2", "Backup")]
    ):
        result = llm_router.chat_json("sys", "user")
    assert result["reasoning"] == "ok"


def test_all_providers_exhausted_raises_runtime_error():
    rl = __import__("openai").RateLimitError(
        "rate limited", response=mock.Mock(status_code=429), body=None
    )
    c1 = _FakeClient([rl])
    c2 = _FakeClient([json.JSONDecodeError("nope", "", 0)])
    with mock.patch.object(
        llm_router, "_get_clients", return_value=[(c1, "m1", "Primary"), (c2, "m2", "Backup")]
    ):
        with pytest.raises(RuntimeError, match="All LLM providers exhausted"):
            llm_router.chat_json("sys", "user")


def test_planner_uses_router_and_falls_back_gracefully():
    from orchestrator.planner import GeminiIntentPlanner

    planner = GeminiIntentPlanner()
    with mock.patch.object(llm_router, "is_configured", return_value=False):
        plan = planner.plan("add task buy milk")
    assert plan.actions and plan.actions[0]["tool"] == "add_task"

    with mock.patch.object(llm_router, "is_configured", return_value=True):
        with mock.patch.object(
            llm_router,
            "chat_json",
            side_effect=RuntimeError("All LLM providers exhausted"),
        ):
            plan = planner.plan("add task buy milk")
    assert plan.actions and plan.actions[0]["tool"] == "add_task"
