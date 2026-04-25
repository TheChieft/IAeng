"""Build UI response from tool results.

Applies language guards from NB40 contracts.
suggested_followups is list[dict] with keys: label (display), action (action_type for app.py).
"""
from __future__ import annotations
import re

_CAUSAL_TERMS = re.compile(
    r"\b(causa|provoca|genera|determina|impacto directo|efecto causal|demuestra que)\b",
    re.IGNORECASE,
)

_ALL_TERMINAL_INTENTS = {
    "greeting", "help", "no_intent", "about_data",
    "explain_result", "explain_metric", "explain_table", "no_intent_guided",
}


# ── plain-language column glossary ───────────────────────────────────────────
# Values written for a non-technical business reader.

_COLUMN_PLAIN: dict[str, str] = {
    "VALUE": "El valor de la métrica para esa zona (mediana del grupo de zonas comparables).",
    "value": "El valor de la métrica para ese segmento o semana (mediana).",
    "n_zones": "Cuántas zonas forman ese grupo. Más zonas = resultado más confiable.",
    "confidence_level": (
        "Qué tan confiable es el resultado: "
        "**reliable** = grupo grande (10+ zonas), **low_confidence** = pocas zonas, tomar con cautela."
    ),
    "rank": "Posición relativa de la zona: 1 = la que mejor se desempeña en esa métrica.",
    "ZONE": "Nombre de la zona Rappi.",
    "COUNTRY": "País (AR = Argentina, BR = Brasil, CO = Colombia, MX = México, etc.).",
    "CITY": "Ciudad donde está la zona.",
    "ZONE_TYPE": (
        "Tipo de zona por nivel socioeconómico: "
        "**Wealthy** = zona de mayor poder adquisitivo, **Non Wealthy** = las demás."
    ),
    "delta": "Diferencia entre los dos grupos comparados. Positivo = el primero supera al segundo.",
    "severity_score": (
        "Qué tan urgente es la alerta: "
        "🔴 ≥0.7 = atención inmediata · 🟡 ≥0.4 = monitorear · 🟢 <0.4 = baja prioridad."
    ),
    "week": "Semana relativa: **L0W** = semana más reciente, **L8W** = hace 8 semanas.",
    "summary_text": "Descripción automática del hallazgo generada por el sistema de insights.",
    "segment": "Nombre del grupo en la comparación (Wealthy o Non Wealthy).",
    "display_entity": "Identificación completa de la zona: País | Ciudad | Zona.",
    "metric_display_name": "Nombre de la métrica analizada.",
}

_COLS_BY_CONTEXT: dict[str, list[str]] = {
    "ranked_table": ["VALUE", "rank", "ZONE", "CITY", "COUNTRY", "ZONE_TYPE"],
    "side_by_side_bar": ["value", "n_zones", "confidence_level", "delta", "segment", "ZONE_TYPE"],
    "line_chart": ["week", "value"],
    "kpi_card": ["VALUE", "n_zones"],
    "rank": ["VALUE", "rank", "ZONE", "CITY", "COUNTRY", "ZONE_TYPE"],
    "compare": ["value", "n_zones", "confidence_level", "delta", "segment", "ZONE_TYPE"],
    "trend": ["week", "value"],
    "insight_request": ["display_entity", "metric_display_name", "summary_text", "severity_score"],
    "hypothesis_request": ["display_entity", "metric_display_name", "summary_text"],
}


# ── helpers ───────────────────────────────────────────────────────────────────

def _diff_magnitude(delta: float | None, reference: float | None) -> str:
    if delta is None or reference is None or reference == 0:
        return "difícil de cuantificar sin más contexto"
    pct = abs(delta / reference * 100)
    if pct >= 15:
        return "grande"
    elif pct >= 7:
        return "moderada"
    elif pct >= 3:
        return "pequeña"
    else:
        return "muy pequeña"


def _trend_consistency(rows: list[dict]) -> str:
    if len(rows) < 3:
        return "con datos limitados"
    overall = rows[-1]["value"] - rows[0]["value"]
    if overall == 0:
        return "sin cambio"
    against = sum(
        1 for i in range(1, len(rows))
        if (rows[i]["value"] - rows[i - 1]["value"]) * overall < 0
    )
    ratio = against / (len(rows) - 1)
    if ratio <= 0.2:
        return "de forma consistente"
    elif ratio <= 0.45:
        return "con algunas oscilaciones"
    else:
        return "de forma irregular"


# ── follow-up action catalog — natural language labels ────────────────────────

_FOLLOWUP_ACTIONS: dict[str, list[dict]] = {
    "rank": [
        {"label": "¿Se mantiene esto en el tiempo?", "action": "trend_for_last_metric"},
        {"label": "¿Hay diferencia entre zonas ricas y otras?", "action": "compare_current_scope"},
        {"label": "¿Qué podría estar detrás de esto?", "action": "hypothesis_for_last_result"},
    ],
    "compare": [
        {"label": "¿Esta diferencia persiste en el tiempo?", "action": "trend_for_last_metric"},
        {"label": "¿Qué zonas destacan más?", "action": "rank_for_last_metric"},
        {"label": "¿Qué factores podrían explicar esta brecha?", "action": "hypothesis_for_last_result"},
    ],
    "trend": [
        {"label": "¿Qué zonas lideran en este indicador?", "action": "rank_for_last_metric"},
        {"label": "¿Hay diferencia entre zonas ricas y otras?", "action": "compare_current_scope"},
        {"label": "¿Qué factores podrían estar asociados?", "action": "hypothesis_for_last_result"},
    ],
    "insight_request": [
        {"label": "¿Por qué esto es una alerta?", "action": "explain_top_insight"},
        {"label": "¿Esta señal persiste en el tiempo?", "action": "trend_for_last_metric"},
        {"label": "¿Qué factores podrían estar detrás?", "action": "hypothesis_for_last_result"},
    ],
    "hypothesis_request": [
        {"label": "¿Qué zonas tienen peor desempeño?", "action": "rank_for_last_metric"},
        {"label": "¿Cómo ha evolucionado este indicador?", "action": "trend_for_last_metric"},
        {"label": "¿Qué otras señales hay en esta zona?", "action": "insight_for_last_scope"},
    ],
    "query": [
        {"label": "¿Qué zonas destacan en esto?", "action": "rank_for_last_metric"},
        {"label": "¿Cómo ha evolucionado en las últimas semanas?", "action": "trend_for_last_metric"},
        {"label": "¿Hay diferencia entre zonas ricas y otras?", "action": "compare_current_scope"},
    ],
    "greeting": [
        {"label": "Top zonas por Perfect Orders en MX", "action": "example_rank_mx"},
        {"label": "¿Hay diferencia Wealthy vs Non Wealthy en CO?", "action": "example_compare_co"},
        {"label": "¿Qué señales hay en Argentina?", "action": "example_insight_ar"},
    ],
    "help": [
        {"label": "Top zonas por Perfect Orders en MX", "action": "example_rank_mx"},
        {"label": "¿Hay diferencia Wealthy vs Non Wealthy en CO?", "action": "example_compare_co"},
        {"label": "¿Qué señales hay en Argentina?", "action": "example_insight_ar"},
    ],
    "about_data": [
        {"label": "Top zonas por Perfect Orders en MX", "action": "example_rank_mx"},
        {"label": "¿Qué señales hay en Argentina?", "action": "example_insight_ar"},
        {"label": "¿Hay diferencia Wealthy vs Non Wealthy en CO?", "action": "example_compare_co"},
    ],
    "explain_result": [
        {"label": "¿Cómo ha evolucionado este indicador?", "action": "trend_for_last_metric"},
        {"label": "¿Qué factores podrían estar asociados?", "action": "hypothesis_for_last_result"},
        {"label": "¿Qué otras señales hay en esta zona?", "action": "insight_for_last_scope"},
    ],
    "explain_metric": [
        {"label": "¿Qué zonas lideran en {metric}?", "action": "rank_for_last_metric"},
        {"label": "¿Cómo ha evolucionado {metric}?", "action": "trend_for_last_metric"},
        {"label": "¿Hay diferencia entre tipos de zona?", "action": "compare_current_scope"},
    ],
    "explain_table": [
        {"label": "¿Cómo ha evolucionado este resultado?", "action": "trend_for_last_metric"},
        {"label": "¿Qué zona tiene el mejor desempeño?", "action": "rank_for_last_metric"},
        {"label": "¿Qué otras señales hay?", "action": "insight_for_last_scope"},
    ],
    "no_intent_guided": [
        {"label": "Top zonas por Perfect Orders en MX", "action": "example_rank_mx"},
        {"label": "¿Qué señales hay en Argentina?", "action": "example_insight_ar"},
        {"label": "¿Hay diferencia Wealthy vs Non Wealthy en CO?", "action": "example_compare_co"},
    ],
    "no_intent": [
        {"label": "Top zonas por Perfect Orders en MX", "action": "example_rank_mx"},
        {"label": "¿Qué señales hay en Argentina?", "action": "example_insight_ar"},
    ],
}


def _render_followup_label(label: str, metric_display: str | None, country: str | None) -> str:
    label = label.replace("{metric}", metric_display or "la métrica")
    label = label.replace("{country}", country or "el país")
    return label


# ── language guards ───────────────────────────────────────────────────────────

def apply_direction_guard(text: str, metric: str | None, metrics_cfg: dict) -> str:
    if not metric:
        return text
    for m in metrics_cfg.get("metrics", []):
        if m["id"] == metric and m.get("direction_confidence") == "provisional":
            note = "\n\n*Nota: la interpretación de dirección de esta métrica es provisional — no está validada formalmente con el negocio.*"
            if "provisional" not in text:
                text = text + note
    return text


def apply_hypothesis_guard(text: str) -> str:
    return _CAUSAL_TERMS.sub("se asocia con", text) if _CAUSAL_TERMS.search(text) else text


# ── answer builders ───────────────────────────────────────────────────────────

def _build_answer_short(plan: dict, result: dict) -> str:  # noqa: C901
    intent = plan.get("intent", "insight_request")
    metric = result.get("metric_display_name", plan.get("metric") or "la métrica")
    country = (plan.get("entity_scope") or {}).get("country") or "todos los países"

    _EXAMPLE_QUERIES = (
        "- *Top 5 zonas por Perfect Orders en MX*\n"
        "- *¿Hay diferencia entre Wealthy y Non Wealthy en Colombia?*\n"
        "- *¿Qué problemas tiene Argentina?*\n"
        "- *Tendencia de Turbo Adoption en México*\n"
        "- *¿Qué significa Perfect Orders?*"
    )

    if intent == "greeting":
        return (
            "Hola. Soy el asistente de análisis operativo de Rappi. "
            "Puedo ayudarte a explorar métricas por zona, identificar alertas, comparar segmentos y entender tendencias.\n\n"
            "Algunas cosas que puedes preguntarme:\n\n"
            + _EXAMPLE_QUERIES
            + "\n\n¿Por dónde quieres empezar?"
        )

    if intent == "help":
        return (
            "Puedo responder preguntas sobre métricas operativas de zonas Rappi. "
            "Estos son los tipos de consulta que entiendo:\n\n"
            "- **¿Cuáles zonas tienen mejor desempeño?** → ranking por métrica y país\n"
            "- **¿Hay diferencia entre zonas ricas y otras?** → comparación Wealthy vs Non Wealthy\n"
            "- **¿Está mejorando o empeorando?** → tendencia temporal\n"
            "- **¿Qué señales preocupantes hay?** → insights automáticos por zona\n"
            "- **¿Qué podría explicar esto?** → posibles factores asociados (no causas)\n"
            "- **¿Cuál es el valor promedio de X?** → agregado por país\n"
            "- **¿Qué significa Perfect Orders?** → definición de cualquier métrica\n\n"
            "**Países disponibles:** AR, BR, CL, CO, CR, EC, MX, PE, UY.\n\n"
            "**Aviso:** `lead_penetration` está suspendida. "
            "Todas las interpretaciones de dirección son preliminares."
        )

    if intent == "no_intent":
        return (
            "No identifiqué eso como una consulta analítica. "
            "Prueba con algo más concreto, por ejemplo:\n\n"
            + _EXAMPLE_QUERIES
        )

    if intent == "no_intent_guided":
        return (
            "No capté claramente qué quieres explorar. Puedo ayudarte con cosas como:\n\n"
            + _EXAMPLE_QUERIES
            + "\n\nTambién puedes escribir **ayuda** para ver todo lo que puedo hacer."
        )

    if intent == "about_data":
        return (
            "Trabajamos con datos semanales de operaciones de zonas Rappi en **9 países**: "
            "Argentina, Brasil, Chile, Colombia, Costa Rica, Ecuador, México, Perú y Uruguay.\n\n"
            "**Qué miden los datos:** desempeño operativo de cada zona, semana a semana. "
            "Las principales métricas incluyen: Perfect Orders, Gross Profit por usuario, "
            "adopción de suscripciones Pro y Turbo, conversión en restaurantes y retail, y más.\n\n"
            "**Cobertura temporal:** 9 semanas relativas. La semana más reciente es L0W, "
            "la más antigua disponible es L8W. No hay fechas calendario.\n\n"
            "**Cómo se organiza:** cada zona tiene un identificador único País + Ciudad + Zona. "
            "Las zonas se clasifican en Wealthy (mayor poder adquisitivo) y Non Wealthy.\n\n"
            "**Limitaciones importantes:** las interpretaciones de dirección de todas las métricas "
            "son provisionales. `lead_penetration` está suspendida por problemas de definición."
        )

    if intent == "explain_metric":
        metric_def = plan.get("_metric_def")
        if not metric_def:
            metric_id = plan.get("_metric_to_explain")
            if metric_id:
                return (
                    f"No encontré la definición de `{metric_id}` en el catálogo. "
                    "Prueba escribiendo el nombre completo, como *qué significa Perfect Orders*."
                )
            return (
                "No identifiqué una métrica específica. "
                "Prueba con algo como: *¿qué significa Perfect Orders?* o *explícame Turbo Adoption*."
            )
        name = metric_def.get("display_name", "")
        desc = (metric_def.get("description") or "Sin descripción disponible.").strip()
        if len(desc) > 300:
            desc = desc[:300].rsplit(" ", 1)[0] + "…"
        direction = metric_def.get("desired_direction", "unknown")
        direction_map = {
            "higher_is_better": "Cuanto más alta, mejor",
            "lower_is_better": "Cuanto más baja, mejor *(la única métrica con esta dirección)*",
            "depends": "Depende del contexto",
            "unknown_pending_validation": "Aún no definida",
        }
        direction_str = direction_map.get(direction, direction)
        suspended = metric_def.get("validation_status") == "suspended_pending_definition"
        low_cov = metric_def.get("low_coverage_peer_groups", False)

        lines = [f"**{name}**\n", f"{desc}\n"]
        lines.append(f"**¿Más alta o más baja es mejor?** {direction_str}")
        lines.append(f"\n*Esta interpretación es preliminar — no fue validada formalmente con el equipo de negocio.*")
        if suspended:
            lines.append("\n⚠️ **Métrica suspendida** — hay inconsistencias en su definición. No se usa en rankings.")
        if low_cov:
            lines.append("\n⚠️ En algunos países o tipos de zona, el grupo de comparación tiene pocas zonas — los benchmarks pueden ser menos confiables.")
        return "\n".join(lines)

    if intent == "explain_table":
        ctx = plan.get("_explain_context") or {}
        last_result_type = ctx.get("last_result_type")
        last_intent = ctx.get("last_intent")

        context_key = last_result_type or last_intent or ""
        relevant_cols = _COLS_BY_CONTEXT.get(context_key, list(_COLUMN_PLAIN.keys())[:8])

        if not last_result_type and not last_intent:
            lines = ["Estos son los términos que aparecen con más frecuencia en los resultados:\n"]
            for col in ["VALUE", "value", "n_zones", "confidence_level", "delta", "severity_score", "rank", "ZONE_TYPE"]:
                if col in _COLUMN_PLAIN:
                    lines.append(f"- **{col}**: {_COLUMN_PLAIN[col]}")
        else:
            label_article = {
                "ranked_table": "el ranking", "rank": "el ranking",
                "side_by_side_bar": "la comparación", "compare": "la comparación",
                "line_chart": "la tendencia", "trend": "la tendencia",
                "insight_request": "el listado de hallazgos",
            }.get(context_key, "el último resultado")
            lines = [f"En {label_article} que te mostré, las columnas significan:\n"]
            for col in relevant_cols:
                if col in _COLUMN_PLAIN:
                    lines.append(f"- **{col}**: {_COLUMN_PLAIN[col]}")

        lines.append(
            "\n*¿Quieres que explique alguna métrica específica? "
            "Escribe por ejemplo: *¿qué significa Perfect Orders?*.*"
        )
        return "\n".join(lines)

    if intent == "explain_result":
        ctx = plan.get("_explain_context") or {}
        last_insight = ctx.get("last_insight")
        last_metric_display = ctx.get("last_metric_display") or ctx.get("last_metric") or "la métrica"
        last_entity = ctx.get("last_entity") or {}
        ctx_country = last_entity.get("country") or "el país analizado"
        last_intent_prev = ctx.get("last_intent")
        last_result_type = ctx.get("last_result_type")

        if not last_insight and not last_intent_prev:
            return (
                "No tengo un resultado anterior en esta sesión para explicar. "
                "Primero haz una consulta analítica — por ejemplo: *¿Qué problemas tiene Argentina?*"
            )

        # explain compare
        last_compare = ctx.get("last_compare_result")
        if last_compare and last_result_type == "compare":
            seg_a = last_compare.get("segment_a", {})
            seg_b = last_compare.get("segment_b", {})
            mn = last_compare.get("metric_display_name", last_metric_display)
            va, vb = seg_a.get("value"), seg_b.get("value")
            delta = last_compare.get("delta")
            if va is not None and vb is not None:
                winner = seg_a.get("name") if (delta or 0) >= 0 else seg_b.get("name")
                loser = seg_b.get("name") if winner == seg_a.get("name") else seg_a.get("name")
                magnitude = _diff_magnitude(delta, vb)
                conf_a = seg_a.get("confidence_level", "")
                conf_b = seg_b.get("confidence_level", "")
                conf_note = (
                    " Ten en cuenta que el grupo de comparación tiene pocas zonas, "
                    "así que este resultado hay que tomarlo con cautela."
                    if "low_confidence" in (conf_a + conf_b) else ""
                )
                mag_interp = {
                    "grande": "Esto es una diferencia notable — puede reflejar patrones estructurales distintos en oferta, demanda o cobertura.",
                    "moderada": "Es una diferencia real, aunque no extrema. Puede valer la pena investigar si es consistente en el tiempo.",
                    "pequeña": "La diferencia existe pero es pequeña. Puede no tener implicación operativa inmediata.",
                    "muy pequeña": "La diferencia es mínima. Probablemente no tiene implicación operativa relevante.",
                }.get(magnitude, "")
                return (
                    f"El resultado que te mostré compara el desempeño en **{mn}** entre zonas "
                    f"**{seg_a['name']}** y **{seg_b['name']}** en {ctx_country}.\n\n"
                    f"Las zonas **{winner}** tienen mejor desempeño, con una diferencia **{magnitude}** "
                    f"({abs(delta or 0):.3f} puntos de diferencia).\n\n"
                    f"{mag_interp}{conf_note}\n\n"
                    f"*Wealthy = zonas de mayor poder adquisitivo. Non Wealthy = las demás. "
                    f"Esta comparación es sobre el tipo de zona, no sobre el usuario.*"
                )

        # explain trend
        last_trend = ctx.get("last_trend_result")
        if last_trend and last_result_type == "trend":
            rows = last_trend.get("rows", [])
            mn = last_trend.get("metric_display_name", last_metric_display)
            if rows:
                oldest, latest = rows[0]["value"], rows[-1]["value"]
                delta = round(latest - oldest, 4)
                direction_word = "subió" if delta > 0 else ("bajó" if delta < 0 else "se mantuvo estable")
                consistency = _trend_consistency(rows)
                pct = abs(delta / oldest * 100) if oldest else 0
                good_or_bad = "señal positiva" if delta > 0 else ("señal de alerta" if delta < 0 else "sin cambio notorio")
                return (
                    f"La tendencia que te mostré indica que **{mn}** en {ctx_country} "
                    f"**{direction_word}** {consistency} durante las últimas {len(rows)} semanas "
                    f"({pct:.1f}% de cambio).\n\n"
                    f"Desde una perspectiva de negocio, esto es una **{good_or_bad}** — "
                    f"{'el indicador está evolucionando en la dirección esperada.' if delta > 0 else ('puede merecer atención si persiste.' if delta < 0 else 'el indicador se está estabilizando.')}\n\n"
                    f"*Nota: la interpretación de si subir es bueno depende de la dirección de la métrica, "
                    f"que en este caso es provisional.*"
                )

        # explain rank
        if last_result_type == "rank":
            return (
                f"El ranking que te mostré lista las zonas con mejor desempeño en "
                f"**{last_metric_display}** en {ctx_country}.\n\n"
                f"Estar en el tope significa que esa zona tiene el valor más alto de la métrica "
                f"en ese período. Estar al fondo significa el más bajo.\n\n"
                f"Para esta métrica, estar más arriba en el ranking es mejor — "
                f"aunque ten en cuenta que esa interpretación de dirección es preliminar.\n\n"
                f"*Si quieres ver si esa zona mantiene esa posición en el tiempo, "
                f"puedes preguntar por la tendencia.*"
            )

        # explain insight
        if last_insight:
            entity = last_insight.get("display_entity", "")
            summary = str(last_insight.get("summary_text", ""))[:250]
            mn = last_insight.get("metric_display_name", last_metric_display)
            sev = float(last_insight.get("severity_score", 0))
            sev_label = "alta" if sev >= 0.7 else ("media" if sev >= 0.4 else "baja")
            urgency = (
                "Esta señal supera el umbral de alerta crítica — merece atención pronto."
                if sev >= 0.7 else
                "Es una señal de atención media — conviene monitorear si persiste en las próximas semanas."
                if sev >= 0.4 else
                "La señal es de baja severidad — puede ser ruido o una variación menor."
            )
            return (
                f"El hallazgo que te mostré es sobre **{mn}** en **{entity}**.\n\n"
                f"{summary}\n\n"
                f"**¿Por qué importa?** La severidad de esta señal es **{sev_label}**. {urgency}\n\n"
                f"*Este hallazgo fue detectado automáticamente por el sistema de insights. "
                f"Es una asociación estadística, no una causa confirmada.*"
            )

        return (
            f"El último análisis fue sobre **{last_metric_display}** en {ctx_country}. "
            f"Para una explicación más detallada, pregunta primero algo concreto — "
            f"por ejemplo: *¿Qué problemas tiene {ctx_country}?*"
        )

    if result.get("error"):
        return f"No se pudo completar la consulta: {result['error']}"

    if intent == "rank":
        rows = result.get("rows", [])
        n = len(rows)
        if not rows:
            return f"No encontré datos de **{metric}** en {country} para la semana indicada."
        top = rows[0]
        top_zone = top.get("ZONE", "?")
        top_country = top.get("COUNTRY", "?")
        top_val = top.get("VALUE", 0)
        asc = result.get("ascending", False)
        direction_note = "menor es mejor para esta métrica" if asc else "mayor es mejor"
        return (
            f"Estas son las {n} zonas que más destacan en **{metric}** en {country} "
            f"({direction_note}, semana {plan.get('time_window','L0W')}).\n\n"
            f"La zona líder es **{top_zone}** ({top_country}) con un valor de **{top_val:.3f}**. "
            f"El detalle completo está en la tabla de abajo."
        )

    if intent == "compare":
        seg_a = result.get("segment_a", {})
        seg_b = result.get("segment_b", {})
        delta = result.get("delta")
        va = seg_a.get("value")
        vb = seg_b.get("value")
        if va is None or vb is None:
            return f"No hay datos suficientes para comparar los segmentos de **{metric}** en {country}."
        winner = seg_a.get("name") if (delta or 0) >= 0 else seg_b.get("name")
        loser = seg_b.get("name") if winner == seg_a.get("name") else seg_a.get("name")
        magnitude = _diff_magnitude(delta, vb)
        conf_a = seg_a.get("confidence_level", "")
        conf_note = (
            "\n\n*El grupo de comparación tiene pocas zonas — este resultado hay que tomarlo con cautela.*"
            if "low_confidence" in (conf_a + seg_b.get("confidence_level", "")) else ""
        )
        n_a = seg_a.get("n_zones", "?")
        n_b = seg_b.get("n_zones", "?")
        return (
            f"En {country}, las zonas **{winner}** tienen mejor desempeño en **{metric}** "
            f"que las zonas **{loser}** — con una diferencia **{magnitude}**.\n\n"
            f"Valores medianos: {seg_a.get('name')} = **{va:.3f}** ({n_a} zonas) · "
            f"{seg_b.get('name')} = **{vb:.3f}** ({n_b} zonas) · diferencia = {abs(delta or 0):.3f}.{conf_note}"
        )

    if intent == "trend":
        rows = result.get("rows", [])
        n = result.get("n_weeks", 0)
        scope = result.get("scope", {})
        scope_str = scope.get("country") or country
        if not rows:
            return f"No hay datos de tendencia para **{metric}** en {scope_str} con los filtros aplicados."
        latest = rows[-1]["value"]
        oldest = rows[0]["value"]
        delta = round(latest - oldest, 4)
        direction = "subió" if delta > 0 else ("bajó" if delta < 0 else "se mantuvo estable")
        consistency = _trend_consistency(rows)
        pct_change = abs(delta / oldest * 100) if oldest else 0
        return (
            f"**{metric}** en {scope_str} **{direction}** {consistency} "
            f"en las últimas {n} semanas ({pct_change:.1f}% de cambio).\n\n"
            f"Valor al inicio del período: {oldest:.3f} → valor más reciente: {latest:.3f} "
            f"(diferencia: {delta:+.3f})."
        )

    if intent == "insight_request":
        rows = result.get("rows", [])
        total = result.get("total_found", 0)
        filters = result.get("filters", {})
        scope_label = filters.get("country") or country
        if not rows:
            parts = [f for f in [filters.get("country"), filters.get("metric")] if f]
            filter_str = " / ".join(parts) if parts else "los filtros actuales"
            return (
                f"No encontré señales activas para {filter_str}. "
                "Puede que no haya anomalías detectadas en este momento, o que los filtros sean muy específicos."
            )
        high = [r for r in rows if float(r.get("severity_score", 0)) >= 0.7]
        med = [r for r in rows if 0.4 <= float(r.get("severity_score", 0)) < 0.7]
        low_r = [r for r in rows if float(r.get("severity_score", 0)) < 0.4]

        if high:
            intro = (
                f"En {scope_label} hay "
                f"{'una señal que requiere atención inmediata' if len(high) == 1 else f'{len(high)} señales que requieren atención'}. "
                f"De {total} hallazgos detectados, estos son los más importantes:"
            )
        elif med:
            intro = (
                f"No hay alertas críticas en {scope_label}, "
                f"pero hay {len(med)} señales que vale la pena monitorear "
                f"({total} hallazgos en total):"
            )
        else:
            intro = (
                f"No hay alertas preocupantes en {scope_label} en este momento. "
                f"Estos son los {min(len(low_r), 3)} hallazgos de baja prioridad detectados:"
            )

        lines = [intro + "\n"]
        for row in rows[:3]:
            sev = float(row.get("severity_score", 0))
            icon = "🔴" if sev >= 0.7 else ("🟡" if sev >= 0.4 else "🟢")
            entity = row.get("display_entity", "")
            mn = row.get("metric_display_name", "")
            summary = str(row.get("summary_text", ""))[:120]
            lines.append(f"{icon} **{entity}** · {mn}\n  {summary}")
        return "\n".join(lines)

    if intent == "hypothesis_request":
        n = result.get("n_found", 0)
        if not n:
            return (
                "No encontré patrones que puedan estar asociados con este resultado. "
                "Intenta sin filtrar por métrica para ampliar la búsqueda."
            )
        rows = result.get("rows", [])
        lines = [
            f"Aquí hay {n} posibles factores que podrían estar asociados con este resultado "
            f"(son correlaciones estadísticas detectadas automáticamente — no implican responsabilidad directa):\n"
        ]
        for row in rows[:3]:
            entity = row.get("display_entity", "")
            mn = row.get("metric_display_name", "")
            summary = str(row.get("summary_text", ""))[:100]
            lines.append(f"• **{entity}** · {mn}: {summary}")
        return "\n".join(lines)

    if intent == "query":
        val = result.get("value")
        n_zones = result.get("n_zones", 0)
        if val is None:
            return f"No hay datos disponibles de **{metric}** en {country} para la semana {plan.get('time_window','L0W')}."
        return (
            f"La mediana de **{metric}** en {country} es **{val}**, "
            f"calculada sobre {n_zones} zonas en la semana {plan.get('time_window','L0W')}."
        )

    return "Consulta procesada."


def _build_headline(plan: dict, result: dict) -> str | None:
    intent = plan.get("intent", "")
    if intent in _ALL_TERMINAL_INTENTS:
        return None
    if intent == "compare":
        seg_a = result.get("segment_a", {})
        seg_b = result.get("segment_b", {})
        delta = result.get("delta")
        mn = result.get("metric_display_name", "")
        va, vb = seg_a.get("value"), seg_b.get("value")
        if delta is not None and va is not None and vb is not None:
            sign = "+" if delta > 0 else ""
            return f"{mn}: {seg_a.get('name')} {va:.3f} · {seg_b.get('name')} {vb:.3f} · diferencia {sign}{delta:.3f}"
    if intent == "query":
        mn = result.get("metric_display_name", "")
        v = result.get("value")
        return f"{mn}: {v}" if v is not None else None
    if intent == "rank" and result.get("rows"):
        top = result["rows"][0]
        mn = result.get("metric_display_name", "")
        return f"Líder: {top.get('ZONE','?')} ({top.get('COUNTRY','?')}) — {mn}: {top.get('VALUE',0):.3f}"
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
        x = [r.get("segment", "") for r in rows]
        y = [r.get("value") or 0 for r in rows]
        annotations = [{"x": r.get("segment", ""), "label": f"{r.get('n_zones', 0)} zonas"} for r in rows]
        return {
            "chart_type": "side_by_side_bar",
            "x_values": x,
            "y_values": y,
            "annotations": annotations,
            "title": f"{mn}: Wealthy vs Non Wealthy — {country} {week}",
        }

    if chart_type == "line_chart":
        rows = result.get("rows", [])
        scope = result.get("scope", {})
        label = scope.get("country") or country or "Todos"
        return {
            "chart_type": "line_chart",
            "x_values": [r["week"] for r in rows],
            "y_values": [r["value"] for r in rows],
            "series_labels": [f"{mn} — {label}"],
            "title": f"Evolución de {mn} — {label}",
        }

    return None


def build_executive_insight_summary(rows: list[dict], country: str | None = None) -> dict:
    """Build structured executive summary from insight rows for sidebar/panel display."""
    if not rows:
        return {"has_alerts": False, "critical": [], "medium": [], "low": [], "total": 0}
    critical = [r for r in rows if float(r.get("severity_score", 0)) >= 0.7]
    medium = [r for r in rows if 0.4 <= float(r.get("severity_score", 0)) < 0.7]
    low = [r for r in rows if float(r.get("severity_score", 0)) < 0.4]
    return {
        "has_alerts": len(critical) > 0,
        "critical": critical[:3],
        "medium": medium[:3],
        "low": low[:2],
        "total": len(rows),
        "country": country,
    }


# ── main builder ──────────────────────────────────────────────────────────────

def build_response(plan: dict, result: dict, artifacts: dict) -> dict:
    intent = plan.get("intent", "insight_request")
    metric = plan.get("metric")
    metrics_cfg = artifacts.get("metrics_cfg", {})

    # inject metric definition for explain_metric
    if intent == "explain_metric":
        metric_to_explain = plan.get("_metric_to_explain")
        if metric_to_explain:
            metric_def = next(
                (m for m in metrics_cfg.get("metrics", [])
                 if m["id"] == metric_to_explain
                 or m.get("display_name", "").lower() == metric_to_explain.lower()),
                None,
            )
            if metric_def:
                plan = {**plan, "_metric_def": metric_def}
                metric = metric_to_explain

    # display name for follow-up labels
    metric_display = result.get("metric_display_name")
    if not metric_display and metric:
        metric_display = next(
            (m["display_name"] for m in metrics_cfg.get("metrics", []) if m["id"] == metric),
            None,
        )
    country = (plan.get("entity_scope") or {}).get("country")

    # answer
    answer = _build_answer_short(plan, result)
    if plan.get("_non_causal_mode"):
        answer = apply_hypothesis_guard(answer)
    if intent not in _ALL_TERMINAL_INTENTS:
        answer = apply_direction_guard(answer, metric, metrics_cfg)

    # headline
    headline = _build_headline(plan, result)

    # evidence
    raw_rows = result.get("rows", [])
    evidence_rows = raw_rows[:5] if intent == "insight_request" else raw_rows[:10]

    # chart
    chart_spec = _build_chart_spec(plan, result)

    # caveat
    caveats = []
    if result.get("caveat"):
        caveats.append(result["caveat"])
    if plan.get("_add_association_caveat"):
        caveats.append("Los posibles factores mostrados son asociaciones estadísticas — no implican causalidad.")
    caveat_text = " | ".join(dict.fromkeys(caveats)) if caveats else None

    # follow-ups
    action_templates = _FOLLOWUP_ACTIONS.get(intent, _FOLLOWUP_ACTIONS["insight_request"])
    followups = [
        {
            "label": _render_followup_label(a["label"], metric_display, country),
            "action": a["action"],
        }
        for a in action_templates[:3]
    ]

    validation = plan.get("_validation", {})

    return {
        "answer_short": answer,
        "headline_metric": headline,
        "supporting_evidence": evidence_rows,
        "filters_used": {
            "country": country,
            "metric": metric,
            "week": plan.get("time_window", "L0W"),
            "intent": intent,
        },
        "chart_spec": chart_spec,
        "caveat": caveat_text,
        "suggested_followups": followups,
        "intent_classified": intent,
        "tool_calls_made": [] if intent in _ALL_TERMINAL_INTENTS else [result.get("tool", "unknown")],
        "debug_meta": {
            "plan": {k: v for k, v in plan.items() if not k.startswith("_raw") and k != "_gemini_raw"},
            "validation_result": validation,
            "tool_error": None if intent in _ALL_TERMINAL_INTENTS else result.get("error"),
            "terminal_intent": intent in _ALL_TERMINAL_INTENTS,
            "llm_attempted": plan.get("_llm_attempted", False),
            "llm_error": plan.get("_llm_error", ""),
            "planner_source": plan.get("_planner_source", "keyword"),
            "planner_fallback": plan.get("_planner_fallback", False),
        },
    }
