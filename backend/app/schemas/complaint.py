from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.complaint import ComplaintStatus, SeverityLevel


class ComplaintBase(BaseModel):
    complaint_source: str | None = Field(
        default=None,
        max_length=100,
    )

    customer_name: str | None = Field(
        default=None,
        max_length=255,
    )

    product_name: str | None = Field(
        default=None,
        max_length=255,
    )

    product_strength_grade: str | None = Field(
        default=None,
        max_length=100,
    )

    batch_lot_number: str | None = Field(
        default=None,
        max_length=100,
    )

    affected_quantity: float | None = Field(
        default=None,
        ge=0,
    )

    affected_quantity_unit: str | None = Field(
        default=None,
        max_length=50,
    )

    manufacturing_date: date | None = None
    expiry_date: date | None = None

    originating_site_block: str | None = Field(
        default=None,
        max_length=255,
    )

    impacted_non_product_material: str | None = Field(
        default=None,
        max_length=255,
    )

    complaint_category: str | None = Field(
        default=None,
        max_length=255,
    )

    structured_defect_summary: str | None = None
    raw_complaint_text: str | None = None

    suggested_severity: SeverityLevel = SeverityLevel.UNCLASSIFIED
    suggested_next_action: str | None = None
    initial_risk_assessment: str | None = None

    ai_confidence_score: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    is_ai_generated: bool = False

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
        mode="before",
    )
    @classmethod
    def clean_optional_strings(cls, value: str | None) -> str | None:
        if isinstance(value, str):
            cleaned_value = value.strip()
            return cleaned_value or None

        return value

    @field_validator("expiry_date")
    @classmethod
    def validate_expiry_date(
        cls,
        expiry_date: date | None,
        validation_info,
    ) -> date | None:
        manufacturing_date = validation_info.data.get("manufacturing_date")

        if (
            manufacturing_date is not None
            and expiry_date is not None
            and expiry_date < manufacturing_date
        ):
            raise ValueError(
                "Expiry date cannot be earlier than manufacturing date."
            )

        return expiry_date


class ComplaintCreate(ComplaintBase):
    status: ComplaintStatus = ComplaintStatus.DRAFT


class ComplaintUpdate(BaseModel):
    complaint_source: str | None = Field(
        default=None,
        max_length=100,
    )
    customer_name: str | None = Field(
        default=None,
        max_length=255,
    )
    product_name: str | None = Field(
        default=None,
        max_length=255,
    )
    product_strength_grade: str | None = Field(
        default=None,
        max_length=100,
    )
    batch_lot_number: str | None = Field(
        default=None,
        max_length=100,
    )
    affected_quantity: float | None = Field(
        default=None,
        ge=0,
    )
    affected_quantity_unit: str | None = Field(
        default=None,
        max_length=50,
    )

    manufacturing_date: date | None = None
    expiry_date: date | None = None

    originating_site_block: str | None = Field(
        default=None,
        max_length=255,
    )

    impacted_non_product_material: str | None = Field(
        default=None,
        max_length=255,
    )

    complaint_category: str | None = Field(
        default=None,
        max_length=255,
    )

    structured_defect_summary: str | None = None
    raw_complaint_text: str | None = None

    suggested_severity: SeverityLevel | None = None
    suggested_next_action: str | None = None
    initial_risk_assessment: str | None = None

    ai_confidence_score: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )

    status: ComplaintStatus | None = None
    is_ai_generated: bool | None = None
    correction_count: int | None = Field(
        default=None,
        ge=0,
    )


class ComplaintResponse(ComplaintBase):
    id: UUID
    complaint_number: str
    status: ComplaintStatus
    correction_count: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ComplaintListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    complaints: list[ComplaintResponse]


class ComplaintDeleteResponse(BaseModel):
    message: str
    complaint_number: str