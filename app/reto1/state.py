"""Session state dataclass for chat conversations."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChatSessionState:
    last_metric_id: str | None = None
    last_entity: dict = field(default_factory=lambda: {"country": None, "city": None, "zone": None})
    last_filters: list[dict] = field(default_factory=list)
    last_comparison: dict | None = None
    last_time_window: str = "L0W"
    mode: str = "direct_answer"  # "direct_answer" | "hypothesis" | "follow_up"
    last_visualization: str | None = None
    last_tool_result: dict | None = None
    last_intent: str | None = None


def init_session() -> ChatSessionState:
    return ChatSessionState()


def update_state(state: ChatSessionState, plan: dict, result: dict) -> ChatSessionState:
    if plan.get("metric"):
        state.last_metric_id = plan["metric"]
    if plan.get("entity_scope"):
        scope = plan["entity_scope"]
        state.last_entity = {
            "country": scope.get("country", state.last_entity.get("country")),
            "city": scope.get("city", state.last_entity.get("city")),
            "zone": scope.get("zone", state.last_entity.get("zone")),
        }
    if plan.get("time_window"):
        state.last_time_window = plan["time_window"]
    if plan.get("comparison"):
        state.last_comparison = plan["comparison"]
    if plan.get("intent"):
        state.last_intent = plan["intent"]
        if plan["intent"] == "hypothesis_request":
            state.mode = "hypothesis"
        else:
            state.mode = "direct_answer"
    state.last_tool_result = result
    if result.get("chart_type"):
        state.last_visualization = result["chart_type"]
    return state


def apply_follow_up(state: ChatSessionState, new_plan: dict) -> dict:
    """Inherit entity/metric/time from previous turn if not specified."""
    merged = dict(new_plan)
    if not merged.get("metric") and state.last_metric_id:
        merged["metric"] = state.last_metric_id
    if not merged.get("entity_scope") or not any(merged["entity_scope"].values()):
        merged["entity_scope"] = dict(state.last_entity)
    if not merged.get("time_window"):
        merged["time_window"] = state.last_time_window
    return merged
