from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.complaint import (
    ComplaintCreate,
    ComplaintDeleteResponse,
    ComplaintListResponse,
    ComplaintResponse,
    ComplaintUpdate,
)
from app.services.complaint_service import (
    create_complaint,
    delete_complaint,
    get_complaint_by_id,
    get_complaint_by_number,
    get_complaints,
    update_complaint,
)


router = APIRouter(
    prefix="/complaints",
    tags=["Complaints"],
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