"""Build UI response from tool results.

Applies language guards from NB40 contracts.
"""
from __future__ import annotations
import re

_CAUSAL_TERMS = re.compile(
    r"\b(causa|provoca|genera|determina|impacto directo|efecto causal|demuestra que)\b",
    re.IGNORECASE
)

_FOLLOWUP_TEMPLATES = {
    "rank": [
        "¿Ver tendencia de la métrica líder en las últimas 8 semanas?",
        "¿Comparar Wealthy vs Non Wealthy para esta métrica?",
        "¿Filtrar por un país específico?",
    ],
    "compare": [
        "¿Ver tendencia de cada segmento en las últimas 8 semanas?",
        "¿Filtrar solo zonas High Priority?",
        "¿Ver en otro país?",
    ],
    "trend": [
        "¿Ver ranking de zonas para esta métrica?",
        "¿Comparar con otro país?",
        "¿Qué hipótesis podrían explicar esta tendencia?",
    ],
    "insight_request": [
        "¿Ver detalle de la zona con mayor alerta?",
        "¿Filtrar por métrica específica?",
        "¿Qué podría explicar los hallazgos?",
    ],
    "hypothesis_request": [
        "¿Ver ranking de zonas para la métrica asociada?",
        "¿Explorar tendencia temporal?",
        "¿Ver insights de otras zonas?",
    ],
    "query": [
        "¿Ver el ranking de zonas para esta métrica?",
        "¿Cómo ha evolucionado en las últimas semanas?",
        "¿Comparar Wealthy vs Non Wealthy?",
    ],
}


def apply_direction_guard(text: str, metric: str | None, metrics_cfg: dict) -> str:
    if not metric:
        return text
    for m in metrics_cfg.get("metrics", []):
        if m["id"] == metric and m.get("direction_confidence") == "provisional":
            note = f" *(dirección provisional — no validada con negocio)*"
            if note not in text:
                text = text + note
    return text


def apply_hypothesis_guard(text: str) -> str:
    if _CAUSAL_TERMS.search(text):
        text = _CAUSAL_TERMS.sub("se asocia con", text)
    return text


def _build_answer_short(plan: dict, result: dict) -> str:
    intent = plan.get("intent", "insight_request")
    metric = result.get("metric_display_name", plan.get("metric") or "la métrica")
    country = (plan.get("entity_scope") or {}).get("country") or "todos los países"

    if result.get("error"):
        return f"No se pudo completar la consulta: {result['error']}"

    if intent == "rank":
        n = len(result.get("rows", []))
        asc_note = "menor a mayor" if result.get("ascending") else "mayor a menor"
        return f"Top {n} zonas por **{metric}** ({asc_note}) en {country}, semana {plan.get('time_window','L0W')}."

    if intent == "compare":
        seg_a = result.get("segment_a", {})
        seg_b = result.get("segment_b", {})
        delta = result.get("delta")
        delta_str = f" (+{delta:.3f})" if delta and delta > 0 else (f" ({delta:.3f})" if delta else "")
        return (
            f"En {country}, zonas **{seg_a.get('name')}** tienen mediana de "
            f"**{metric}** = {seg_a.get('value'):.3f} vs {seg_b.get('value'):.3f} en "
            f"{seg_b.get('name')}{delta_str}."
        )

    if intent == "trend":
        rows = result.get("rows", [])
        n = result.get("n_weeks", 0)
        scope = result.get("scope", {})
        scope_str = scope.get("country") or "todos los países"
        latest = rows[-1]["value"] if rows else "N/A"
        return f"Tendencia de **{metric}** en {scope_str}: {n} semanas disponibles. Valor más reciente (L0W): {latest}."

    if intent == "insight_request":
        total = result.get("total_found", 0)
        return f"{total} insights curados encontrados para los filtros seleccionados."

    if intent == "hypothesis_request":
        n = result.get("n_found", 0)
        return f"{n} posibles drivers identificados. Recuerda: son asociaciones, no causas."

    if intent == "query":
        val = result.get("value")
        n_zones = result.get("n_zones", 0)
        return f"Mediana de **{metric}** en {country}: **{val}** (n={n_zones} zonas)."

    return "Consulta procesada."


def _build_headline(plan: dict, result: dict) -> str | None:
    intent = plan.get("intent", "")
    if intent == "compare":
        seg_a = result.get("segment_a", {})
        seg_b = result.get("segment_b", {})
        delta = result.get("delta")
        mn = result.get("metric_display_name", "")
        va, vb = seg_a.get("value"), seg_b.get("value")
        if delta is not None and va is not None and vb is not None:
            sign = "+" if delta > 0 else ""
            return f"{mn}: {seg_a.get('name')}={va:.3f} vs {seg_b.get('name')}={vb:.3f} ({sign}{delta:.3f})"
    if intent == "query":
        mn = result.get("metric_display_name", "")
        v = result.get("value")
        return f"{mn}: {v}" if v is not None else None
    if intent == "rank" and result.get("rows"):
        top = result["rows"][0]
        mn = result.get("metric_display_name", "")
        return f"#{1} {top.get('ZONE','?')} ({top.get('COUNTRY','?')}) — {mn}: {top.get('VALUE',0):.3f}"
    return None


def _build_chart_spec(plan: dict, result: dict) -> dict | None:
    chart_type = result.get("chart_type")
    if not chart_type or chart_type in ("ranked_table", "kpi_card", None):
        return None

    mn = result.get("metric_display_name", "")
    country = (plan.get("entity_scope") or {}).get("country") or ""
    week = plan.get("time_window", "L0W")

    if chart_type == "side_by_side_bar":
        rows = result.get("rows", [])
        return {
            "chart_type": "side_by_side_bar",
            "x_values": [r["segment"] for r in rows],
            "y_values": [r["value"] for r in rows],
            "annotations": [{"x": r["segment"], "label": f"n={r['n_zones']}"} for r in rows],
            "title": f"{mn}: Wealthy vs Non Wealthy — {country} {week}",
        }

    if chart_type == "line_chart":
        rows = result.get("rows", [])
        scope = result.get("scope", {})
        label = scope.get("country") or "All"
        return {
            "chart_type": "line_chart",
            "x_values": [r["week"] for r in rows],
            "y_values": [r["value"] for r in rows],
            "series_labels": [f"{mn} — {label}"],
            "title": f"Tendencia {mn} — {label}",
        }

    return None


def build_response(plan: dict, result: dict, artifacts: dict) -> dict:
    intent = plan.get("intent", "insight_request")
    metric = plan.get("metric")
    metrics_cfg = artifacts.get("metrics_cfg", {})

    # base answer
    answer = _build_answer_short(plan, result)

    # language guards
    if plan.get("_non_causal_mode"):
        answer = apply_hypothesis_guard(answer)
    answer = apply_direction_guard(answer, metric, metrics_cfg)

    # headline
    headline = _build_headline(plan, result)

    # evidence table
    rows = result.get("rows", [])[:10]

    # chart
    chart_spec = _build_chart_spec(plan, result)
    if plan.get("intent") == "follow_up_visualization" and not chart_spec:
        # try to generate from last tool result shape
        chart_spec = None  # would need last result — handled in app.py

    # caveat — provisional direction already in tool caveat; only add association here
    caveats = []
    if result.get("caveat"):
        caveats.append(result["caveat"])
    if plan.get("_add_association_caveat"):
        caveats.append("Asociación estadística, no causalidad. No inferir relación causal.")
    caveat_text = " | ".join(dict.fromkeys(caveats)) if caveats else None

    # followups
    followups = _FOLLOWUP_TEMPLATES.get(intent, _FOLLOWUP_TEMPLATES["insight_request"])[:3]

    validation = plan.get("_validation", {})

    return {
        "answer_short": answer,
        "headline_metric": headline,
        "supporting_evidence": rows,
        "filters_used": {
            "country": (plan.get("entity_scope") or {}).get("country"),
            "metric": metric,
            "week": plan.get("time_window", "L0W"),
            "intent": intent,
        },
        "chart_spec": chart_spec,
        "caveat": caveat_text,
        "suggested_followups": followups,
        "intent_classified": intent,
        "tool_calls_made": [result.get("tool", "unknown")],
        "debug_meta": {
            "plan": {k: v for k, v in plan.items() if not k.startswith("_raw")},
            "validation_result": validation,
            "tool_error": result.get("error"),
        },
    }
