from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CorrectionHistoryResponse(BaseModel):
    id: UUID
    complaint_id: UUID
    correction_number: int
    source: str
    user_message: str | None
    field_updates: dict[str, Any]
    previous_values: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CorrectionHistoryListResponse(BaseModel):
    total: int
    corrections: list[CorrectionHistoryResponse]


class ComplaintCommitResponse(BaseModel):
    success: bool
    complaint_id: UUID
    complaint_number: str
    status: str
    message: str
    validation_warnings: list[str] = Field(
        default_factory=list
    )