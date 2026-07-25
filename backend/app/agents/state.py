from typing import Any, Literal, TypedDict


class ComplaintAgentState(TypedDict, total=False):
    """
    Shared state passed between LangGraph nodes.

    The graph handles both:
    1. New complaint intake
    2. Existing complaint correction
    """

    thread_id: str
    intent: Literal["new_complaint", "correction", "unknown"]

    user_message: str
    create_draft: bool
    
    complaint_id: str | None
    complaint_number: str | None

    existing_complaint: dict[str, Any] | None

    analysis: dict[str, Any] | None
    field_updates: dict[str, Any]

    missing_fields: list[str]
    warnings: list[str]
    validation_errors: list[str]

    processing_status: str
    assistant_message: str

    used_model: str | None
    fallback_used: bool

    error: str | None