"""NUSRangers backend: the cloud half of the app's hybrid AI. Contract: docs/api.md."""

import json
import logging
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from fastapi import Body, Depends, FastAPI, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from .care import CareRouter, CareUnavailableError, load_care_router
from .extract import ExtractorUnavailableError, IntakeExtractor, load_extractor
from .llm import LLMError, make_provider
from .ml import ModelUnavailableError, PredictionError, PredictionInputError, Predictor, load_model_service
from .prompts import PACK_PROMPTS
from .schemas import (
    AnalyzeRequest,
    AssessRequest,
    AssessResponse,
    Assessment,
    ChatRequest,
    ChatResponse,
    ExtractRequest,
    Extraction,
    PredictRequest,
    PredictResponse,
)

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
    app.state.extractor = None
    app.state.extractor_error = "Extraction model is unavailable"
    try:
        app.state.extractor = load_extractor(os.getenv("EXTRACT_MODEL_PATH"), os.getenv("EXTRACT_CODE_PATH"))
    except ExtractorUnavailableError as exc:
        app.state.extractor_error = str(exc)
        log.warning("Extract endpoint unavailable: %s", exc)
    app.state.care_router = None
    app.state.care_error = "Care routing is unavailable"
    try:
        app.state.care_router = load_care_router(os.getenv("CARE_CODE_PATH"), os.getenv("CARE_DATA_PATH"))
    except CareUnavailableError as exc:
        app.state.care_error = str(exc)
        log.warning("Assess endpoint unavailable: %s", exc)
    try:
        yield
    finally:
        app.state.model_service = None
        app.state.extractor = None
        app.state.care_router = None


app = FastAPI(title="NUSRangers backend", version="0.1.0", lifespan=lifespan)
# The native app doesn't need CORS; this is for the Expo web build and browser testing.
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

provider = make_provider()
DEFAULT_PACK = os.getenv("DEFAULT_PACK", "health")


def _raise(e: LLMError):
    # 503 = try again later, 502 = upstream rejected the request. Either way the app falls back offline.
    raise HTTPException(status_code=503 if e.retryable else 502, detail=str(e))


GUIDANCE_PATH = Path(os.getenv("GUIDANCE_PATH") or Path(__file__).resolve().parents[2] / "src/intake/guidanceRegistry.json")


@app.get("/guidance")
def guidance():
    """The current guidance registry. Phones download it when its version is newer than their copy."""
    try:
        return json.loads(GUIDANCE_PATH.read_text())
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Guidance registry is unavailable") from exc


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


# Store-and-forward target for confirmed intake records. In-memory for the hackathon; map to DHIS2
# (tracked entity + event) for a real deployment. Never log the record contents: it is patient data.
RECORDS: dict[str, dict[str, Any]] = {}


@app.post("/records")
async def save_record(record: dict[str, Any] = Body(...)):
    rec_id = str(record.get("id", ""))
    if not rec_id:
        raise HTTPException(status_code=422, detail="record.id is required")
    RECORDS[rec_id] = record
    log.info("Stored intake record %s (%d total)", rec_id, len(RECORDS))
    return {"ok": True}


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


def get_extractor(request: Request) -> IntakeExtractor:
    extractor = getattr(request.app.state, "extractor", None)
    if extractor is None:
        # The app falls back to its on-phone rules on any non-200.
        detail = getattr(request.app.state, "extractor_error", "Extraction model is unavailable")
        raise HTTPException(status_code=503, detail=detail)
    return extractor


# Null values are sent explicitly ("value": null): the app tells "not found" apart from a missing field.
@app.post("/extract", response_model=Extraction)
def extract(req: ExtractRequest, extractor: IntakeExtractor = Depends(get_extractor)):
    # Never log the answers: they are patient data.
    try:
        return extractor.extract(req)
    except Exception as exc:
        log.exception("Extraction failed")
        raise HTTPException(status_code=500, detail="Extraction failed") from exc


def get_care_router(request: Request) -> CareRouter:
    router = getattr(request.app.state, "care_router", None)
    if router is None:
        # The app keeps its on-phone clinic list on any non-200.
        detail = getattr(request.app.state, "care_error", "Care routing is unavailable")
        raise HTTPException(status_code=503, detail=detail)
    return router


@app.post("/assess", response_model=AssessResponse)
def assess(req: AssessRequest, router: CareRouter = Depends(get_care_router)):
    # Never log the note: it is patient data.
    try:
        return router.assess(req)
    except Exception as exc:
        log.exception("Care assessment failed")
        raise HTTPException(status_code=500, detail="Care assessment failed") from exc
