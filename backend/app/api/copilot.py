import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.complaint_graph import (
    build_complaint_graph,
)
from app.core.database import get_db
from app.core.exceptions import AIServiceError
from app.schemas.copilot import (
    ComplaintCopilotRequest,
    ComplaintCopilotResponse,
)


logger = logging.getLogger(__name__)


router = APIRouter(
    prefix="/copilot",
    tags=["Complaint Copilot"],
)


@router.post(
    "/message",
    response_model=ComplaintCopilotResponse,
)
def process_copilot_message(
    request_data: ComplaintCopilotRequest,
    db: Session = Depends(get_db),
):
    thread_id = (
        request_data.thread_id
        or str(uuid.uuid4())
    )

    graph = build_complaint_graph(db)

    initial_state = {
        "thread_id": thread_id,
        "user_message": request_data.message,
        "complaint_id": (
            str(request_data.complaint_id)
            if request_data.complaint_id
            else None
        ),
        "create_draft": request_data.create_draft,
        "field_updates": {},
        "missing_fields": [],
        "warnings": [],
        "validation_errors": [],
        "processing_status": "processing",
        "fallback_used": False,
        "error": None,
    }

    try:
        result = graph.invoke(
            initial_state,
            config={
                "configurable": {
                    "thread_id": thread_id,
                }
            },
        )

    except AIServiceError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception(
            "Complaint Copilot workflow failed."
        )

        raise HTTPException(
            status_code=500,
            detail="Complaint Copilot workflow failed.",
        ) from exc

    success = not bool(result.get("error"))

    return ComplaintCopilotResponse(
        success=success,
        intent=result.get(
            "intent",
            "unknown",
        ),
        thread_id=thread_id,
        complaint_id=result.get("complaint_id"),
        complaint_number=result.get(
            "complaint_number"
        ),
        processing_status=result.get(
            "processing_status",
            "unknown",
        ),
        assistant_message=result.get(
            "assistant_message",
            "Request processed.",
        ),
        complaint_data=(
            result.get("existing_complaint")
            or result.get("analysis")
        ),
        field_updates=result.get(
            "field_updates",
            {},
        ),
        missing_fields=result.get(
            "missing_fields",
            [],
        ),
        warnings=result.get(
            "warnings",
            [],
        ),
        used_model=result.get("used_model"),
        fallback_used=result.get(
            "fallback_used",
            False,
        ),
    )