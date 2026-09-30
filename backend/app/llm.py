"""
LLM providers.

LLM_PROVIDER=anthropic  Claude via the Anthropic SDK (needs ANTHROPIC_API_KEY)
LLM_PROVIDER=echo       No model and no key: deterministic canned replies for local dev, CI and smoke tests
"""

import json
import logging
import os
from typing import Protocol

import anthropic

from .prompts import ANALYZE_RULES, MOBILE_RULES, SMS_RULES, pack_prompt
from .schemas import AnalyzeRequest, Assessment, ChatMessage, ChatRequest

log = logging.getLogger("llm")

REFUSAL_REPLY = "Sorry, I can't help with that. Please contact a local expert."


class LLMError(Exception):
    """Upstream model failure. The API returns 502/503 and the app falls back to on-phone answers."""

    def __init__(self, message: str, retryable: bool):
        super().__init__(message)
        self.retryable = retryable


class Provider(Protocol):
    name: str

    async def chat(self, req: ChatRequest) -> str: ...
    async def analyze(self, req: AnalyzeRequest) -> Assessment: ...
    async def sms(self, pack_id: str, text: str) -> str: ...


def to_api_messages(messages: list[ChatMessage]) -> list[dict]:
    """
    Claude needs the conversation to start with a user turn and alternate roles.
    The app sends a sliding window of history, which may start mid-conversation,
    so drop leading assistant turns and merge any consecutive same-role turns.
    """
    out: list[dict] = []
    for m in messages:
        if m.role == "system" or not m.content.strip():
            continue
        if not out and m.role == "assistant":
            continue
        if out and out[-1]["role"] == m.role:
            out[-1]["content"] += "\n\n" + m.content
        else:
            out.append({"role": m.role, "content": m.content})
    return out


class EchoProvider:
    name = "echo"

    async def chat(self, req: ChatRequest) -> str:
        last = next((m.content for m in reversed(req.messages) if m.role == "user"), "")
        return f"[echo:{req.packId}/{req.locale}] {last}"

    async def analyze(self, req: AnalyzeRequest) -> Assessment:
        photo = " with photo" if req.imageBase64 else ""
        return Assessment(
            summary=f"[echo] Report received{photo}: {json.dumps(req.fields, default=str)}",
            riskLevel="low",
            actions=["Replace LLM_PROVIDER=echo with anthropic for real assessments"],
        )

    async def sms(self, pack_id: str, text: str) -> str:
        return f"[echo:{pack_id}] {text}"[:160]


# Models that accept the server-side refusal fallback (`fallbacks: "default"`).
FALLBACK_MODELS = {"claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5"}


class AnthropicProvider:
    name = "anthropic"

    def __init__(self) -> None:
        self.client = anthropic.AsyncAnthropic(
            timeout=float(os.getenv("LLM_TIMEOUT_SECONDS", "25")),
            max_retries=1,  # the phone waits on us; keep total latency bounded
        )
        self.model = os.getenv("ANTHROPIC_MODEL", "claude-opus-5-5")
        # Low effort keeps replies fast for a chat UI on slow networks. Raise for harder analysis.
        self.effort = os.getenv("ANTHROPIC_EFFORT", "low")
        self.use_fallbacks = self.model in FALLBACK_MODELS and os.getenv("ANTHROPIC_FALLBACKS", "on") == "on"

    def _common(self, max_tokens: int) -> dict:
        kwargs: dict = {"model": self.model, "max_tokens": max_tokens}
        if not self.model.startswith("claude-haiku"):  # Haiku 4.5 rejects the effort parameter
            kwargs["output_config"] = {"effort": self.effort}
        if self.use_fallbacks:
            # If a safety classifier declines, the API retries on Anthropic's recommended fallback model.
            kwargs["betas"] = ["server-side-fallback-2026-07-01"]
            kwargs["fallbacks"] = "default"
        return kwargs

    async def _text(self, system: str, messages: list[dict], max_tokens: int) -> str:
        try:
            response = await self.client.beta.messages.create(
                system=system, messages=messages, **self._common(max_tokens)
            )
        except anthropic.RateLimitError as e:
            raise LLMError("Rate limited by the model provider", retryable=True) from e
        except anthropic.APIStatusError as e:
            log.error("Anthropic API error %s: %s", e.status_code, e.message)
            raise LLMError(f"Model provider error {e.status_code}", retryable=e.status_code >= 500) from e
        except anthropic.APIConnectionError as e:
            raise LLMError("Could not reach the model provider", retryable=True) from e

        if response.stop_reason == "refusal":
            return REFUSAL_REPLY
        text = "".join(b.text for b in response.content if b.type == "text").strip()
        if not text:
            raise LLMError(f"Empty reply (stop_reason={response.stop_reason})", retryable=True)
        return text

    async def chat(self, req: ChatRequest) -> str:
        persona = req.systemPrompt.strip() or pack_prompt(req.packId)
        system = f"{persona}\n\n{MOBILE_RULES.format(locale=req.locale)}"
        messages = to_api_messages(req.messages)
        if not messages:
            raise LLMError("No user message to answer", retryable=False)
        return await self._text(system, messages, max_tokens=2048)

    async def analyze(self, req: AnalyzeRequest) -> Assessment:
        system = f"{pack_prompt(req.packId)}\n\n{ANALYZE_RULES.format(locale=req.locale)}"
        content: list[dict] = []
        if req.imageBase64:
            content.append(
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": req.imageBase64}}
            )
        content.append({"type": "text", "text": "Report fields:\n" + json.dumps(req.fields, default=str, indent=1)})

        try:
            response = await self.client.beta.messages.parse(
                system=system,
                messages=[{"role": "user", "content": content}],
                output_format=Assessment,
                **self._common(max_tokens=4096),
            )
        except anthropic.RateLimitError as e:
            raise LLMError("Rate limited by the model provider", retryable=True) from e
        except anthropic.APIStatusError as e:
            log.error("Anthropic API error %s: %s", e.status_code, e.message)
            raise LLMError(f"Model provider error {e.status_code}", retryable=e.status_code >= 500) from e
        except anthropic.APIConnectionError as e:
            raise LLMError("Could not reach the model provider", retryable=True) from e

        if response.stop_reason == "refusal" or response.parsed_output is None:
            return Assessment(summary=REFUSAL_REPLY, riskLevel=None, actions=["Contact a local expert"])
        return response.parsed_output

    async def sms(self, pack_id: str, text: str) -> str:
        system = f"{pack_prompt(pack_id)}\n\n{SMS_RULES}"
        reply = await self._text(system, [{"role": "user", "content": text}], max_tokens=1024)
        return reply[:160]


def make_provider() -> Provider:
    name = os.getenv("LLM_PROVIDER", "anthropic").lower()
    if name == "echo":
        return EchoProvider()
    if name == "anthropic":
        return AnthropicProvider()
    raise ValueError(f"Unknown LLM_PROVIDER={name!r} (expected 'anthropic' or 'echo')")
