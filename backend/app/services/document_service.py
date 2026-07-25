import re
import uuid
from dataclasses import dataclass
from pathlib import Path

import pymupdf
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.complaint_document import ComplaintDocument
from app.schemas.document import PDFExtractionResult


ALLOWED_PDF_CONTENT_TYPES = {
    "application/pdf",
    "application/x-pdf",
}


@dataclass
class SavedUpload:
    original_filename: str
    stored_filename: str
    file_path: Path
    content_type: str
    file_size_bytes: int


def get_upload_directory() -> Path:
    upload_directory = Path(
        settings.UPLOAD_DIRECTORY
    ).resolve()

    upload_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return upload_directory


def sanitize_filename(filename: str) -> str:
    """
    Remove unsafe characters from a client-provided filename.
    """

    path_name = Path(filename).name

    cleaned = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        path_name,
    )

    return cleaned[:150] or "complaint.pdf"


async def validate_and_save_pdf(
    upload_file: UploadFile,
) -> SavedUpload:
    original_filename = (
        upload_file.filename or "complaint.pdf"
    )

    safe_original_name = sanitize_filename(
        original_filename
    )

    if not safe_original_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF complaint documents are supported.",
        )

    if (
        upload_file.content_type
        and upload_file.content_type
        not in ALLOWED_PDF_CONTENT_TYPES
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid file content type. "
                "Please upload a PDF document."
            ),
        )

    file_bytes = await upload_file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded PDF is empty.",
        )

    max_size_bytes = (
        settings.MAX_UPLOAD_SIZE_MB
        * 1024
        * 1024
    )

    if len(file_bytes) > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"PDF exceeds the maximum upload size of "
                f"{settings.MAX_UPLOAD_SIZE_MB} MB."
            ),
        )

    # PDF file signature check.
    if not file_bytes.startswith(b"%PDF"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid PDF.",
        )

    unique_name = (
        f"{uuid.uuid4()}_{safe_original_name}"
    )

    file_path = (
        get_upload_directory()
        / unique_name
    )

    try:
        file_path.write_bytes(file_bytes)
    except OSError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to store the uploaded PDF.",
        ) from exc
    finally:
        await upload_file.close()

    return SavedUpload(
        original_filename=safe_original_name,
        stored_filename=unique_name,
        file_path=file_path,
        content_type="application/pdf",
        file_size_bytes=len(file_bytes),
    )


def normalize_extracted_text(text: str) -> str:
    """
    Preserve paragraph separation while reducing broken whitespace.
    """

    text = text.replace("\x00", " ")

    lines = [
        re.sub(r"[ \t]+", " ", line).strip()
        for line in text.splitlines()
    ]

    normalized_lines: list[str] = []
    previous_blank = False

    for line in lines:
        is_blank = not line

        if is_blank and previous_blank:
            continue

        normalized_lines.append(line)
        previous_blank = is_blank

    return "\n".join(normalized_lines).strip()


def extract_text_from_pdf(
    file_path: Path,
) -> PDFExtractionResult:
    try:
        document = pymupdf.open(file_path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded PDF could not be opened.",
        ) from exc

    try:
        if document.page_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The PDF contains no pages.",
            )

        if document.page_count > settings.MAX_PDF_PAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"PDF contains {document.page_count} pages. "
                    f"The maximum allowed is "
                    f"{settings.MAX_PDF_PAGES}."
                ),
            )

        page_texts: list[str] = []
        page_text_lengths: list[int] = []

        for page_number in range(
            document.page_count
        ):
            page = document.load_page(page_number)

            page_text = page.get_text(
                "text",
                sort=True,
            )

            page_text = normalize_extracted_text(
                page_text
            )

            page_texts.append(page_text)
            page_text_lengths.append(
                len(page_text)
            )

        extracted_text = "\n\n".join(
            text for text in page_texts if text
        ).strip()

        warning = None
        extraction_status = "completed"

        if (
            len(extracted_text)
            < settings.MIN_EXTRACTED_TEXT_LENGTH
        ):
            extraction_status = "ocr_required"
            warning = (
                "Very little selectable text was found. "
                "The PDF may be scanned and require OCR."
            )

        return PDFExtractionResult(
            text=extracted_text,
            page_count=document.page_count,
            character_count=len(extracted_text),
            extraction_status=extraction_status,
            warning=warning,
            page_text_lengths=page_text_lengths,
        )

    finally:
        document.close()


def create_document_record(
    db: Session,
    saved_upload: SavedUpload,
    extraction: PDFExtractionResult,
    complaint_id=None,
) -> ComplaintDocument:
    document_record = ComplaintDocument(
        complaint_id=complaint_id,
        original_filename=(
            saved_upload.original_filename
        ),
        stored_filename=(
            saved_upload.stored_filename
        ),
        file_path=str(saved_upload.file_path),
        content_type=saved_upload.content_type,
        file_size_bytes=(
            saved_upload.file_size_bytes
        ),
        page_count=extraction.page_count,
        extracted_text=extraction.text,
        extraction_status=(
            extraction.extraction_status
        ),
        extraction_warning=extraction.warning,
    )

    db.add(document_record)
    db.commit()
    db.refresh(document_record)

    return document_record


def attach_document_to_complaint(
    db: Session,
    document: ComplaintDocument,
    complaint_id,
) -> ComplaintDocument:
    document.complaint_id = complaint_id

    db.add(document)
    db.commit()
    db.refresh(document)

    return document