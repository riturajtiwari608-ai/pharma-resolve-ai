import enum
import uuid
from typing import TYPE_CHECKING
from datetime import date, datetime

from app.models.complaint_document import ComplaintDocument
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import Mapped, mapped_column

if TYPE_CHECKING:
    from app.models.complaint_correction import ComplaintCorrection
    from app.models.complaint_document import ComplaintDocument

from app.core.database import Base


class ComplaintStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_TRIAGE = "pending_triage"
    READY_TO_COMMIT = "ready_to_commit"
    COMMITTED = "committed"
    UNDER_INVESTIGATION = "under_investigation"
    CLOSED = "closed"


class SeverityLevel(str, enum.Enum):
    CRITICAL = "critical"
    MAJOR = "major"
    MINOR = "minor"
    UNCLASSIFIED = "unclassified"


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    complaint_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
    )

    complaint_source: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    customer_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    product_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    product_strength_grade: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    batch_lot_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    affected_quantity: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    affected_quantity_unit: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    manufacturing_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    expiry_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
    )

    originating_site_block: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    impacted_non_product_material: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    complaint_category: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    structured_defect_summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    raw_complaint_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    suggested_severity: Mapped[SeverityLevel] = mapped_column(
        Enum(
            SeverityLevel,
            name="severity_level_enum",
        ),
        nullable=False,
        default=SeverityLevel.UNCLASSIFIED,
    )

    suggested_next_action: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    initial_risk_assessment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    ai_confidence_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    status: Mapped[ComplaintStatus] = mapped_column(
        Enum(
            ComplaintStatus,
            name="complaint_status_enum",
        ),
        nullable=False,
        default=ComplaintStatus.DRAFT,
        index=True,
    )

    is_ai_generated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )

    correction_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    documents: Mapped[list["ComplaintDocument"]] = relationship(
        "ComplaintDocument",
        back_populates="complaint",
        cascade="all, delete-orphan",
    )
    corrections: Mapped[list["ComplaintCorrection"]] = relationship(
        "ComplaintCorrection",
        back_populates="complaint",
        cascade="all, delete-orphan",
        order_by="ComplaintCorrection.created_at",
    )