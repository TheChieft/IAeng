"""Intent classifier and plan extractor.

Phase 1 (always active): keyword/regex router — deterministic, thread-safe.
Phase 2 (optional): Gemini structured output — enabled via .env.

build_plan() always returns a valid plan. Gemini failure → keyword fallback.
Timeout uses concurrent.futures (thread-safe) — signal.SIGALRM not used.
"""
from __future__ import annotations
import json
import re
import logging
import concurrent.futures
from app.reto1.config import LLM_ACTIVE, SUSPENDED_METRICS, GEMINI_API_KEY, GEMINI_MODEL, LLM_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

# ── terminal / UX intent detection ───────────────────────────────────────────

_GREETING_RE = re.compile(
    r"^\s*(hola|hi|hello|buenos\s*días|buenas\s*tardes|buenas\s*noches|buenas|hey|saludos|"
    r"qué\s*tal|cómo\s*estás?|como\s*estas?|good\s*morning|good\s*afternoon|"
    r"hola\s+\w+|hey\s+\w+)\s*[!?.,]?\s*$",
    re.IGNORECASE,
)
# catches "Hola Gemini, como estas?" and similar multi-word greetings
_GREETING_CONVERSATIONAL_RE = re.compile(
    r"^\s*(hola|hey|hi)\s+\w+[,.]?\s*(como|cómo)\s+estas?[!?.]?\s*$",
    re.IGNORECASE,
)
_VAGUE_RE = re.compile(
    r"^\s*(ok|okay|bien|gracias|thanks|thank\s*you|si|sí|no|perfecto|entendido|claro|dale|listo)\s*[!?.,]?\s*$",
    re.IGNORECASE,
)
_HELP_RE = re.compile(
    r"\b(ayuda|help|qué\s*puedes|que\s*puedes|cómo\s*funciona|como\s*funciona|"
    r"qué\s*soportas|que\s*soportas|qué\s*preguntas|que\s*preguntas|"
    r"capacidades|capabilities|qué\s*haces|que\s*haces|para\s*qué\s*sirves|"
    r"para\s*que\s*sirves|qué\s*puedo\s*preguntar|que\s*puedo\s*preguntar)\b",
    re.IGNORECASE,
)
_ABOUT_DATA_RE = re.compile(
    r"\b(háblame|cuéntame|qué\s*datos|cuáles\s*datos|sobre\s*la\s*data|de\s*qué\s*trata|"
    r"qué\s*información\s*tenemos|qué\s*métricas\s*tenemos|qué\s*data|explica.*data|"
    r"describe.*dataset|qué\s*cubre|qué\s*tiene.*data|qué\s*contiene.*data|"
    r"data\s*que\s*tenemos|datos\s*que\s*tenemos|dataset)\b",
    re.IGNORECASE,
)
_EXPLAIN_RE = re.compile(
    r"\b(explícame|explica\s*esto|qué\s*significa\s*(esto|eso|este\s+\w+)|por\s*qué\s*importa|"
    r"qué\s*quiere\s*decir|qué\s*implica|cómo\s*lo\s*interpreto|"
    r"qué\s*tan\s*grave|dime\s*más\s*sobre|amplía|profundiza|detalla|"
    r"explica\s*el\s*resultado|explica\s*el\s*hallazgo)\b",
    re.IGNORECASE,
)
# "qué significa Perfect Orders" / "explícame Turbo Adoption"
_EXPLAIN_METRIC_RE = re.compile(
    r"\b(qué\s*(es|significa|mide)|explícame|cuéntame\s*sobre|cómo\s*se\s*calcula|"
    r"cómo\s*interpreto|qué\s*quiere\s*decir)\s+"
    r"(perfect\s*orders?|turbo\s*adoption|gross\s*profit|pro\s*adoption|"
    r"markdowns?|assortment|atc\s*cvr|sst\s*cvr|mltv|breakeven|lead\s*penetration|"
    r"non.?pro\s*ptc|non_pro_ptc|esta\s*métrica|las?\s*métricas?)\b",
    re.IGNORECASE,
)
# "qué significa value" / "qué es n_zones" / "explícame la evidencia"
_EXPLAIN_TABLE_RE = re.compile(
    r"\b(qué\s*(es|son|significa|significan)|para\s*qué\s*sirve[ns]?|explícame|qué\s*quiere\s*decir)\s+"
    r"(value|n_zones|n\s*zones|confidence|confidence_level|peer|peer_group|severity|"
    r"severity_score|delta|la\s*evidencia|la\s*tabla|estas?\s*columnas?|"
    r"estos?\s*números?)\b",
    re.IGNORECASE,
)
_EXPLAIN_TABLE_GENERIC_RE = re.compile(
    r"\b(qué\s*significa\s*(esa|esta|la)?\s*tabla|explícame\s*(esa|esta|la)?\s*tabla|"
    r"qué\s*significa\s*(esa|esta|la)?\s*evidencia|tradúceme\s*(esa|esta|la)?\s*evidencia)\b",
    re.IGNORECASE,
)
_EXPLAIN_SEGMENTS_RE = re.compile(
    r"\b("
    r"(wealthy\s+y\s+non\s*wealthy|wealthy|non\s*wealthy|zonas?\s*wealthy|zonas?\s*non\s*wealthy|"
    r"categor[ií]as?|segmentos?)\b.*(expl[ií]came|expl[ií]camelos?|cu[aá]l\s*es\s*la\s*diferencia|"
    r"qu[eé]\s*significan|qu[eé]\s*son|qu[eé]\s*es|qu[eé]\s*son\s*esas|qu[eé]\s*significa)"
    r"|"
    r"(expl[ií]came|expl[ií]camelos?|cu[aá]l\s*es\s*la\s*diferencia|qu[eé]\s*significan|qu[eé]\s*son|qu[eé]\s*es)"
    r".*(wealthy\s+y\s+non\s*wealthy|wealthy|non\s*wealthy|zonas?\s*wealthy|zonas?\s*non\s*wealthy|"
    r"categor[ií]as?|segmentos?)"
    r")\b",
    re.IGNORECASE,
)
_AVAILABLE_METRICS_RE = re.compile(
    r"\b(qué\s*métricas\s*(tenemos|hay|están|existen)|indicadores\s*disponibles|"
    r"con\s*qué\s*métricas\s*puedo\s*medir|qué\s*puedo\s*medir|"
    r"métricas\s*para\s*\w+|métricas\s*que\s*tenemos|qué\s*métricas\s*hay\s*para)\b",
    re.IGNORECASE,
)
_EXPLAIN_SIGNALS_RE = re.compile(
    r"\b(qué\s*significan\s*estas\s*señales|qué\s*significan\s*las\s*señales|"
    r"explícame\s*estas\s*señales|explícame\s*las\s*señales|por\s*qué\s*son\s*alertas|"
    r"qué\s*me\s*está\s*diciendo\s*esto|qué\s*me\s*dice\s*esto|qué\s*dice\s*esto|"
    r"qué\s*está\s*diciendo\s*esto)\b",
    re.IGNORECASE,
)
_EXPLAIN_RESULT_SIMPLE_RE = re.compile(
    r"\b(explícamelo\s*mejor|explícamelo|en\s*palabras\s*simples|qué\s*significa\s*eso|"
    r"qué\s*significa\s*esto|por\s*qué\s*importa|tradúceme\s*esa\s*evidencia|"
    r"explícalo\s*simple|más\s*simple|en\s*simple|resume\s*esto)\b",
    re.IGNORECASE,
)
_SCOPE_SWITCH_RE = re.compile(
    r"\b(y\s+en\s+(colombia|méxico|mexico|brasil|brazil|argentina|chile|perú|peru|ecuador|uruguay|costa\s*rica)|"
    r"y\s+en\s+(wealthy|non\s*wealthy)|y\s+solo\s+en\s+\w+|solo\s+en\s+\w+|"
    r"y\s+si\s*miro\s+(wealthy|non\s*wealthy)|cambia\s+a\s+\w+)\b",
    re.IGNORECASE,
)

# Terminal intents — no tool call, no state inheritance, clean plans
_TERMINAL_INTENTS = {
    "greeting", "help", "no_intent", "about_data",
    "explain_result", "explain_metric", "explain_table", "no_intent_guided",
    "clarify_metric", "clarify_country_scope",
    "explain_segments", "available_metrics", "available_metrics_for_scope",
    "explain_signals", "explain_result_simple",
}

_CLEAN_PLAN_BASE = {
    "metric": None,
    "entity_scope": {"country": None, "city": None, "zone": None},
    "time_window": "L0W",
    "top_n": 5,
}


def _is_explain_metric(text: str) -> bool:
    return bool(_EXPLAIN_METRIC_RE.search(text))


def _is_explain_table(text: str) -> bool:
    return bool(_EXPLAIN_TABLE_RE.search(text))


def _is_greeting(text: str) -> bool:
    return bool(_GREETING_RE.match(text) or _VAGUE_RE.match(text) or _GREETING_CONVERSATIONAL_RE.match(text))


def _is_help(text: str) -> bool:
    return bool(_HELP_RE.search(text))


def _is_about_data(text: str) -> bool:
    return bool(_ABOUT_DATA_RE.search(text))


def _is_explain(text: str) -> bool:
    return bool(_EXPLAIN_RE.search(text))


def _is_too_short(text: str) -> bool:
    return len(text.strip()) < 4


def _is_vague_country_scope(text: str) -> bool:
    return bool(_VAGUE_COUNTRY_SCOPE_RE.search(text))


def _has_context(state) -> bool:
    return bool(state and (state.last_intent or state.last_metric_id or state.last_top_insight or state.last_compare_result))


# ── keyword maps ─────────────────────────────────────────────────────────────

_RANK_KW = r"\b(top|ranking|rank|mejor|peor|mejores|peores|mayor|menor|más alto|más bajo|máximo|mínimo|cuál.*más|cuáles.*más)\b"
_COMPARE_KW = r"\b(compar|versus|vs\.?|diferencia|contra|wealthy.*(non|no)\s*wealthy|(non|no)\s*wealthy.*wealthy|segmento|tipo de zona)\b"
_TREND_KW = r"\b(tendencia|trend|evolución|evoluciona|semanas|histórico|últimas.*semanas|cómo.*ha.*cambiado|L\dW)\b"
_INSIGHT_KW = r"\b(insight|problema|alert|alerta|qué.*pasa|qué.*tiene|situación|estado|reporte|resumen|issues)\b"
_HYPOTHESIS_KW = r"\b(hipótesis|hypothesis|explica|driver|causa|razón|por qué|podría.*ser|qué.*podría|asocia)\b"
_FOLLOWUP_SCOPE_KW = r"\b(solo en|solo para|ahora en|pero en|filtra|cambia.*a|en colombia|en méxico|en brasil|en argentina|en chile|en perú|en ecuador|en uruguay)\b"
_FOLLOWUP_VIZ_KW = r"\b(muestr.*gráfico|muéstramelo|en gráfico|visualiz|chart|gráfica|ahora.*gráfico)\b"
_QUERY_KW = r"\b(cuánto|cuál.*valor|dame el|promedio|mediana|agregado|aggregate|valor de)\b"
_VAGUE_COUNTRY_SCOPE_RE = re.compile(
    r"\b(qué\s*está\s*pasando|que\s*esta\s*pasando|qué\s*pasa|que\s*pasa|"
    r"qué\s*señales\s*hay|que\s*señales\s*hay|qué\s*está\s*sucediendo|"
    r"que\s*esta\s*sucediendo|cómo\s*va|como\s*va)\b",
    re.IGNORECASE,
)

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

_VALID_INTENTS: set[str] = {
    "rank", "compare", "trend", "insight_request", "hypothesis_request",
    "follow_up_scope_refine", "follow_up_visualization", "query", "scope_switch",
    "greeting", "help", "no_intent", "about_data",
    "explain_result", "explain_metric", "explain_table", "no_intent_guided",
    "clarify_metric", "clarify_country_scope",
    "explain_segments", "available_metrics", "available_metrics_for_scope",
    "explain_signals", "explain_result_simple",
}


# ── Phase 1: keyword router ───────────────────────────────────────────────────

def _terminal_plan(intent: str, text: str, extra: dict | None = None) -> dict:
    """Clean, context-free plan for non-analytical intents."""
    plan = {"intent": intent, **_CLEAN_PLAN_BASE, "_raw_text": text, "_planner_source": "keyword"}
    if extra:
        plan.update(extra)
    return plan


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
    """
    Keyword-based classification. Always succeeds.
    Terminal intents checked first — safe fallback default is no_intent_guided, NOT insight_request.
    """
    # ── terminal / UX intents ─────────────────────────────────────────────────
    if _is_greeting(text) or _is_too_short(text):
        return _terminal_plan("greeting", text)
    if _is_help(text):
        return _terminal_plan("help", text)
    if _is_about_data(text):
        return _terminal_plan("about_data", text)
    if _is_explain_table(text):
        plan = _terminal_plan("explain_table", text)
        if state:
            plan["_explain_context"] = {
                "last_result_type": state.last_visualization,
                "last_intent": state.last_intent,
            }
        return plan
    if _EXPLAIN_TABLE_GENERIC_RE.search(text):
        plan = _terminal_plan("explain_table", text)
        if state:
            plan["_explain_context"] = {
                "last_result_type": state.last_visualization,
                "last_intent": state.last_intent,
            }
        return plan
    if _EXPLAIN_SEGMENTS_RE.search(text):
        return _terminal_plan("explain_segments", text)
    if _AVAILABLE_METRICS_RE.search(text):
        country = _extract_country(text)
        intent = "available_metrics_for_scope" if country else "available_metrics"
        plan = _terminal_plan(intent, text)
        if country:
            plan["entity_scope"] = {"country": country, "city": None, "zone": None}
        return plan
    if _EXPLAIN_SIGNALS_RE.search(text):
        plan = _terminal_plan("explain_signals", text)
        if state:
            plan["_signal_context"] = {
                "last_insight": state.last_top_insight,
                "last_metric": state.last_metric_id,
                "last_metric_display": state.last_metric_display,
                "last_entity": dict(state.last_entity),
                "last_intent": state.last_intent,
                "last_summary_text": state.last_summary_text,
                "last_compare_result": state.last_compare_result,
                "last_trend_result": state.last_trend_result,
                "last_result_type": state.last_result_type,
            }
        return plan
    if _EXPLAIN_RESULT_SIMPLE_RE.search(text):
        plan = _terminal_plan("explain_result_simple", text)
        if state:
            plan["_explain_context"] = {
                "last_insight": state.last_top_insight,
                "last_metric": state.last_metric_id,
                "last_metric_display": state.last_metric_display,
                "last_entity": dict(state.last_entity),
                "last_intent": state.last_intent,
                "last_compare_result": state.last_compare_result,
                "last_trend_result": state.last_trend_result,
                "last_result_type": state.last_result_type,
                "last_summary_text": state.last_summary_text,
            }
        return plan
    if _is_explain_metric(text):
        plan = _terminal_plan("explain_metric", text)
        metric_id = _extract_metric(text)
        plan["_metric_to_explain"] = metric_id or (state.last_metric_id if state else None)
        return plan
    if _is_explain(text):
        plan = _terminal_plan("explain_result", text)
        if state:
            plan["_explain_context"] = {
                "last_insight": state.last_top_insight,
                "last_metric": state.last_metric_id,
                "last_metric_display": state.last_metric_display,
                "last_entity": dict(state.last_entity),
                "last_intent": state.last_intent,
                "last_compare_result": state.last_compare_result,
                "last_trend_result": state.last_trend_result,
                "last_result_type": state.last_result_type,
            }
        return plan

    # ── analytical intent detection ───────────────────────────────────────────
    t_lower = text.lower()

    if re.search(_FOLLOWUP_VIZ_KW, t_lower):
        intent = "follow_up_visualization"
    elif re.search(_SCOPE_SWITCH_RE, t_lower) and state and _has_context(state):
        intent = "scope_switch"
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
        # SAFE FALLBACK — vague text → guided non-analytical, not insight_request
        intent = "no_intent_guided"

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
        "_planner_source": "keyword",
    }

    if intent == "compare" and zone_type:
        plan["comparison"] = {
            "segment_a": zone_type,
            "segment_b": "Non Wealthy" if zone_type == "Wealthy" else "Wealthy",
            "dimension": "ZONE_TYPE",
        }
    elif intent == "compare":
        plan["comparison"] = {"segment_a": "Wealthy", "segment_b": "Non Wealthy", "dimension": "ZONE_TYPE"}

    # Country-level open questions ("qué está pasando en CO") are underspecified.
    if intent == "insight_request" and country and not metric and _is_vague_country_scope(text):
        plan["intent"] = "clarify_country_scope"
        plan["requires_clarification"] = True
        plan["clarification_question"] = (
            "¿Quieres ver ranking de zonas, señales/insights o comparación Wealthy vs Non Wealthy?"
        )

    return plan


# ── Phase 2: Gemini planner ───────────────────────────────────────────────────

def _build_gemini_client():
    if not LLM_ACTIVE:
        return None
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY)
    except Exception as exc:
        logger.warning("Gemini client init failed: %s", exc)
        return None


_gemini_client = None


def _get_gemini_client():
    global _gemini_client
    if _gemini_client is None:
        _gemini_client = _build_gemini_client()
    return _gemini_client


def _validate_llm_output(raw: dict, metric_ids: list[str]) -> tuple[bool, str]:
    if not isinstance(raw, dict):
        return False, "not a dict"
    intent = raw.get("intent")
    if intent not in _VALID_INTENTS:
        return False, f"invalid intent '{intent}'"
    metric = raw.get("metric")
    if metric is not None and metric not in metric_ids:
        return False, f"unknown metric '{metric}'"
    country = (raw.get("entity_scope") or {}).get("country")
    if country not in {"AR", "BR", "CL", "CO", "CR", "EC", "MX", "PE", "UY", None}:
        return False, f"invalid country '{country}'"
    tw = raw.get("time_window", "L0W")
    if tw not in {"L0W", "L1W", "L2W", "L3W", "L4W", "L8W"}:
        return False, f"invalid time_window '{tw}'"
    return True, "ok"


def _gemini_classify(text: str, artifacts: dict) -> tuple[dict | None, bool, str]:
    """
    Returns (plan_or_None, llm_attempted, error_reason). Never raises.
    Uses concurrent.futures for timeout — thread-safe, works inside Streamlit.
    (signal.SIGALRM not used — fails in non-main threads.)
    """
    if (_is_greeting(text) or _is_help(text) or _is_about_data(text)
            or _is_explain(text) or _is_explain_metric(text) or _is_explain_table(text)
            or _EXPLAIN_SEGMENTS_RE.search(text) or _AVAILABLE_METRICS_RE.search(text)
            or _EXPLAIN_SIGNALS_RE.search(text) or _EXPLAIN_RESULT_SIMPLE_RE.search(text)
            or _is_too_short(text)):
        return None, False, "terminal_shortcircuit"

    client = _get_gemini_client()
    if client is None:
        return None, False, "no_client"

    from app.reto1.prompts import PLANNER_SYSTEM, PLANNER_USER
    metric_ids = [m["id"] for m in artifacts["metrics_cfg"]["metrics"]]
    full_prompt = (
        PLANNER_SYSTEM.format(metric_ids=", ".join(metric_ids))
        + "\n\n"
        + PLANNER_USER.format(text=text)
    )

    try:
        # thread-safe timeout — works in any thread including Streamlit workers
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                client.models.generate_content,
                model=GEMINI_MODEL,
                contents=full_prompt,
            )
            try:
                response = future.result(timeout=LLM_TIMEOUT_SECONDS)
            except concurrent.futures.TimeoutError:
                return None, True, f"timeout:{LLM_TIMEOUT_SECONDS}s"

        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            raw_text = re.sub(r"^```[a-z]*\n?", "", raw_text)
            raw_text = re.sub(r"\n?```$", "", raw_text)

        parsed = json.loads(raw_text)
        ok, reason = _validate_llm_output(parsed, metric_ids)
        if not ok:
            return None, True, f"invalid_output:{reason}"

        comp = parsed.get("comparison") or {}
        plan = {
            "intent": parsed["intent"],
            "metric": parsed.get("metric"),
            "entity_scope": parsed.get("entity_scope") or {"country": None, "city": None, "zone": None},
            "time_window": parsed.get("time_window", "L0W"),
            "top_n": int(parsed.get("top_n") or 5),
            "_raw_text": text,
            "_planner_source": "gemini",
            "_gemini_raw": parsed,
        }

        if parsed["intent"] == "compare":
            plan["comparison"] = {
                "segment_a": comp.get("segment_a") or "Wealthy",
                "segment_b": comp.get("segment_b") or "Non Wealthy",
                "dimension": "ZONE_TYPE",
            }

        if parsed.get("requires_clarification"):
            plan["requires_clarification"] = True
            plan["clarification_question"] = parsed.get("clarification_question")

        return plan, True, "ok"

    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        return None, True, f"parse_error:{exc}"
    except Exception as exc:
        return None, True, f"exception:{type(exc).__name__}:{exc}"


# ── validation ────────────────────────────────────────────────────────────────

def validate_plan(plan: dict, artifacts: dict) -> dict:
    metric = plan.get("metric")
    intent = plan.get("intent")

    if intent in _TERMINAL_INTENTS:
        return {"valid": True, "action": intent, "reason": "ok", "suggestion": "", "adjusted_plan": plan}

    if intent not in _VALID_INTENTS:
        return {"valid": False, "action": "reject", "reason": f"Intent '{intent}' not supported",
                "suggestion": "Reformula como ranking, comparación o insight.", "adjusted_plan": plan}

    requires_metric_intents = {"rank", "compare", "trend", "query"}
    if intent in requires_metric_intents and not metric:
        clarified = {
            **plan,
            "intent": "clarify_metric",
            "requires_clarification": True,
            "clarification_question": (
                "Puedo medir desempeño de varias formas. "
                "¿Quieres verlo por Perfect Orders, Gross Profit UE, Turbo Adoption o Pro Adoption?"
            ),
        }
        return {
            "valid": True,
            "action": "clarify",
            "reason": "missing_metric",
            "suggestion": "Selecciona una métrica para continuar.",
            "adjusted_plan": clarified,
        }

    if intent == "insight_request":
        raw_text = str(plan.get("_raw_text", ""))
        country = (plan.get("entity_scope") or {}).get("country")
        if country and not metric and _is_vague_country_scope(raw_text):
            clarified = {
                **plan,
                "intent": "clarify_country_scope",
                "requires_clarification": True,
                "clarification_question": (
                    "¿Quieres ver ranking de zonas, señales/insights o comparación Wealthy vs Non Wealthy?"
                ),
            }
            return {
                "valid": True,
                "action": "clarify",
                "reason": "vague_country_scope",
                "suggestion": "Elige el tipo de análisis para ese país.",
                "adjusted_plan": clarified,
            }

    if metric in SUSPENDED_METRICS:
        return {"valid": False, "action": "reject",
                "reason": "lead_penetration suspendida — definición pendiente con equipo de datos.",
                "suggestion": "Prueba con perfect_orders o gross_profit_ue.", "adjusted_plan": plan}

    scope = plan.get("entity_scope", {})
    if scope.get("zone") and not scope.get("country"):
        plan = {**plan, "requires_clarification": True}
        return {"valid": False, "action": "clarify",
                "reason": "ZONE solo no es único — necesito COUNTRY + CITY.",
                "suggestion": "¿En qué país/ciudad está esa zona?", "adjusted_plan": plan}

    if intent == "hypothesis_request":
        plan = {**plan, "_non_causal_mode": True, "_add_association_caveat": True}

    if metric:
        for m in artifacts.get("metrics_cfg", {}).get("metrics", []):
            if m["id"] == metric and m.get("direction_confidence") == "provisional":
                plan = {**plan, "_add_provisional_caveat": True}
                break

    return {"valid": True, "action": "execute", "reason": "ok", "suggestion": "", "adjusted_plan": plan}


# ── main entry ────────────────────────────────────────────────────────────────

def build_plan(text: str, artifacts: dict, state=None) -> dict:
    """
    Planner chain:
      1. Try Gemini (if LLM_ACTIVE, not terminal)
      2. Keyword fallback (safe — defaults to no_intent_guided, not insight_request)
    Debug keys: _planner_source, _llm_attempted, _llm_error, _planner_fallback.
    """
    llm_attempted = False
    llm_error = ""

    if LLM_ACTIVE:
        plan, llm_attempted, llm_error = _gemini_classify(text, artifacts)
    else:
        plan = None

    used_fallback = plan is None
    if plan is None:
        plan = classify_intent(text, state)
        if used_fallback and llm_attempted:
            plan["_planner_source"] = "safe_fallback"

    plan["_llm_attempted"] = llm_attempted
    plan["_llm_error"] = llm_error if llm_error != "ok" else ""
    if used_fallback and llm_attempted:
        plan["_planner_fallback"] = True

    # ensure explain intents have context (keyword path sets it; Gemini path may not)
    if plan.get("intent") == "explain_result" and state and not plan.get("_explain_context"):
        plan["_explain_context"] = {
            "last_insight": state.last_top_insight,
            "last_metric": state.last_metric_id,
            "last_metric_display": state.last_metric_display,
            "last_entity": dict(state.last_entity),
            "last_intent": state.last_intent,
            "last_compare_result": state.last_compare_result,
            "last_trend_result": state.last_trend_result,
            "last_result_type": state.last_result_type,
        }
    if plan.get("intent") == "explain_metric" and state and not plan.get("_metric_to_explain"):
        plan["_metric_to_explain"] = state.last_metric_id
    if plan.get("intent") == "explain_table" and state and not plan.get("_explain_context"):
        plan["_explain_context"] = {
            "last_result_type": state.last_visualization,
            "last_intent": state.last_intent,
        }

    if state and _SCOPE_SWITCH_RE.search(str(plan.get("_raw_text", text))) and _has_context(state):
        from app.reto1.state import apply_scope_switch
        plan = apply_scope_switch(state, plan)

    # follow-up context inheritance
    if state and plan.get("intent") in ("follow_up_scope_refine", "follow_up_visualization", "scope_switch"):
        from app.reto1.state import apply_follow_up, apply_scope_switch
        if plan.get("intent") == "scope_switch":
            plan = apply_scope_switch(state, plan)
        else:
            plan = apply_follow_up(state, plan)

    validation = validate_plan(plan, artifacts)
    if not validation["valid"]:
        return {
            **plan,
            "_validation": validation,
            "_error": validation["reason"],
            "_suggestion": validation["suggestion"],
        }

    return {**validation["adjusted_plan"], "_validation": validation}
