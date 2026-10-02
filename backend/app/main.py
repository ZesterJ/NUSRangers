"""NUSRangers backend: the cloud half of the app's hybrid AI. Contract: docs/api.md."""

import logging
import os
import re
from contextlib import asynccontextmanager
from xml.sax.saxutils import escape

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .llm import LLMError, make_provider
from .ml import ModelUnavailableError, PredictionError, PredictionInputError, Predictor, load_model_service
from .prompts import PACK_PROMPTS
from .schemas import AnalyzeRequest, Assessment, ChatRequest, ChatResponse, PredictRequest, PredictResponse

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.model_service = None
    app.state.model_error = "ML model is unavailable"
    try:
        app.state.model_service = load_model_service(os.getenv("ML_MODEL_PATH"))
    except ModelUnavailableError as exc:
        app.state.model_error = str(exc)
        log.warning("Prediction endpoint unavailable: %s", exc)
    try:
        yield
    finally:
        app.state.model_service = None


app = FastAPI(title="NUSRangers backend", version="0.1.0", lifespan=lifespan)
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


def get_model_service(request: Request) -> Predictor:
    service = getattr(request.app.state, "model_service", None)
    if service is None:
        raise HTTPException(status_code=503, detail=getattr(request.app.state, "model_error", "ML model is unavailable"))
    return service


@app.post("/predict", response_model=PredictResponse)
def predict(req: PredictRequest, service: Predictor = Depends(get_model_service)):
    # FastAPI runs synchronous routes in its thread pool.
    try:
        return service.predict(req)
    except ModelUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except PredictionInputError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except PredictionError as exc:
        log.exception("Local model inference failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc
