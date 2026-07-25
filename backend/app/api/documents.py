import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import (
    AIResponseValidationError,
    AIServiceError,
)
from app.schemas.document import (
    PDFComplaintUploadResponse,
)
from app.services.complaint_service import (
    create_ai_extracted_draft,
)
from app.services.document_service import (
    attach_document_to_complaint,
    create_document_record,
    extract_text_from_pdf,
    validate_and_save_pdf,
)
from app.services.groq_service import (
    analyze_complaint_text,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/documents",
    tags=["Complaint Documents"],
)


@router.post(
    "/analyze-pdf",
    response_model=PDFComplaintUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and analyze a complaint PDF",
)
async def analyze_complaint_pdf(
    file: Annotated[
        UploadFile,
        File(description="Pharmaceutical complaint PDF"),
    ],
    create_draft: Annotated[
        bool,
        Form(),
    ] = True,
    db: Session = Depends(get_db),
):
    saved_upload = None

    try:
        saved_upload = await validate_and_save_pdf(
            upload_file=file
        )

        extraction = extract_text_from_pdf(
            saved_upload.file_path
        )

        document_record = create_document_record(
            db=db,
            saved_upload=saved_upload,
            extraction=extraction,
        )

        warnings: list[str] = []

        if extraction.warning:
            warnings.append(extraction.warning)

        # Do not send an almost-empty/scanned document to the LLM.
        if extraction.extraction_status == "ocr_required":
            return PDFComplaintUploadResponse(
                success=False,
                document=document_record,
                text_preview=extraction.text[:1000],
                extracted_character_count=(
                    extraction.character_count
                ),
                analysis=None,
                assistant_message=(
                    "The PDF was uploaded, but insufficient "
                    "selectable text was detected. Please upload "
                    "a text-based PDF or use OCR."
                ),
                warnings=warnings,
            )

        ai_output = analyze_complaint_text(
            complaint_text=extraction.text
        )

        draft_complaint = None

        if create_draft:
            draft_complaint = create_ai_extracted_draft(
                db=db,
                raw_complaint_text=extraction.text,
                analysis=ai_output.analysis,
            )

            attach_document_to_complaint(
                db=db,
                document=document_record,
                complaint_id=draft_complaint.id,
            )

        all_warnings = [
            *warnings,
            *ai_output.analysis.warnings,
        ]

        return PDFComplaintUploadResponse(
            success=True,
            document=document_record,
            text_preview=extraction.text[:1500],
            extracted_character_count=(
                extraction.character_count
            ),
            analysis=ai_output.analysis.model_dump(
                mode="json"
            ),
            complaint_id=(
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
                draft_complaint.status.value
                if draft_complaint
                else None
            ),
            assistant_message=(
                ai_output.analysis.assistant_message
            ),
            warnings=all_warnings,
            used_model=ai_output.usage.used_model,
            fallback_used=(
                ai_output.usage.fallback_used
            ),
        )

    except HTTPException:
        raise

    except AIResponseValidationError as exc:
        logger.exception(
            "PDF AI response validation failed."
        )

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
            "Unexpected PDF complaint processing error."
        )

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Unexpected PDF complaint processing error: "
                f"{type(exc).__name__}: {exc}"
            ),
        ) from exc