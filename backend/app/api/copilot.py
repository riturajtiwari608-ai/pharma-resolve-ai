import logging
import traceback
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.complaint_graph import build_complaint_graph
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


def make_serializable(value: Any) -> Any:
    """
    Convert common SQLAlchemy/Pydantic values into response-safe data.
    """

    if value is None:
        return None

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    if isinstance(value, dict):
        return value

    if hasattr(value, "__table__"):
        result = {}

        for column in value.__table__.columns:
            column_value = getattr(value, column.name)

            if hasattr(column_value, "value"):
                column_value = column_value.value
            elif hasattr(column_value, "isoformat"):
                column_value = column_value.isoformat()
            elif isinstance(column_value, uuid.UUID):
                column_value = str(column_value)

            result[column.name] = column_value

        return result

    return value


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

    initial_state = {
        "thread_id": thread_id,
        "user_message": request_data.message.strip(),
        "complaint_id": (
            str(request_data.complaint_id)
            if request_data.complaint_id
            else None
        ),
        "create_draft": request_data.create_draft,
        "intent": None,
        "complaint_number": None,
        "existing_complaint": None,
        "analysis": None,
        "field_updates": {},
        "missing_fields": [],
        "warnings": [],
        "validation_errors": [],
        "processing_status": "processing",
        "assistant_message": None,
        "used_model": None,
        "fallback_used": False,
        "error": None,
    }

    try:
        graph = build_complaint_graph(db)

        result = graph.invoke(
            initial_state,
            config={
                "configurable": {
                    "thread_id": thread_id,
                }
            },
        )

        if not isinstance(result, dict):
            raise TypeError(
                "LangGraph returned an invalid result. "
                f"Expected dict, received {type(result).__name__}."
            )

        complaint_data = (
            result.get("existing_complaint")
            or result.get("analysis")
        )

        complaint_data = make_serializable(
            complaint_data
        )

        return ComplaintCopilotResponse(
            success=not bool(result.get("error")),
            intent=result.get("intent") or "unknown",
            thread_id=thread_id,
            complaint_id=result.get("complaint_id"),
            complaint_number=result.get(
                "complaint_number"
            ),
            processing_status=(
                result.get("processing_status")
                or "unknown"
            ),
            assistant_message=(
                result.get("assistant_message")
                or "Request processed."
            ),
            complaint_data=complaint_data,
            field_updates=(
                result.get("field_updates")
                or {}
            ),
            missing_fields=(
                result.get("missing_fields")
                or []
            ),
            warnings=result.get("warnings") or [],
            used_model=result.get("used_model"),
            fallback_used=bool(
                result.get("fallback_used", False)
            ),
        )

    except AIServiceError as exc:
        logger.exception(
            "AI service failed during complaint processing."
        )

        raise HTTPException(
            status_code=503,
            detail=f"AI service error: {str(exc)}",
        ) from exc

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception(
            "Complaint Copilot workflow failed."
        )

        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=(
                f"{type(exc).__name__}: {str(exc)}"
            ),
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
        complaint_number=result.get("complaint_number"),
        processing_status=result.get(
            "processing_status",
            "unknown",
        ),
        assistant_message=result.get(
            "assistant_message",
            "Request processed.",
        ),
        complaint_data=(result.get("existing_complaint") or result.get("analysis")),
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
