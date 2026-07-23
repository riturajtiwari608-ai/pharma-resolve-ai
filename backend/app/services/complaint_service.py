from datetime import datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.schemas.ai_intake import ComplaintAnalysisResult
from app.models.complaint import ComplaintStatus
from app.models.complaint import Complaint
from app.schemas.complaint import ComplaintCreate, ComplaintUpdate


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
    statement = select(Complaint).where(
        Complaint.complaint_number == complaint_number
    )

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
        impacted_non_product_material=(
            extracted.impacted_non_product_material
        ),
        complaint_category=extracted.complaint_category,
        structured_defect_summary=(
            extracted.structured_defect_summary
        ),
        raw_complaint_text=raw_complaint_text,
        suggested_severity=extracted.suggested_severity,
        suggested_next_action=extracted.suggested_next_action,
        initial_risk_assessment=(
            extracted.initial_risk_assessment
        ),
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