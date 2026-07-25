from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy.orm import Session

from app.agents.nodes import (
    analyze_new_complaint_node,
    apply_correction_node,
    detect_intent_node,
    extract_correction_node,
    failure_node,
    finish_without_save_node,
    load_existing_complaint_node,
    save_new_complaint_node,
)
from app.agents.state import ComplaintAgentState

memory = InMemorySaver()


def route_after_intent(
    state: ComplaintAgentState,
) -> str:
    intent = state.get("intent")

    if intent == "new_complaint":
        return "analyze_new_complaint"

    if intent == "correction":
        return "load_existing_complaint"

    return "failure"


def build_complaint_graph(
    db: Session,
):
    workflow = StateGraph(ComplaintAgentState)

    workflow.add_node(
        "detect_intent",
        detect_intent_node,
    )

    workflow.add_node(
        "analyze_new_complaint",
        analyze_new_complaint_node,
    )

    workflow.add_node(
        "save_new_complaint",
        lambda state: save_new_complaint_node(
            state=state,
            db=db,
        ),
    )

    workflow.add_node(
        "load_existing_complaint",
        lambda state: load_existing_complaint_node(
            state=state,
            db=db,
        ),
    )

    workflow.add_node(
        "extract_correction",
        extract_correction_node,
    )

    workflow.add_node(
        "apply_correction",
        lambda state: apply_correction_node(
            state=state,
            db=db,
        ),
    )

    workflow.add_node(
        "failure",
        failure_node,
    )
    workflow.add_node(
        "finish_without_save",
        lambda state: state,
    )

    workflow.add_edge(
        START,
        "detect_intent",
    )

    workflow.add_conditional_edges(
        "detect_intent",
        route_after_intent,
        {
            "analyze_new_complaint": ("analyze_new_complaint"),
            "load_existing_complaint": ("load_existing_complaint"),
            "failure": "failure",
        },
    )

    workflow.add_conditional_edges(
        "analyze_new_complaint",
        route_after_analysis,
        {
            "save_new_complaint": "save_new_complaint",
            "finish_without_save": "finish_without_save",
            "failure": "failure",
        },
    )

    workflow.add_edge(
        "save_new_complaint",
        END,
    )

    workflow.add_edge(
        "load_existing_complaint",
        "extract_correction",
    )

    workflow.add_edge(
        "extract_correction",
        "apply_correction",
    )

    workflow.add_edge(
        "apply_correction",
        END,
    )

    workflow.add_edge(
        "failure",
        END,
    )

    return workflow.compile(checkpointer=memory)


def route_after_analysis(
    state: ComplaintAgentState,
) -> str:
    if state.get("error"):
        return "failure"

    if state.get("create_draft", True):
        return "save_new_complaint"

    return "finish_without_save"
