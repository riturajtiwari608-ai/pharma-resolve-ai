from typing import Any, Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


class ComplaintCopilotRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=3,
        max_length=15000,
    )

    complaint_id: UUID | None = Field(
        default=None,
        description=(
            "Existing complaint ID. Required when correcting "
            "an already-created complaint."
        ),
    )

    thread_id: str | None = Field(
        default=None,
        max_length=100,
        description="Conversation identifier used by LangGraph.",
    )

    create_draft: bool = True

    @field_validator("message")
    @classmethod
    def clean_message(cls, value: str) -> str:
        cleaned = " ".join(value.split())

        if len(cleaned) < 3:
            raise ValueError("Message is too short.")

        return cleaned
    raw_intent = result.get("intent")

    intent_mapping = {
        "new": "new_complaint",
        "new_complaint": "new_complaint",
        "create_complaint": "new_complaint",
        "correction": "correction",
        "correct_complaint": "correction",
        "complaint_correction": "correction",
    }

    safe_intent = intent_mapping.get(
        raw_intent,
        "unknown",
    )


class ComplaintCopilotResponse(BaseModel):
    success: bool

    intent: Literal[
        "new_complaint",
        "correction",
        "unknown",
    ] = "unknown"

    thread_id: str

    complaint_id: str | UUID | None = None
    complaint_number: str | None = None

    processing_status: str = "unknown"
    assistant_message: str = "Request processed."

    complaint_data: dict[str, Any] | None = None

    field_updates: dict[str, Any] = Field(
        default_factory=dict
    )

    missing_fields: list[str] = Field(
        default_factory=list
    )

    warnings: list[str] = Field(
        default_factory=list
    )

    used_model: str | None = None
    fallback_used: bool = False

    model_config = ConfigDict(
        extra="ignore",
    )


class ComplaintCorrectionResult(BaseModel):
    field_updates: dict[str, Any] = Field(
        default_factory=dict
    )

    assistant_message: str = (
        "Complaint correction processed."
    )

    warnings: list[str] = Field(
        default_factory=list
    )

    confidence: float = Field(
        default=0,
        ge=0,
        le=1,
    )

    model_config = ConfigDict(
        extra="ignore",
    )