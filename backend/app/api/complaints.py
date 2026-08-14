from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.complaint_service import (
    apply_complaint_corrections,
    create_complaint,
    delete_complaint,
    get_complaint_by_id,
    get_complaint_by_number,
    get_complaints,
    get_missing_commit_fields,
    update_complaint,
)
from app.models.complaint import ComplaintStatus
from app.schemas.complaint import (
    ComplaintResponse,
    ComplaintManualSaveRequest,
    ComplaintCreate,
    ComplaintListResponse,
    ComplaintDeleteResponse,
    ComplaintUpdate,
)
from app.schemas.complaint_correction import (
    ComplaintCommitResponse,
    CorrectionHistoryListResponse,
)
from app.models.complaint_correction import ComplaintCorrection
from sqlalchemy import select

router = APIRouter(
    prefix="/complaints",
    tags=["Complaints"],
)


@router.patch(
    "/{complaint_id}/manual-save",
    response_model=ComplaintResponse,
)
def save_manual_form_changes(
    complaint_id: UUID,
    complaint_data: ComplaintManualSaveRequest,
    db: Session = Depends(get_db),
):
    complaint = get_complaint_by_id(
        db=db,
        complaint_id=complaint_id,
    )

    field_updates = complaint_data.model_dump(exclude_unset=True)

    return apply_complaint_corrections(
        db=db,
        complaint=complaint,
        field_updates=field_updates,
        source="manual",
        user_message="Manual form update",
    )


@router.post(
    "/{complaint_id}/commit",
    response_model=ComplaintCommitResponse,
)
def commit_complaint_to_qms(
    complaint_id: UUID,
    db: Session = Depends(get_db),
):
    complaint = get_complaint_by_id(
        db=db,
        complaint_id=complaint_id,
    )

    if complaint.status == ComplaintStatus.COMMITTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Complaint is already committed.",
        )

    missing_fields = get_missing_commit_fields(complaint)

    if missing_fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": (
                    "Complaint cannot be committed because "
                    "required information is missing."
                ),
                "missing_fields": missing_fields,
            },
        )

    try:
        complaint.status = ComplaintStatus.COMMITTED
        db.add(complaint)
        db.commit()
        db.refresh(complaint)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The QMS ledger is temporarily unavailable. Please try again.",
        ) from exc

    return ComplaintCommitResponse(
        success=True,
        complaint_id=complaint.id,
        complaint_number=complaint.complaint_number,
        status=complaint.status.value,
        message=(
            f"Complaint {complaint.complaint_number} "
            "was committed to the QMS ledger."
        ),
    )


@router.post(
    "",
    response_model=ComplaintResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_new_complaint(
    complaint_data: ComplaintCreate,
    db: Session = Depends(get_db),
):
    return create_complaint(
        db=db,
        complaint_data=complaint_data,
    )


@router.get(
    "",
    response_model=ComplaintListResponse,
)
def list_complaints(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    complaints, total = get_complaints(
        db=db,
        page=page,
        page_size=page_size,
    )

    return ComplaintListResponse(
        total=total,
        page=page,
        page_size=page_size,
        complaints=complaints,
    )


@router.get(
    "/number/{complaint_number}",
    response_model=ComplaintResponse,
)
def retrieve_complaint_by_number(
    complaint_number: str,
    db: Session = Depends(get_db),
):
    return get_complaint_by_number(
        db=db,
        complaint_number=complaint_number,
    )


@router.get(
    "/{complaint_id}",
    response_model=ComplaintResponse,
)
def retrieve_complaint(
    complaint_id: UUID,
    db: Session = Depends(get_db),
):
    return get_complaint_by_id(
        db=db,
        complaint_id=complaint_id,
    )


@router.patch(
    "/{complaint_id}",
    response_model=ComplaintResponse,
)
def update_existing_complaint(
    complaint_id: UUID,
    complaint_data: ComplaintUpdate,
    db: Session = Depends(get_db),
):
    return update_complaint(
        db=db,
        complaint_id=complaint_id,
        complaint_data=complaint_data,
    )


@router.delete(
    "/{complaint_id}",
    response_model=ComplaintDeleteResponse,
)
def remove_complaint(
    complaint_id: UUID,
    db: Session = Depends(get_db),
):
    deleted_complaint = delete_complaint(
        db=db,
        complaint_id=complaint_id,
    )

    return ComplaintDeleteResponse(
        message="Complaint deleted successfully.",
        complaint_number=deleted_complaint.complaint_number,
    )
