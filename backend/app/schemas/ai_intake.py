from datetime import date
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.complaint import ComplaintStatus, SeverityLevel


class ComplaintTextAnalysisRequest(BaseModel):
    complaint_text: str = Field(
        ...,
        min_length=20,
        max_length=15000,
        description="Raw customer complaint email or message.",
    )

    create_draft: bool = Field(
        default=False,
        description="Create a draft complaint in the database.",
    )

    @field_validator("complaint_text")
    @classmethod
    def clean_complaint_text(cls, value: str) -> str:
        cleaned = " ".join(value.split())

        if len(cleaned) < 20:
            raise ValueError(
                "Complaint text must contain at least 20 meaningful characters."
            )

        return cleaned


class ExtractedFieldEvidence(BaseModel):
    value: str | float | None = None
    confidence: float = Field(default=0, ge=0, le=1)
    source_text: str | None = None


class ComplaintExtractionData(BaseModel):
    complaint_source: str | None = None
    customer_name: str | None = None

    product_name: str | None = None
    product_strength_grade: str | None = None
    batch_lot_number: str | None = None

    affected_quantity: float | None = Field(default=None, ge=0)
    affected_quantity_unit: str | None = None

    manufacturing_date: date | None = None
    expiry_date: date | None = None

    originating_site_block: str | None = None
    impacted_non_product_material: str | None = None

    complaint_category: str | None = None
    structured_defect_summary: str | None = None

    suggested_severity: SeverityLevel = SeverityLevel.UNCLASSIFIED
    suggested_next_action: str | None = None
    initial_risk_assessment: str | None = None

    overall_confidence: float = Field(default=0, ge=0, le=1)

    @field_validator(
        "complaint_source",
        "customer_name",
        "product_name",
        "product_strength_grade",
        "batch_lot_number",
        "affected_quantity_unit",
        "originating_site_block",
        "impacted_non_product_material",
        "complaint_category",
        "structured_defect_summary",
        "suggested_next_action",
        "initial_risk_assessment",
        mode="before",
    )
    @classmethod
    def clean_optional_text(cls, value):
        if not isinstance(value, str):
            return value

        cleaned = value.strip()

        if cleaned.lower() in {
            "",
            "null",
            "none",
            "not available",
            "not provided",
            "unknown",
        }:
            return None

        return cleaned

    @model_validator(mode="after")
    def validate_date_order(self):
        if (
            self.manufacturing_date
            and self.expiry_date
            and self.expiry_date < self.manufacturing_date
        ):
            self.expiry_date = None

        return self


class ComplaintFieldEvidence(BaseModel):
    complaint_source: ExtractedFieldEvidence | None = None
    customer_name: ExtractedFieldEvidence | None = None
    product_name: ExtractedFieldEvidence | None = None
    product_strength_grade: ExtractedFieldEvidence | None = None
    batch_lot_number: ExtractedFieldEvidence | None = None
    affected_quantity: ExtractedFieldEvidence | None = None
    manufacturing_date: ExtractedFieldEvidence | None = None
    expiry_date: ExtractedFieldEvidence | None = None


class ComplaintAnalysisResult(BaseModel):
    extraction: ComplaintExtractionData

    missing_fields: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    field_evidence: ComplaintFieldEvidence = Field(
        default_factory=ComplaintFieldEvidence
    )

    processing_status: Literal[
        "needs_information",
        "ready_to_commit",
    ]

    assistant_message: str


class AIUsageInfo(BaseModel):
    requested_model: str
    used_model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    fallback_used: bool = False


class ComplaintTextAnalysisResponse(BaseModel):
    success: bool = True
    analysis: ComplaintAnalysisResult

    draft_complaint_id: str | None = None
    complaint_number: str | None = None
    complaint_status: ComplaintStatus | None = None

    usage: AIUsageInfo