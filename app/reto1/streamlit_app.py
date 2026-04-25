"""Reto 1 — Operational Intelligence Streamlit MVP.

Run: streamlit run app/reto1/streamlit_app.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2]))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from app.reto1.config import SEVERITY_COLORS, WEEK_OPTIONS, LLM_ACTIVE, GEMINI_MODEL
from app.reto1.data_loader import load_artifacts, get_metric_display, get_countries
from app.reto1.state import ChatSessionState, init_session, update_state, build_plan_from_action
from app.reto1.planner import build_plan, validate_plan
from app.reto1.tools import run_tool
from app.reto1.renderer import build_response, build_executive_insight_summary

# ── page config ───────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Rappi Operational Intelligence",
    page_icon="📊",
    layout="wide",
)

# ── chart renderer ────────────────────────────────────────────────────────────

def _build_plotly(spec: dict):
    ct = spec.get("chart_type")
    if ct == "side_by_side_bar":
        fig = go.Figure(go.Bar(
            x=spec["x_values"],
            y=spec["y_values"],
            text=[a["label"] for a in spec.get("annotations", [])],
            textposition="outside",
        ))
        fig.update_layout(title=spec.get("title", ""), height=350, margin=dict(t=40))
        return fig
    if ct == "line_chart":
        fig = go.Figure(go.Scatter(
            x=spec["x_values"],
            y=spec["y_values"],
            mode="lines+markers",
            name=(spec.get("series_labels") or [""])[0],
        ))
        fig.update_layout(title=spec.get("title", ""), height=350, margin=dict(t=40))
        return fig
    return None


# ── response renderer ─────────────────────────────────────────────────────────

_EXAMPLES = {
    "example_rank_mx":    "Top 5 zonas por Perfect Orders en MX",
    "example_compare_co": "Compara Wealthy vs Non Wealthy por Perfect Orders en CO",
    "example_insight_ar": "Qué problemas tiene Argentina",
}

_TERMINAL_INTENTS_UI = {
    "greeting", "help", "no_intent", "about_data",
    "explain_result", "explain_metric", "explain_table", "no_intent_guided",
}


def _render_response(resp: dict, msg_key: str = ""):
    intent = resp.get("intent_classified", "")
    st.markdown(resp.get("answer_short", ""))

    hl = resp.get("headline_metric")
    if hl:
        st.metric(label="Resumen del resultado", value=hl)

    spec = resp.get("chart_spec")
    if spec:
        fig = _build_plotly(spec)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    rows = resp.get("supporting_evidence", [])
    if rows:
        if intent == "insight_request":
            summary = build_executive_insight_summary(rows)
            alert_label = "alertas críticas activas" if summary["has_alerts"] else "señales medias o bajas"
            with st.expander(
                f"📋 Ver detalle numérico — {summary['total']} hallazgos ({alert_label})",
                expanded=False,
            ):
                st.caption("Si quieres revisar el detalle de cada hallazgo, aquí están los datos utilizados.")
                df = pd.DataFrame(rows)
                # only show readable columns
                show_cols = [c for c in ["display_entity", "metric_display_name", "summary_text", "severity_score"] if c in df.columns]
                st.dataframe(df[show_cols] if show_cols else df, use_container_width=True)
                st.caption(
                    "severity_score: 🔴 ≥0.7 atención inmediata · "
                    "🟡 ≥0.4 monitorear · 🟢 <0.4 baja prioridad · "
                    "display_entity = País | Ciudad | Zona"
                )
        elif intent not in _TERMINAL_INTENTS_UI:
            _READABLE_COLS = {
                "rank": ["ZONE", "CITY", "COUNTRY", "ZONE_TYPE", "VALUE", "rank"],
                "compare": ["segment", "value", "n_zones", "confidence_level"],
                "trend": ["week", "value"],
                "query": ["week", "value", "n_zones"],
                "hypothesis_request": ["display_entity", "metric_display_name", "summary_text"],
            }
            with st.expander("Ver detalle numérico", expanded=False):
                st.caption("Si quieres revisar el detalle numérico, aquí está la evidencia utilizada.")
                df = pd.DataFrame(rows)
                preferred = _READABLE_COLS.get(intent, [])
                show_cols = [c for c in preferred if c in df.columns] or list(df.columns)
                st.dataframe(df[show_cols], use_container_width=True)
                st.caption("Escribe *¿qué significa [columna]?* si quieres que te explique algún término.")

    cav = resp.get("caveat")
    if cav:
        st.warning(cav)

    # structured follow-up buttons
    followups = resp.get("suggested_followups", [])
    if followups:
        st.markdown("**¿Qué quieres explorar ahora?**")
        cols = st.columns(len(followups))
        for i, fup in enumerate(followups):
            label = fup["label"] if isinstance(fup, dict) else fup
            action = fup.get("action", "") if isinstance(fup, dict) else ""
            btn_key = f"fq_{msg_key}_{i}"
            if cols[i].button(label, key=btn_key):
                if action.startswith("example_"):
                    st.session_state["_pending_input"] = _EXAMPLES.get(action, label)
                elif action:
                    st.session_state["_pending_action"] = action
                else:
                    st.session_state["_pending_input"] = label

    # debug panel
    with st.expander("Debug / Meta", expanded=False):
        dmeta = resp.get("debug_meta", {})
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Intent", intent or "—")
        planner_src = dmeta.get("planner_source", "keyword")
        fallback = dmeta.get("planner_fallback", False)
        c2.metric("Planner", planner_src + (" ⚠️" if fallback else ""))
        llm_err = dmeta.get("llm_error", "")
        c3.metric("LLM error", llm_err[:20] if llm_err else "—")
        c4.metric("Tools", str(resp.get("tool_calls_made", [])))
        if llm_err:
            st.error(f"LLM error detail: {llm_err}")
        st.json(dmeta)


# ── action executor (structured follow-ups) ──────────────────────────────────

def _execute_action(action: str, state: ChatSessionState, artifacts: dict,
                    sel_country: str | None, sel_metric: str | None, sel_week: str) -> dict:
    """Build a plan from a structured action + session state, run tool, return response."""
    plan = build_plan_from_action(action, state)

    if plan is None:
        # no context available — guide the user
        missing = "métrica" if not state.last_metric_id else "entidad/scope"
        return {
            "answer_short": f"No hay {missing} reciente en la sesión. Haz primero una pregunta analítica.",
            "headline_metric": None,
            "supporting_evidence": [],
            "filters_used": {},
            "chart_spec": None,
            "caveat": None,
            "suggested_followups": [
                {"label": "Top 5 por Perfect Orders en MX", "action": "example_rank_mx"},
                {"label": "Insights de Argentina", "action": "example_insight_ar"},
            ],
            "intent_classified": "no_context",
            "tool_calls_made": [],
            "debug_meta": {"action": action, "state_metric": state.last_metric_id, "state_entity": state.last_entity},
        }

    # fill sidebar defaults if still missing
    scope = plan.get("entity_scope") or {}
    if not scope.get("country") and sel_country:
        plan["entity_scope"] = {**scope, "country": sel_country}
    if not plan.get("metric") and sel_metric:
        plan["metric"] = sel_metric
    if not plan.get("time_window"):
        plan["time_window"] = sel_week

    # validate
    validation = validate_plan(plan, artifacts)
    if not validation["valid"]:
        return {
            "answer_short": f"⚠️ {validation['reason']}",
            "headline_metric": None,
            "supporting_evidence": [],
            "filters_used": {},
            "chart_spec": None,
            "caveat": validation.get("suggestion"),
            "suggested_followups": [],
            "intent_classified": plan.get("intent", "unknown"),
            "tool_calls_made": [],
            "debug_meta": {"plan": plan, "validation": validation},
        }

    plan = {**validation["adjusted_plan"], "_validation": validation}
    result = run_tool(plan, artifacts)
    return build_response(plan, result, artifacts)


# ── session init ──────────────────────────────────────────────────────────────

if "chat_state" not in st.session_state:
    st.session_state.chat_state = init_session()
if "messages" not in st.session_state:
    st.session_state.messages = []
if "msg_counter" not in st.session_state:
    st.session_state.msg_counter = 0

artifacts = load_artifacts()
metric_display = get_metric_display(artifacts)
countries = get_countries(artifacts)

# ── sidebar ───────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📊 Reto 1 — Ops Intel")
    st.caption("Chatbot analítico gobernado — Rappi Zonas")

    st.subheader("Filtros de contexto")
    metric_options = {v: k for k, v in metric_display.items()}
    sel_metric_display = st.selectbox("Métrica (default)", ["(ninguna)"] + list(metric_display.values()))
    sel_metric = metric_options.get(sel_metric_display)

    sel_country = st.selectbox("País (default)", ["(todos)"] + countries)
    if sel_country == "(todos)":
        sel_country = None

    sel_week = st.selectbox("Semana", WEEK_OPTIONS, index=0)

    st.divider()

    with st.expander("Top insights activos", expanded=False):
        si = artifacts["streamlit_insights"]
        display_si = si if not sel_country else si[si["display_entity"].str.match(f"^{sel_country}\\s*\\|", na=False)]
        for _, row in display_si.head(8).iterrows():
            sev = float(row.get("severity_score", 0))
            color = SEVERITY_COLORS["HIGH"] if sev >= 0.7 else (SEVERITY_COLORS["MEDIUM"] if sev >= 0.4 else SEVERITY_COLORS["LOW"])
            st.markdown(
                f'<span style="color:{color}">●</span> **{row["display_entity"]}** — '
                f'{row["metric_display_name"]}: {str(row["summary_text"])[:80]}…',
                unsafe_allow_html=True,
            )

    st.divider()

    with st.expander("📖 Qué datos usamos", expanded=False):
        st.markdown(
            "**Países:** AR · BR · CL · CO · CR · EC · MX · PE · UY\n\n"
            "**Semanas:** L0W (más reciente) → L8W (hace 8 semanas). Sin fechas calendario.\n\n"
            "**Zonas:** cada zona Rappi tiene `COUNTRY + CITY + ZONE` como clave única.\n\n"
            "**Tipos de zona:** Wealthy vs Non Wealthy (segmento socioeconómico).\n\n"
            "**Fuente:** RAW_INPUT_METRICS + RAW_ORDERS. ~300–600 zonas por país."
        )

    with st.expander("📏 Métricas principales", expanded=False):
        st.markdown(
            "| Métrica | Dirección |\n"
            "|---|---|\n"
            "| Perfect Orders | ↑ mayor es mejor |\n"
            "| Turbo Adoption | ↑ mayor es mejor |\n"
            "| Gross Profit UE | ↑ mayor es mejor |\n"
            "| Pro Adoption | ↑ mayor es mejor |\n"
            "| Restaurants Markdowns/GMV | ↓ menor es mejor |\n"
            "| Assortment Coverage | ↑ mayor es mejor |\n"
            "| ATC CVR / SST CVR | ↑ mayor es mejor |\n\n"
            "⚠️ Todas las direcciones son **provisionales** — no validadas con negocio.\n\n"
            "`lead_penetration` **suspendida** — excluida de rankings."
        )

    with st.expander("🔍 Cómo leer los resultados", expanded=False):
        st.markdown(
            "**VALUE**: valor de la métrica (mediana de zonas cuando hay agregación).\n\n"
            "**n_zones**: cantidad de zonas en el cálculo.\n\n"
            "**confidence_level**: `reliable` = 10+ zonas · `low_confidence` = <10 zonas.\n\n"
            "**severity_score**: 🔴 ≥0.7 crítico · 🟡 ≥0.4 medio · 🟢 <0.4 bajo.\n\n"
            "**delta**: diferencia entre segmentos (Wealthy − Non Wealthy).\n\n"
            "**Wealthy / Non Wealthy**: segmento socioeconómico de la zona, no del usuario.\n\n"
            "**peer group**: zonas comparables por país + tipo + priorización. Mínimo 10 zonas."
        )

    with st.expander("⚠️ Limitaciones importantes", expanded=False):
        st.markdown(
            "- Todas las **direcciones deseables** son hipótesis de trabajo — no validadas.\n"
            "- `lead_penetration` **suspendida** por definición inconsistente.\n"
            "- Sin fechas calendario — solo offsets relativos.\n"
            "- Las hipótesis detectadas son **asociaciones estadísticas**, no causalidades.\n"
            "- Peer groups con <10 zonas tienen benchmarks frágiles.\n"
            "- Cobertura parcial: ~264 zonas en orders sin métricas operativas."
        )

    st.divider()
    if LLM_ACTIVE:
        st.success(f"Planner: Gemini ({GEMINI_MODEL})")
    else:
        st.info("Planner: keyword (sin LLM)")

    # show current session context
    state_ref: ChatSessionState = st.session_state.chat_state
    if state_ref.last_metric_id or state_ref.last_entity.get("country"):
        with st.expander("Contexto de sesión", expanded=False):
            st.caption(f"Métrica: {state_ref.last_metric_id or '—'}")
            st.caption(f"País: {state_ref.last_entity.get('country') or '—'}")
            st.caption(f"Semana: {state_ref.last_time_window}")
            st.caption(f"Último intent: {state_ref.last_intent or '—'}")

    if st.button("Limpiar conversación"):
        st.session_state.messages = []
        st.session_state.chat_state = init_session()
        st.session_state.msg_counter = 0
        st.rerun()

# ── main area ─────────────────────────────────────────────────────────────────

st.title("Rappi Operational Intelligence")
st.caption(
    "Ejemplos: *Top 5 zonas por Perfect Orders en MX* · "
    "*Compara Wealthy vs Non Wealthy en CO* · "
    "*Qué problemas tiene Argentina* · "
    "*Tendencia de Turbo Adoption en MX*"
)

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            _render_response(msg["response"], msg_key=str(msg.get("idx", "")))

# ── input handling ────────────────────────────────────────────────────────────

pending_input = st.session_state.pop("_pending_input", None)
pending_action = st.session_state.pop("_pending_action", None)
user_input = st.chat_input("Pregunta sobre métricas operativas de zonas Rappi...") or pending_input

state: ChatSessionState = st.session_state.chat_state

# ── structured action (follow-up button) ─────────────────────────────────────

if pending_action:
    display_label = pending_action.replace("_", " ").capitalize()
    st.session_state.messages.append({"role": "user", "content": f"[{display_label}]"})
    with st.chat_message("user"):
        st.markdown(f"*{display_label}*")

    with st.chat_message("assistant"):
        with st.spinner("Procesando..."):
            resp = _execute_action(pending_action, state, artifacts, sel_country, sel_metric, sel_week)
            # update state if action ran a real tool
            if resp.get("intent_classified") not in ("no_context", "unknown"):
                plan_stub = {
                    "intent": resp.get("intent_classified"),
                    "metric": (resp.get("filters_used") or {}).get("metric"),
                    "entity_scope": {"country": (resp.get("filters_used") or {}).get("country"), "city": None, "zone": None},
                    "time_window": (resp.get("filters_used") or {}).get("week", "L0W"),
                }
                result_stub = {"tool": (resp.get("tool_calls_made") or ["unknown"])[0]}
                state = update_state(state, plan_stub, result_stub)
                state.last_chart_spec = resp.get("chart_spec")
                st.session_state.chat_state = state

        idx = st.session_state.msg_counter
        st.session_state.msg_counter += 1
        _render_response(resp, msg_key=str(idx))

    st.session_state.messages.append({"role": "assistant", "response": resp, "idx": idx})

# ── free-text input ───────────────────────────────────────────────────────────

elif user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Procesando..."):
            plan = build_plan(user_input, artifacts, state)

            # inject sidebar defaults only for analytical intents
            _NON_ANALYTICAL = _TERMINAL_INTENTS_UI
            if plan.get("intent") not in _NON_ANALYTICAL:
                scope = plan.get("entity_scope") or {}
                if not scope.get("country") and sel_country:
                    plan["entity_scope"] = {**scope, "country": sel_country}
                if not plan.get("metric") and sel_metric:
                    plan["metric"] = sel_metric
            if plan.get("intent") not in _NON_ANALYTICAL and plan.get("time_window") == "L0W":
                plan["time_window"] = sel_week

            if plan.get("_error"):
                resp = {
                    "answer_short": f"⚠️ {plan['_error']}",
                    "headline_metric": None,
                    "supporting_evidence": [],
                    "filters_used": {},
                    "chart_spec": None,
                    "caveat": plan.get("_suggestion"),
                    "suggested_followups": [
                        {"label": "Top zonas por Perfect Orders en MX", "action": "example_rank_mx"},
                        {"label": "Compara Wealthy vs Non Wealthy en CO", "action": "example_compare_co"},
                        {"label": "Insights de Argentina", "action": "example_insight_ar"},
                    ],
                    "intent_classified": plan.get("intent", "unknown"),
                    "tool_calls_made": [],
                    "debug_meta": {
                        "plan": {k: v for k, v in plan.items() if not k.startswith("_raw") and k != "_gemini_raw"},
                        "llm_attempted": plan.get("_llm_attempted", False),
                        "llm_error": plan.get("_llm_error", ""),
                        "planner_source": plan.get("_planner_source", "keyword"),
                        "planner_fallback": plan.get("_planner_fallback", False),
                    },
                }
            else:
                result = run_tool(plan, artifacts)
                resp = build_response(plan, result, artifacts)
                # don't update state for terminal intents — preserves last analytical context
                if plan.get("intent") not in _NON_ANALYTICAL:
                    state = update_state(state, plan, result)
                    state.last_chart_spec = resp.get("chart_spec")
                    st.session_state.chat_state = state

        idx = st.session_state.msg_counter
        st.session_state.msg_counter += 1
        _render_response(resp, msg_key=str(idx))

    st.session_state.messages.append({"role": "assistant", "response": resp, "idx": idx})
