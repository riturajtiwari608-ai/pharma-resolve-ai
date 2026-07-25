from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PDFExtractionResult(BaseModel):
    text: str
    page_count: int
    character_count: int

    extraction_status: str
    warning: str | None = None

    page_text_lengths: list[int] = Field(
        default_factory=list
    )


class DocumentMetadataResponse(BaseModel):
    id: UUID

    complaint_id: UUID | None

    original_filename: str
    stored_filename: str
    content_type: str

    file_size_bytes: int
    page_count: int | None

    extraction_status: str
    extraction_warning: str | None

    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PDFComplaintUploadResponse(BaseModel):
    success: bool

    document: DocumentMetadataResponse

    text_preview: str
    extracted_character_count: int

    analysis: dict[str, Any] | None = None

    complaint_id: str | None = None
    complaint_number: str | None = None
    complaint_status: str | None = None

    assistant_message: str
    warnings: list[str] = Field(default_factory=list)

    used_model: str | None = None
    fallback_used: bool = False