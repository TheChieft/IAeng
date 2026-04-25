"""Intent classifier and plan extractor.

Phase 1: keyword/regex based (no LLM required).
Phase 2: LLM structured output (optional, enabled via config.USE_LLM).
"""
from __future__ import annotations
import re
from app.reto1.config import USE_LLM, SUSPENDED_METRICS

# ── keyword maps ────────────────────────────────────────────────────────────

_RANK_KW = r"\b(top|ranking|rank|mejor|peor|mejores|peores|mayor|menor|más alto|más bajo|máximo|mínimo|cuál.*más|cuáles.*más)\b"
_COMPARE_KW = r"\b(compar|versus|vs\.?|diferencia|contra|wealthy.*(non|no)\s*wealthy|(non|no)\s*wealthy.*wealthy|segmento|tipo de zona)\b"
_TREND_KW = r"\b(tendencia|trend|evolución|evoluciona|semanas|histórico|últimas.*semanas|cómo.*ha.*cambiado|L\dW)\b"
_INSIGHT_KW = r"\b(insight|problema|alert|alerta|qué.*pasa|qué.*tiene|situación|estado|reporte|resumen|issues)\b"
_HYPOTHESIS_KW = r"\b(hipótesis|hypothesis|explica|driver|causa|razón|por qué|podría.*ser|qué.*podría|asocia)\b"
_FOLLOWUP_SCOPE_KW = r"\b(solo en|solo para|ahora en|pero en|filtra|cambia.*a|en colombia|en méxico|en brasil|en argentina|en chile|en perú|en ecuador|en uruguay)\b"
_FOLLOWUP_VIZ_KW = r"\b(muestr.*gráfico|muéstramelo|en gráfico|visualiz|chart|gráfica|tabla|ahora.*gráfico)\b"
_QUERY_KW = r"\b(cuánto|cuál.*valor|dame el|promedio|mediana|agregado|aggregate|valor de)\b"

# metric name → id map (partial match)
_METRIC_ALIASES: dict[str, str] = {
    "perfect orders": "perfect_orders",
    "perfect order": "perfect_orders",
    "pro adoption": "pro_adoption_last_week",
    "gross profit": "gross_profit_ue",
    "turbo adoption": "turbo_adoption",
    "turbo": "turbo_adoption",
    "markdowns": "restaurants_markdowns_gmv",
    "markdown": "restaurants_markdowns_gmv",
    "assortment": "pct_restaurants_sessions_optimal_assortment",
    "atc cvr": "restaurants_ss_atc_cvr",
    "sst cvr restaurants": "restaurants_sst_ss_cvr",
    "sst cvr retail": "retail_sst_ss_cvr",
    "retail sst": "retail_sst_ss_cvr",
    "mltv": "mltv_top_verticals_adoption",
    "breakeven": "pct_pro_users_breakeven",
    "lead penetration": "lead_penetration",
    "non-pro ptc": "non_pro_ptc_op",
    "non pro ptc": "non_pro_ptc_op",
}

_COUNTRY_MAP: dict[str, str] = {
    "colombia": "CO", "méxico": "MX", "mexico": "MX", "brasil": "BR", "brazil": "BR",
    "argentina": "AR", "chile": "CL", "perú": "PE", "peru": "PE",
    "ecuador": "EC", "uruguay": "UY", "costa rica": "CR",
}


def _extract_metric(text: str) -> str | None:
    t = text.lower()
    for alias, mid in _METRIC_ALIASES.items():
        if alias in t:
            return mid
    return None


def _extract_country(text: str) -> str | None:
    t = text.lower()
    for name, code in _COUNTRY_MAP.items():
        if name in t:
            return code
    # try 2-letter codes
    m = re.search(r"\b(AR|BR|CL|CO|CR|EC|MX|PE|UY)\b", text.upper())
    return m.group(1) if m else None


def _extract_zone_type(text: str) -> str | None:
    t = text.lower()
    if "wealthy" in t and "non" not in t:
        return "Wealthy"
    if "non wealthy" in t or "no wealthy" in t:
        return "Non Wealthy"
    return None


def _extract_time_window(text: str) -> str:
    m = re.search(r"\bL([0-9])W\b", text.upper())
    if m:
        return f"L{m.group(1)}W"
    kw = text.lower()
    if "última semana" in kw or "last week" in kw:
        return "L0W"
    if "8 semanas" in kw or "ocho semanas" in kw:
        return "L8W"
    return "L0W"


def _extract_top_n(text: str) -> int:
    m = re.search(r"\btop[- ]?(\d+)\b", text.lower())
    return int(m.group(1)) if m else 5


def classify_intent(text: str, state=None) -> dict:
    """Return plan dict with intent + extracted entities."""
    t_lower = text.lower()

    # follow-up detection (scope or viz)
    if re.search(_FOLLOWUP_VIZ_KW, t_lower):
        intent = "follow_up_visualization"
    elif re.search(_FOLLOWUP_SCOPE_KW, t_lower) and state and state.last_intent:
        intent = "follow_up_scope_refine"
    elif re.search(_COMPARE_KW, t_lower):
        intent = "compare"
    elif re.search(_RANK_KW, t_lower):
        intent = "rank"
    elif re.search(_TREND_KW, t_lower):
        intent = "trend"
    elif re.search(_HYPOTHESIS_KW, t_lower):
        intent = "hypothesis_request"
    elif re.search(_INSIGHT_KW, t_lower):
        intent = "insight_request"
    elif re.search(_QUERY_KW, t_lower):
        intent = "query"
    else:
        intent = "insight_request"  # safe default

    metric = _extract_metric(text)
    country = _extract_country(text)
    zone_type = _extract_zone_type(text)
    time_window = _extract_time_window(text)
    top_n = _extract_top_n(text)

    plan = {
        "intent": intent,
        "metric": metric,
        "entity_scope": {"country": country, "city": None, "zone": None},
        "time_window": time_window,
        "top_n": top_n,
        "_raw_text": text,
    }

    if intent == "compare" and zone_type:
        plan["comparison"] = {
            "segment_a": zone_type,
            "segment_b": "Non Wealthy" if zone_type == "Wealthy" else "Wealthy",
            "dimension": "ZONE_TYPE",
        }
    elif intent == "compare":
        plan["comparison"] = {"segment_a": "Wealthy", "segment_b": "Non Wealthy", "dimension": "ZONE_TYPE"}

    return plan


def validate_plan(plan: dict, artifacts: dict) -> dict:
    """8 semantic rules from NB40 validate_plan_v2."""
    metric = plan.get("metric")
    intent = plan.get("intent")

    # Rule 1: unknown intent
    supported = {"rank", "compare", "trend", "insight_request", "hypothesis_request",
                 "follow_up_scope_refine", "follow_up_visualization", "query"}
    if intent not in supported:
        return {"valid": False, "action": "reject", "reason": f"Intent '{intent}' not supported",
                "suggestion": "Reformula como ranking, comparación o insight.", "adjusted_plan": plan}

    # Rule 2: suspended metric
    if metric in SUSPENDED_METRICS:
        return {"valid": False, "action": "reject",
                "reason": "lead_penetration suspendida — definición pendiente con equipo de datos.",
                "suggestion": "Prueba con perfect_orders o gross_profit_ue.", "adjusted_plan": plan}

    # Rule 3: ZONE ambiguity (ZONE alone not unique — need COUNTRY)
    scope = plan.get("entity_scope", {})
    if scope.get("zone") and not scope.get("country"):
        plan = {**plan, "requires_clarification": True}
        return {"valid": False, "action": "clarify",
                "reason": "ZONE solo no es único — necesito COUNTRY + CITY.",
                "suggestion": "¿En qué país/ciudad está esa zona?", "adjusted_plan": plan}

    # Rule 4: hypothesis → non-causal mode
    if intent == "hypothesis_request":
        plan = {**plan, "_non_causal_mode": True, "_add_association_caveat": True}

    # Rule 5: provisional direction caveat
    if metric:
        metrics_list = artifacts.get("metrics_cfg", {}).get("metrics", [])
        for m in metrics_list:
            if m["id"] == metric and m.get("direction_confidence") == "provisional":
                plan = {**plan, "_add_provisional_caveat": True}
                break

    return {"valid": True, "action": "execute", "reason": "ok", "suggestion": "", "adjusted_plan": plan}


# ── LLM planner (Phase 2, optional) ─────────────────────────────────────────

def _llm_classify(text: str, artifacts: dict) -> dict | None:
    """Try LLM structured output. Returns None on failure or if not configured."""
    if not USE_LLM:
        return None
    try:
        import anthropic
        metric_ids = [m["id"] for m in artifacts["metrics_cfg"]["metrics"]]
        client = anthropic.Anthropic()
        prompt = f"""You are an intent classifier for an operational analytics chatbot.

Available intents: rank, compare, trend, insight_request, hypothesis_request, follow_up_scope_refine, follow_up_visualization, query
Available metrics: {', '.join(metric_ids)}
Countries: AR, BR, CL, CO, CR, EC, MX, PE, UY

User question: "{text}"

Respond with a JSON object only:
{{
  "intent": "<intent>",
  "metric": "<metric_id or null>",
  "country": "<2-letter code or null>",
  "time_window": "<L0W|L1W...|L8W>",
  "top_n": <number or 5>,
  "zone_type": "<Wealthy|Non Wealthy or null>"
}}"""
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}]
        )
        import json
        return json.loads(resp.content[0].text)
    except Exception:
        return None


def build_plan(text: str, artifacts: dict, state=None) -> dict:
    """Main entry: classify → validate → return plan."""
    llm_result = _llm_classify(text, artifacts)

    if llm_result:
        plan = {
            "intent": llm_result.get("intent", "insight_request"),
            "metric": llm_result.get("metric"),
            "entity_scope": {
                "country": llm_result.get("country"),
                "city": None,
                "zone": None,
            },
            "time_window": llm_result.get("time_window", "L0W"),
            "top_n": llm_result.get("top_n", 5),
            "_raw_text": text,
        }
        zt = llm_result.get("zone_type")
        if plan["intent"] == "compare":
            plan["comparison"] = {
                "segment_a": zt or "Wealthy",
                "segment_b": "Non Wealthy" if (zt or "Wealthy") == "Wealthy" else "Wealthy",
                "dimension": "ZONE_TYPE",
            }
    else:
        plan = classify_intent(text, state)

    if state:
        from app.reto1.state import apply_follow_up
        if plan["intent"] in ("follow_up_scope_refine", "follow_up_visualization"):
            plan = apply_follow_up(state, plan)

    validation = validate_plan(plan, artifacts)
    if not validation["valid"]:
        return {**plan, "_validation": validation, "_error": validation["reason"],
                "_suggestion": validation["suggestion"]}

    return {**validation["adjusted_plan"], "_validation": validation}
