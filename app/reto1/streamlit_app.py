"""Reto 1 — Operational Intelligence Streamlit MVP.

Run: streamlit run app/reto1/streamlit_app.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[2]))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from app.reto1.config import SEVERITY_COLORS, WEEK_OPTIONS, USE_LLM
from app.reto1.data_loader import load_artifacts, get_metric_display, get_countries
from app.reto1.state import ChatSessionState, init_session, update_state
from app.reto1.planner import build_plan
from app.reto1.tools import run_tool
from app.reto1.renderer import build_response

# ── page config ──────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Rappi Operational Intelligence",
    page_icon="📊",
    layout="wide",
)

# ── helper functions ─────────────────────────────────────────────────────────

def _build_plotly(spec: dict):
    ct = spec.get("chart_type")
    if ct == "side_by_side_bar":
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=spec["x_values"],
            y=spec["y_values"],
            text=[a["label"] for a in spec.get("annotations", [])],
            textposition="outside",
        ))
        fig.update_layout(title=spec.get("title", ""), height=350)
        return fig

    if ct == "line_chart":
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=spec["x_values"],
            y=spec["y_values"],
            mode="lines+markers",
            name=(spec.get("series_labels") or [""])[0],
        ))
        fig.update_layout(title=spec.get("title", ""), height=350)
        return fig

    return None


def _render_response(resp: dict, msg_key: str = ""):
    """Render a UI response dict as Streamlit components."""
    st.markdown(resp.get("answer_short", ""))

    hl = resp.get("headline_metric")
    if hl:
        st.metric(label="Métrica principal", value=hl)

    spec = resp.get("chart_spec")
    if spec:
        fig = _build_plotly(spec)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    rows = resp.get("supporting_evidence", [])
    if rows:
        st.subheader("Evidencia")
        st.dataframe(pd.DataFrame(rows), use_container_width=True)

    cav = resp.get("caveat")
    if cav:
        st.warning(cav)

    followups = resp.get("suggested_followups", [])
    if followups:
        st.markdown("**Preguntas sugeridas:**")
        cols = st.columns(len(followups))
        for i, fq in enumerate(followups):
            btn_key = f"fq_{msg_key}_{i}"
            if cols[i].button(fq, key=btn_key):
                st.session_state["_pending_input"] = fq

    with st.expander("Debug / Meta", expanded=False):
        st.json(resp.get("debug_meta", {}))
        st.caption(f"Intent: {resp.get('intent_classified')} | Tools: {resp.get('tool_calls_made')}")


# ── session init ─────────────────────────────────────────────────────────────

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
    sel_metric_display = st.selectbox(
        "Métrica (default)", ["(ninguna)"] + list(metric_display.values())
    )
    sel_metric = metric_options.get(sel_metric_display)

    sel_country = st.selectbox("País (default)", ["(todos)"] + countries)
    if sel_country == "(todos)":
        sel_country = None

    sel_week = st.selectbox("Semana", WEEK_OPTIONS, index=0)

    st.divider()

    with st.expander("Top insights activos", expanded=False):
        si = artifacts["streamlit_insights"]
        display_si = si
        if sel_country:
            display_si = si[si["display_entity"].str.match(f"^{sel_country}\\s*\\|", na=False)]
        for _, row in display_si.head(8).iterrows():
            sev = float(row.get("severity_score", 0))
            color = SEVERITY_COLORS["HIGH"] if sev >= 0.7 else (SEVERITY_COLORS["MEDIUM"] if sev >= 0.4 else SEVERITY_COLORS["LOW"])
            st.markdown(
                f'<span style="color:{color}">●</span> **{row["display_entity"]}** — '
                f'{row["metric_display_name"]}: {str(row["summary_text"])[:80]}…',
                unsafe_allow_html=True,
            )

    st.divider()
    if USE_LLM:
        st.success("LLM planner: activo")
    else:
        st.info("Modo: keyword planner (sin LLM)")

    if st.button("Limpiar conversación"):
        st.session_state.messages = []
        st.session_state.chat_state = init_session()
        st.session_state.msg_counter = 0
        st.rerun()

# ── main area ─────────────────────────────────────────────────────────────────

st.title("Rappi Operational Intelligence")
st.caption(
    "Pregunta sobre métricas operativas de zonas. "
    "Ejemplos: *Top 5 zonas por Perfect Orders en MX* · "
    "*Compara Wealthy vs Non Wealthy en CO* · "
    "*Tendencia de Turbo Adoption en BR* · "
    "*Qué problemas tiene Argentina*"
)

# render history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            _render_response(msg["response"], msg_key=str(msg.get("idx", "")))

# ── chat input ────────────────────────────────────────────────────────────────

pending = st.session_state.pop("_pending_input", None)
user_input = st.chat_input("Pregunta sobre métricas operativas de zonas Rappi...") or pending

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    state: ChatSessionState = st.session_state.chat_state

    with st.chat_message("assistant"):
        with st.spinner("Procesando..."):
            plan = build_plan(user_input, artifacts, state)

            # inject sidebar defaults if not extracted from text
            scope = plan.get("entity_scope") or {}
            if not scope.get("country") and sel_country:
                plan["entity_scope"] = {**scope, "country": sel_country}
            if not plan.get("metric") and sel_metric:
                plan["metric"] = sel_metric
            if plan.get("time_window") == "L0W":
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
                        "¿Ver top zonas por Perfect Orders?",
                        "¿Comparar Wealthy vs Non Wealthy?",
                        "¿Ver insights de Argentina?",
                    ],
                    "intent_classified": plan.get("intent", "unknown"),
                    "tool_calls_made": [],
                    "debug_meta": {"plan": plan},
                }
            else:
                result = run_tool(plan, artifacts)
                resp = build_response(plan, result, artifacts)
                state = update_state(state, plan, result)
                st.session_state.chat_state = state

        idx = st.session_state.msg_counter
        st.session_state.msg_counter += 1
        _render_response(resp, msg_key=str(idx))

    st.session_state.messages.append({"role": "assistant", "response": resp, "idx": idx})
