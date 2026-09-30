"""AnthropicProvider request building and error handling, with a fake client (no network)."""

import asyncio
from types import SimpleNamespace

import anthropic
import httpx
import pytest

from app.llm import REFUSAL_REPLY, AnthropicProvider, LLMError, to_api_messages
from app.schemas import AnalyzeRequest, Assessment, ChatMessage, ChatRequest


class FakeMessages:
    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error:
            raise self.error
        return self.response

    parse = create


def provider_with(monkeypatch, fake, model="claude-opus-5-5"):
    monkeypatch.setenv("ANTHROPIC_MODEL", model)
    p = AnthropicProvider()
    p.client = SimpleNamespace(beta=SimpleNamespace(messages=fake))
    return p


def text_response(text, stop_reason="end_turn"):
    return SimpleNamespace(stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)])


def chat_req(*msgs):
    return ChatRequest(packId="agri", locale="sw", systemPrompt="You are ShambaMate", messages=list(msgs))


def test_chat_request_uses_fallbacks_effort_and_locale(monkeypatch):
    fake = FakeMessages(text_response("Panda mwezi Machi."))
    p = provider_with(monkeypatch, fake)
    reply = asyncio.run(p.chat(chat_req(ChatMessage(role="user", content="Nipande lini?"))))
    assert reply == "Panda mwezi Machi."
    call = fake.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default"
    assert call["betas"] == ["server-side-fallback-2026-07-01"]
    assert call["output_config"] == {"effort": "low"}
    assert call["system"].startswith("You are ShambaMate")
    assert "'sw'" in call["system"]


def test_haiku_skips_effort_and_fallbacks(monkeypatch):
    fake = FakeMessages(text_response("ok"))
    p = provider_with(monkeypatch, fake, model="claude-haiku-4-5")
    asyncio.run(p.chat(chat_req(ChatMessage(role="user", content="hi"))))
    call = fake.calls[0]
    assert "output_config" not in call and "fallbacks" not in call and "betas" not in call


def test_refusal_returns_safe_reply(monkeypatch):
    fake = FakeMessages(SimpleNamespace(stop_reason="refusal", content=[]))
    p = provider_with(monkeypatch, fake)
    assert asyncio.run(p.chat(chat_req(ChatMessage(role="user", content="x")))) == REFUSAL_REPLY


def test_rate_limit_maps_to_retryable_error(monkeypatch):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    err = anthropic.RateLimitError("slow down", response=httpx.Response(429, request=request), body=None)
    p = provider_with(monkeypatch, FakeMessages(error=err))
    with pytest.raises(LLMError) as exc:
        asyncio.run(p.chat(chat_req(ChatMessage(role="user", content="x"))))
    assert exc.value.retryable


def test_bad_request_maps_to_non_retryable_error(monkeypatch):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    err = anthropic.BadRequestError("bad", response=httpx.Response(400, request=request), body=None)
    p = provider_with(monkeypatch, FakeMessages(error=err))
    with pytest.raises(LLMError) as exc:
        asyncio.run(p.chat(chat_req(ChatMessage(role="user", content="x"))))
    assert not exc.value.retryable


def test_analyze_sends_image_and_parses(monkeypatch):
    expected = Assessment(summary="Fall armyworm likely.", riskLevel="med", actions=["Scout 20 plants"])
    fake = FakeMessages(SimpleNamespace(stop_reason="end_turn", parsed_output=expected))
    p = provider_with(monkeypatch, fake)
    req = AnalyzeRequest(packId="agri", locale="en", fields={"crop": "maize"}, imageBase64="aGVsbG8=")
    assert asyncio.run(p.analyze(req)) == expected
    call = fake.calls[0]
    assert call["output_format"] is Assessment
    blocks = call["messages"][0]["content"]
    assert blocks[0]["type"] == "image" and blocks[0]["source"]["media_type"] == "image/jpeg"
    assert "maize" in blocks[1]["text"]


def test_to_api_messages_starts_with_user_and_alternates():
    msgs = [
        ChatMessage(role="assistant", content="greeting"),
        ChatMessage(role="user", content="a"),
        ChatMessage(role="user", content="b"),
        ChatMessage(role="assistant", content="c"),
        ChatMessage(role="system", content="ignored"),
        ChatMessage(role="user", content="d"),
    ]
    assert to_api_messages(msgs) == [
        {"role": "user", "content": "a\n\nb"},
        {"role": "assistant", "content": "c"},
        {"role": "user", "content": "d"},
    ]
