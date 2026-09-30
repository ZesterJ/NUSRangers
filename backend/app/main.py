"""NUSRangers backend: the cloud half of the app's hybrid AI. Contract: docs/api.md."""

import logging
import os
import re
from xml.sax.saxutils import escape

from fastapi import FastAPI, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .llm import LLMError, make_provider
from .prompts import PACK_PROMPTS
from .schemas import AnalyzeRequest, Assessment, ChatRequest, ChatResponse

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("api")

app = FastAPI(title="NUSRangers backend", version="0.1.0")
# The native app doesn't need CORS; this is for the Expo web build and browser testing.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

provider = make_provider()
DEFAULT_PACK = os.getenv("DEFAULT_PACK", "agri")


def _raise(e: LLMError):
    # 503 = try again later, 502 = upstream rejected the request. Either way the app falls back offline.
    raise HTTPException(status_code=503 if e.retryable else 502, detail=str(e))


@app.get("/health")
async def health():
    return {"ok": True, "provider": provider.name}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        return ChatResponse(reply=await provider.chat(req))
    except LLMError as e:
        _raise(e)


@app.post("/analyze", response_model=Assessment)
async def analyze(req: AnalyzeRequest):
    try:
        return await provider.analyze(req)
    except LLMError as e:
        _raise(e)


SMS_PREFIX = re.compile(r"^\s*([A-Za-z]+)\s*:\s*(.*)$", re.S)


def parse_sms(body: str) -> tuple[str, str]:
    """The app composes 'AGRI: question'. Plain texts from basic phones go to DEFAULT_PACK."""
    m = SMS_PREFIX.match(body)
    if m and m.group(1).lower() in PACK_PROMPTS:
        return m.group(1).lower(), m.group(2).strip()
    return DEFAULT_PACK, body.strip()


@app.post("/sms/webhook")
async def sms_webhook(Body: str = Form(""), From: str = Form("")):
    """Twilio inbound SMS webhook (form-encoded). Replies with TwiML."""
    pack_id, text = parse_sms(Body)
    log.info("SMS from %s… pack=%s", From[:6], pack_id)
    if not text:
        reply = "Send your question as text, e.g. AGRI: when to plant maize?"
    else:
        try:
            reply = await provider.sms(pack_id, text)
        except LLMError:
            reply = "Sorry, the service is busy. Please try again in a few minutes."
    twiml = f'<?xml version="1.0" encoding="UTF-8"?><Response><Message>{escape(reply)}</Message></Response>'
    return Response(content=twiml, media_type="application/xml")
