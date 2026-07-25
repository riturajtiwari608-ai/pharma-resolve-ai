import enum
from datetime import datetime
from uuid import UUID
import typing


from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.schemas.ai_intake import ComplaintAnalysisResult
from app.models.complaint import ComplaintStatus
from app.models.complaint import Complaint
from app.schemas.complaint import ComplaintCreate, ComplaintUpdate
from app.models.complaint_correction import ComplaintCorrection
from datetime import date
from typing import Any

from app.models.complaint import (
    Complaint,
    ComplaintStatus,
    SeverityLevel,
)


def generate_complaint_number(db: Session) -> str:
    """
    Generate a complaint number such as:
    CMP-2026-0001
    """

    current_year = datetime.utcnow().year

    count_statement = select(func.count(Complaint.id)).where(
        Complaint.complaint_number.like(f"CMP-{current_year}-%")
    )

    current_count = db.scalar(count_statement) or 0
    next_number = current_count + 1

    return f"CMP-{current_year}-{next_number:04d}"


def create_complaint(
    db: Session,
    complaint_data: ComplaintCreate,
) -> Complaint:
    complaint_number = generate_complaint_number(db)

    complaint = Complaint(
        complaint_number=complaint_number,
        **complaint_data.model_dump(),
    )

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return complaint


def get_complaint_by_id(
    db: Session,
    complaint_id: UUID,
) -> Complaint:
    complaint = db.get(Complaint, complaint_id)

    if complaint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found.",
        )

    return complaint


def get_complaint_by_number(
    db: Session,
    complaint_number: str,
) -> Complaint:
    statement = select(Complaint).where(Complaint.complaint_number == complaint_number)

    complaint = db.scalar(statement)

    if complaint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Complaint not found.",
        )

    return complaint


def get_complaints(
    db: Session,
    page: int,
    page_size: int,
) -> tuple[list[Complaint], int]:
    offset = (page - 1) * page_size

    count_statement = select(func.count(Complaint.id))
    total = db.scalar(count_statement) or 0

    statement = (
        select(Complaint)
        .order_by(Complaint.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )

    complaints = list(db.scalars(statement).all())

    return complaints, total


def update_complaint(
    db: Session,
    complaint_id: UUID,
    complaint_data: ComplaintUpdate,
) -> Complaint:
    complaint = get_complaint_by_id(db, complaint_id)

    update_data = complaint_data.model_dump(
        exclude_unset=True,
    )

    for field_name, field_value in update_data.items():
        setattr(complaint, field_name, field_value)

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    return complaint


def delete_complaint(
    db: Session,
    complaint_id: UUID,
) -> Complaint:
    complaint = get_complaint_by_id(db, complaint_id)

    db.delete(complaint)
    db.commit()

    return complaint


def create_ai_extracted_draft(
    db: Session,
    raw_complaint_text: str,
    analysis: ComplaintAnalysisResult,
) -> Complaint:
    """
    Save AI-extracted complaint data as a human-reviewable draft.

    The AI never commits directly to the QMS ledger.
    """

    extracted = analysis.extraction

    complaint_data = ComplaintCreate(
        complaint_source=extracted.complaint_source,
        customer_name=extracted.customer_name,
        product_name=extracted.product_name,
        product_strength_grade=extracted.product_strength_grade,
        batch_lot_number=extracted.batch_lot_number,
        affected_quantity=extracted.affected_quantity,
        affected_quantity_unit=extracted.affected_quantity_unit,
        manufacturing_date=extracted.manufacturing_date,
        expiry_date=extracted.expiry_date,
        originating_site_block=extracted.originating_site_block,
        impacted_non_product_material=(extracted.impacted_non_product_material),
        complaint_category=extracted.complaint_category,
        structured_defect_summary=(extracted.structured_defect_summary),
        raw_complaint_text=raw_complaint_text,
        suggested_severity=extracted.suggested_severity,
        suggested_next_action=extracted.suggested_next_action,
        initial_risk_assessment=(extracted.initial_risk_assessment),
        ai_confidence_score=extracted.overall_confidence,
        is_ai_generated=True,
        status=(
            ComplaintStatus.READY_TO_COMMIT
            if analysis.processing_status == "ready_to_commit"
            else ComplaintStatus.PENDING_TRIAGE
        ),
    )

    return create_complaint(
        db=db,
        complaint_data=complaint_data,
    )


def complaint_to_dict(
    complaint: Complaint,
) -> dict:
    """
    Convert SQLAlchemy complaint object into serializable graph state.
    """

    return {
        "id": str(complaint.id),
        "complaint_number": complaint.complaint_number,
        "complaint_source": complaint.complaint_source,
        "customer_name": complaint.customer_name,
        "product_name": complaint.product_name,
        "product_strength_grade": (complaint.product_strength_grade),
        "batch_lot_number": complaint.batch_lot_number,
        "affected_quantity": complaint.affected_quantity,
        "affected_quantity_unit": (complaint.affected_quantity_unit),
        "manufacturing_date": (
            complaint.manufacturing_date.isoformat()
            if complaint.manufacturing_date
            else None
        ),
        "expiry_date": (
            complaint.expiry_date.isoformat() if complaint.expiry_date else None
        ),
        "originating_site_block": (complaint.originating_site_block),
        "impacted_non_product_material": (complaint.impacted_non_product_material),
        "complaint_category": complaint.complaint_category,
        "structured_defect_summary": (complaint.structured_defect_summary),
        "suggested_severity": (
            complaint.suggested_severity.value if complaint.suggested_severity else None
        ),
        "suggested_next_action": (complaint.suggested_next_action),
        "initial_risk_assessment": (complaint.initial_risk_assessment),
        "ai_confidence_score": (complaint.ai_confidence_score),
        "status": complaint.status.value,
        "correction_count": complaint.correction_count,
    }


def apply_complaint_corrections(
    db: Session,
    complaint: Complaint,
    field_updates: dict,
    user_message: str | None = None,
    source: str = "copilot",
) -> Complaint:
    """
    Apply safe updates and record the change history.
    """

    if complaint.status == ComplaintStatus.COMMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Committed complaints cannot be modified. "
                "Create a formal amendment instead."
            ),
        )

    date_fields = {
        "manufacturing_date",
        "expiry_date",
    }

    previous_values: dict[str, Any] = {}
    applied_updates: dict[str, Any] = {}

    for field_name, field_value in field_updates.items():
        if not hasattr(complaint, field_name):
            continue

        previous_value = getattr(
            complaint,
            field_name,
        )

        if isinstance(previous_value, enum.Enum):
            previous_value = previous_value.value

        if isinstance(previous_value, date):
            previous_value = previous_value.isoformat()

        if field_name in date_fields and isinstance(field_value, str):
            field_value = date.fromisoformat(field_value)

        if field_name == "suggested_severity" and isinstance(field_value, str):
            field_value = SeverityLevel(field_value)

        previous_values[field_name] = previous_value

        setattr(
            complaint,
            field_name,
            field_value,
        )

        serialized_value = field_value

        if isinstance(serialized_value, enum.Enum):
            serialized_value = serialized_value.value

        if isinstance(serialized_value, date):
            serialized_value = serialized_value.isoformat()

        applied_updates[field_name] = serialized_value

    if not applied_updates:
        return complaint

    complaint.correction_count += 1
    complaint.status = recalculate_complaint_status(complaint)

    db.add(complaint)
    db.commit()
    db.refresh(complaint)

    create_correction_history(
        db=db,
        complaint=complaint,
        field_updates=applied_updates,
        previous_values=previous_values,
        source=source,
        user_message=user_message,
    )

    return complaint


def get_missing_commit_fields(
    complaint: Complaint,
) -> list[str]:
    """
    Return human-readable required fields that are still missing.
    """

    missing_fields: list[str] = []

    for field_name, field_label in REQUIRED_COMMIT_FIELDS.items():
        value = getattr(complaint, field_name, None)

        if value is None:
            missing_fields.append(field_label)
            continue

        if isinstance(value, str) and not value.strip():
            missing_fields.append(field_label)

    if complaint.suggested_severity == SeverityLevel.UNCLASSIFIED:
        missing_fields.append("Suggested severity")

    return missing_fields


def recalculate_complaint_status(
    complaint: Complaint,
) -> ComplaintStatus:
    """
    Calculate complaint status without committing it.
    """

    if complaint.status == ComplaintStatus.COMMITTED:
        return ComplaintStatus.COMMITTED

    missing_fields = get_missing_commit_fields(complaint)

    if missing_fields:
        return ComplaintStatus.PENDING_TRIAGE

    return ComplaintStatus.READY_TO_COMMIT
