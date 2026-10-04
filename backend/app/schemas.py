"""Request/response models. Mirror src/api/types.ts in the mobile app — field names are camelCase on the wire."""

from typing import Annotated, Any, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["low", "med", "high"]


class LatLng(BaseModel):
    lat: float
    lng: float


FieldValue = Union[str, float, int, LatLng, None]


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(max_length=4000)


class ChatRequest(BaseModel):
    packId: str = Field(max_length=64)
    locale: str = Field(default="en", max_length=16)
    systemPrompt: str = Field(default="", max_length=8000)
    messages: list[ChatMessage] = Field(min_length=1, max_length=24)
    context: Optional[dict[str, Any]] = None


class ChatResponse(BaseModel):
    reply: str
    sources: Optional[list[str]] = None


class AnalyzeRequest(BaseModel):
    packId: str = Field(max_length=64)
    locale: str = Field(default="en", max_length=16)
    fields: dict[str, FieldValue] = Field(default_factory=dict)
    # JPEG base64 without the data: prefix. The app sends quality 0.3 photos (~50-300 KB).
    imageBase64: Optional[str] = Field(default=None, max_length=4_000_000)


class Assessment(BaseModel):
    """Same shape as the app's `Assessment` type. Also used as the structured-output schema for Claude."""

    summary: str
    riskLevel: Optional[RiskLevel] = None
    actions: list[str]


# Deliberately isolated initial contract: replace these types when the task is known.
Feature = Annotated[float, Field(strict=True, allow_inf_nan=False)]
PredictionValue = Union[Annotated[str, Field(strict=True)], Feature]


class PredictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    features: list[Feature] = Field(min_length=1)


class PredictResponse(BaseModel):
    prediction: PredictionValue
    modelVersion: str = Field(min_length=1, pattern=r"\S")


# ---- /extract: mirrors `Extraction` in src/intake/types.ts ----
Confidence = Literal["high", "low"]
AnswerText = Annotated[str, Field(max_length=2000)]


class IntakeAnswers(BaseModel):
    who: AnswerText = ""
    complaint: AnswerText = ""
    duration: AnswerText = ""
    danger: AnswerText = ""


class ExtractRequest(BaseModel):
    locale: str = Field(default="sw", max_length=16)
    answers: IntakeAnswers


class ExtractionField(BaseModel):
    value: Any
    confidence: Confidence
    evidence: Optional[str] = None


class Extraction(BaseModel):
    patientGroup: ExtractionField
    symptoms: ExtractionField
    durationDays: ExtractionField
    dangerSigns: ExtractionField
    unmapped: list[str]
    source: Literal["rules", "model"]
