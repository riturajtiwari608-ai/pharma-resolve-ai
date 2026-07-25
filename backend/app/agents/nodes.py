from uuid import UUID

from sqlalchemy.orm import Session

from app.agents.state import ComplaintAgentState
from app.schemas.ai_intake import ComplaintAnalysisResult
from app.services.complaint_service import (
    apply_complaint_corrections,
    complaint_to_dict,
    create_ai_extracted_draft,
    get_complaint_by_id,
)
from app.services.correction_service import (
    extract_complaint_corrections,
)
from app.services.groq_service import (
    analyze_complaint_text,
)



def detect_intent_node(
    state: ComplaintAgentState,
) -> dict:
    """
    Route based primarily on complaint_id.

    A complaint_id means the user is editing an existing complaint.
    Without complaint_id, the message is treated as a new complaint.
    """

    complaint_id = state.get("complaint_id")
    message = state.get("user_message", "").strip()

    if not message:
        return {
            "intent": "unknown",
            "error": "User message is empty.",
            "processing_status": "failed",
        }

    if complaint_id:
        return {
            "intent": "correction",
        }

    return {
        "intent": "new_complaint",
    }


def analyze_new_complaint_node(
    state: ComplaintAgentState,
) -> dict:
    output = analyze_complaint_text(
        complaint_text=state["user_message"],
    )

    return {
        "analysis": output.analysis.model_dump(
            mode="json"
        ),
        "missing_fields": (
            output.analysis.missing_fields
        ),
        "warnings": output.analysis.warnings,
        "processing_status": (
            output.analysis.processing_status
        ),
        "assistant_message": (
            output.analysis.assistant_message
        ),
        "used_model": output.usage.used_model,
        "fallback_used": output.usage.fallback_used,
    }


def save_new_complaint_node(
    state: ComplaintAgentState,
    db: Session,
) -> dict:
    analysis_data = state.get("analysis")

    if not analysis_data:
        return {
            "error": "No complaint analysis is available.",
            "processing_status": "failed",
        }

    analysis = ComplaintAnalysisResult.model_validate(
        analysis_data
    )

    complaint = create_ai_extracted_draft(
        db=db,
        raw_complaint_text=state["user_message"],
        analysis=analysis,
    )

    return {
        "complaint_id": str(complaint.id),
        "complaint_number": complaint.complaint_number,
        "existing_complaint": complaint_to_dict(
            complaint
        ),
    }


def load_existing_complaint_node(
    state: ComplaintAgentState,
    db: Session,
) -> dict:
    complaint_id = state.get("complaint_id")

    if not complaint_id:
        return {
            "error": (
                "Complaint ID is required for corrections."
            ),
            "processing_status": "failed",
        }

    complaint = get_complaint_by_id(
        db=db,
        complaint_id=UUID(complaint_id),
    )

    return {
        "complaint_number": complaint.complaint_number,
        "existing_complaint": complaint_to_dict(
            complaint
        ),
    }


def extract_correction_node(
    state: ComplaintAgentState,
) -> dict:
    existing_complaint = state.get(
        "existing_complaint"
    )

    if not existing_complaint:
        return {
            "error": "Existing complaint data is missing.",
            "processing_status": "failed",
        }

    result = extract_complaint_corrections(
        user_message=state["user_message"],
        existing_complaint=existing_complaint,
    )

    status = (
        "correction_ready"
        if result.field_updates
        else "no_changes_detected"
    )

    return {
        "field_updates": result.field_updates,
        "assistant_message": result.assistant_message,
        "warnings": result.warnings,
        "processing_status": status,
    }


def apply_correction_node(
    state: ComplaintAgentState,
    db: Session,
) -> dict:
    complaint_id = state.get("complaint_id")
    updates = state.get("field_updates", {})

    if not complaint_id:
        return {
            "error": "Complaint ID is missing.",
            "processing_status": "failed",
        }

    if not updates:
        return {
            "processing_status": "no_changes_detected",
        }

    complaint = get_complaint_by_id(
        db=db,
        complaint_id=UUID(complaint_id),
    )

    updated_complaint = apply_complaint_corrections(
        db=db,
        complaint=complaint,
        field_updates=updates,
    )

    updated_fields_text = ", ".join(
        field_name.replace("_", " ")
        for field_name in updates
    )
    updated_complaint = apply_complaint_corrections(
        db=db,
        complaint=complaint,
        field_updates=updates,
        user_message=state.get("user_message"),
        source="copilot",
    )

    return {
        "existing_complaint": complaint_to_dict(
            updated_complaint
        ),
        "complaint_number": (
            updated_complaint.complaint_number
        ),
        "processing_status": (
            updated_complaint.status.value
        ),
        "assistant_message": (
            f"Updated {updated_fields_text}. "
            "Please review the revised complaint form."
        ),
    }
    


def failure_node(
    state: ComplaintAgentState,
) -> dict:
    return {
        "processing_status": "failed",
        "assistant_message": (
            state.get("error")
            or "Unable to process the complaint request."
        ),
    }
def finish_without_save_node(
    state: ComplaintAgentState,
) -> dict:
    return {
        "processing_status": (
            state.get("processing_status")
            or "analysis_complete"
        )
    }