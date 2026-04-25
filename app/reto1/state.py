"""Session state dataclass for chat conversations."""
from dataclasses import dataclass, field


_NON_ANALYTICAL_INTENTS = {
    "greeting", "help", "no_intent", "about_data",
    "explain_result", "explain_metric", "explain_table", "no_intent_guided",
    "clarify_metric", "clarify_country_scope",
    "explain_segments", "available_metrics", "available_metrics_for_scope",
    "explain_signals", "explain_result_simple",
}


@dataclass
class ChatSessionState:
    last_metric_id: str | None = None
    last_metric_display: str | None = None
    last_entity: dict = field(default_factory=lambda: {"country": None, "city": None, "zone": None})
    last_filters: list[dict] = field(default_factory=list)
    last_comparison: dict | None = None
    last_time_window: str = "L0W"
    mode: str = "direct_answer"
    last_visualization: str | None = None      # chart_type from last tool result
    last_result_type: str | None = None         # intent of last analytical turn
    last_tool_result: dict | None = None
    last_tool_name: str | None = None
    last_intent: str | None = None
    last_top_insight: dict | None = None        # first row of last insight result
    last_chart_spec: dict | None = None         # last rendered chart spec (set in app.py)
    last_compare_result: dict | None = None     # full compare_segments result
    last_trend_result: dict | None = None       # full get_trend result
    last_summary_text: str | None = None        # summary_text of top insight


def init_session() -> ChatSessionState:
    return ChatSessionState()


def update_state(state: ChatSessionState, plan: dict, result: dict) -> ChatSessionState:
    if plan.get("metric"):
        state.last_metric_id = plan["metric"]

    # preserve non-None values — never overwrite a known country/city with None
    scope = plan.get("entity_scope") or {}
    state.last_entity = {
        "country": scope.get("country") or state.last_entity.get("country"),
        "city": scope.get("city") or state.last_entity.get("city"),
        "zone": scope.get("zone") or state.last_entity.get("zone"),
    }

    if plan.get("time_window"):
        state.last_time_window = plan["time_window"]
    if plan.get("comparison"):
        state.last_comparison = plan["comparison"]
    if plan.get("intent") and plan["intent"] != "greeting":
        state.last_intent = plan["intent"]
        if plan["intent"] not in _NON_ANALYTICAL_INTENTS:
            state.last_result_type = plan["intent"]
            state.mode = "hypothesis" if plan["intent"] == "hypothesis_request" else "direct_answer"

    state.last_tool_result = result
    state.last_tool_name = result.get("tool")

    if result.get("chart_type"):
        state.last_visualization = result["chart_type"]

    # save top insight for drilldown / explain follow-ups
    if result.get("tool") == "route_insight_request" and result.get("rows"):
        state.last_top_insight = result["rows"][0]
        state.last_summary_text = str(result["rows"][0].get("summary_text", ""))

    # save compare result for contextual follow-ups
    if result.get("tool") == "compare_segments":
        state.last_compare_result = result

    # save trend result for contextual follow-ups
    if result.get("tool") == "get_trend":
        state.last_trend_result = result

    # save metric display name from tool result
    if result.get("metric_display_name"):
        state.last_metric_display = result["metric_display_name"]

    return state


def apply_follow_up(state: ChatSessionState, new_plan: dict) -> dict:
    """Inherit entity/metric/time from previous turn if not specified."""
    merged = dict(new_plan)
    if not merged.get("metric") and state.last_metric_id:
        merged["metric"] = state.last_metric_id
    scope = merged.get("entity_scope") or {}
    if not any(scope.values()):
        merged["entity_scope"] = dict(state.last_entity)
    elif scope.get("country"):
        merged["entity_scope"] = {
            "country": scope.get("country"),
            "city": scope.get("city"),
            "zone": scope.get("zone"),
        }
    elif scope.get("city"):
        merged["entity_scope"] = {
            "country": state.last_entity.get("country"),
            "city": scope.get("city"),
            "zone": scope.get("zone"),
        }
    else:
        merged["entity_scope"] = {
            "country": state.last_entity.get("country"),
            "city": state.last_entity.get("city"),
            "zone": scope.get("zone") or state.last_entity.get("zone"),
        }
    if not merged.get("time_window"):
        merged["time_window"] = state.last_time_window
    return merged


def apply_scope_switch(state: ChatSessionState, new_plan: dict) -> dict:
    """Switch only the requested scope while preserving the prior analytical intent."""
    merged = apply_follow_up(state, new_plan)
    last_intent = state.last_result_type or state.last_intent or "insight_request"
    if last_intent == "compare":
        merged["intent"] = "compare"
        merged["comparison"] = state.last_comparison or {"segment_a": "Wealthy", "segment_b": "Non Wealthy", "dimension": "ZONE_TYPE"}
    elif last_intent in {"rank", "trend", "query", "hypothesis_request", "insight_request"}:
        merged["intent"] = last_intent
    else:
        merged["intent"] = "insight_request"
    return merged


def build_plan_from_action(action: str, state: ChatSessionState) -> dict | None:
    """
    Build a structured plan directly from session state + action name.
    Returns None if state lacks required context.
    """
    base = {
        "metric": state.last_metric_id,
        "entity_scope": dict(state.last_entity),
        "time_window": state.last_time_window,
        "_planner_source": "follow_up_action",
        "_action_type": action,
    }

    if action == "trend_for_last_metric":
        if not state.last_metric_id:
            return None
        return {**base, "intent": "trend"}

    if action == "rank_for_last_metric":
        if not state.last_metric_id:
            return None
        return {**base, "intent": "rank", "top_n": 5}

    if action == "compare_current_scope":
        if not state.last_metric_id:
            return None
        comp = state.last_comparison or {"segment_a": "Wealthy", "segment_b": "Non Wealthy", "dimension": "ZONE_TYPE"}
        return {**base, "intent": "compare", "comparison": comp}

    if action == "hypothesis_for_last_result":
        if not state.last_metric_id:
            return None
        return {**base, "intent": "hypothesis_request",
                "_non_causal_mode": True, "_add_association_caveat": True}

    if action == "insight_for_last_scope":
        return {**base, "intent": "insight_request"}

    if action in ("drilldown_top_insight", "explain_top_insight"):
        if not state.last_top_insight:
            return None
        entity = state.last_top_insight.get("display_entity", "")
        parts = [p.strip() for p in entity.split("|")]
        country = parts[0] if len(parts) >= 1 else state.last_entity.get("country")
        city = parts[1] if len(parts) >= 2 else None
        zone = parts[2] if len(parts) >= 3 else None
        explain_ctx = {
            "last_insight": state.last_top_insight,
            "last_metric": state.last_metric_id,
            "last_metric_display": state.last_metric_display,
            "last_entity": dict(state.last_entity),
            "last_intent": state.last_intent,
        }
        if action == "explain_top_insight":
            return {
                **base,
                "intent": "explain_result",
                "_explain_context": explain_ctx,
            }
        return {
            **base,
            "intent": "insight_request",
            "entity_scope": {"country": country, "city": city, "zone": zone},
        }

    return None
