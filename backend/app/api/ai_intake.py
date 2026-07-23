import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import (
    AIConfigurationError,
    AIModelUnavailableError,
    AIResponseValidationError,
    AIServiceError,
)
from app.schemas.ai_intake import (
    ComplaintTextAnalysisRequest,
    ComplaintTextAnalysisResponse,
)
from app.services.complaint_service import (
    create_ai_extracted_draft,
)
from app.services.groq_service import (
    analyze_complaint_text,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/ai/intake",
    tags=["AI Complaint Intake"],
)


@router.post(
    "/analyze-text",
    response_model=ComplaintTextAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze raw pharmaceutical complaint text",
)
def analyze_text_complaint(
    request_data: ComplaintTextAnalysisRequest,
    db: Session = Depends(get_db),
):
    try:
        ai_output = analyze_complaint_text(
            complaint_text=request_data.complaint_text,
        )

        draft_complaint = None

        if request_data.create_draft:
            draft_complaint = create_ai_extracted_draft(
                db=db,
                raw_complaint_text=request_data.complaint_text,
                analysis=ai_output.analysis,
            )

        return ComplaintTextAnalysisResponse(
            analysis=ai_output.analysis,
            draft_complaint_id=(
                str(draft_complaint.id)
                if draft_complaint
                else None
            ),
            complaint_number=(
                draft_complaint.complaint_number
                if draft_complaint
                else None
            ),
            complaint_status=(
                draft_complaint.status
                if draft_complaint
                else None
            ),
            usage=ai_output.usage,
        )

    except AIConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc

    except AIModelUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except AIResponseValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    except AIServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Unexpected complaint analysis failure."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unexpected AI complaint analysis failure.",
        ) from exc