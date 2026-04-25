# Reto 1 — Streamlit MVP Integration Contract

> Generated: 2026-04-25  
> Status: design-complete, ready to implement

## Principle

The Streamlit app consumes pre-defined contracts from NB20/NB30/NB40.  
It does NOT perform analytics — it renders outputs from deterministic tools.

---

## Data artifacts consumed at startup

| Artifact | Path | Purpose |
|---|---|---|
| `streamlit_insights.parquet` | `reports/reto1/` | Pre-curated insights for insight_request intent |
| `top_insights_final.parquet` | `reports/reto1/` | Full curated insight pool for detail view |
| `metrics_long.parquet` | `data/processed/` | Base for query/rank/trend/compare tools |
| `zone_master.parquet` | `data/processed/` | Zone filter options + peer group lookup |
| `metrics.yaml` | `config/` | Metric catalog: display names, direction, validation_status |
| `business_rules.yaml` | `config/` | Peer group rules, fallback behavior, language rules |
| `question_types.yaml` | `config/` | Intent catalog: supported intents + unsupported_cases |

Load order: YAMLs → parquets (cached with `@st.cache_data`).

---

## App screens (MVP)

### Screen 1: Chat Interface
```
┌─────────────────────────────────────────────────────────────┐
│ SIDEBAR                    │ MAIN CHAT AREA                 │
│                            │                                │
│ [Métrica]    ▼             │ [conversation history]         │
│ [País]       ▼             │                                │
│ [Semana]     ▼             │  BOT: respuesta corta          │
│                            │  📊 headline_metric            │
│ ─── Top insights ──        │  📋 supporting_evidence table  │
│ 🔴 Zona X: alerta HIGH     │  📈 chart (if chart_spec)      │
│ 🟡 Zona Y: alerta MEDIUM   │  ⚠️ caveat                     │
│                            │  💡 suggested followups        │
│                            │                                │
│                            │ ────────────────────────────── │
│                            │ [chat_input: Pregunta aquí...] │
└─────────────────────────────────────────────────────────────┘
```

### Screen 2: Insight Dashboard (optional)
```
┌─────────────────────────────────────────────────────────────┐
│ Top Insights — [country] [city] — L0W                       │
│                                                             │
│ [HIGH] Zona X | metric | summary | chart_hint              │
│ [HIGH] Zona Y | metric | summary | chart_hint              │
│ [MED]  Zona Z | metric | summary | chart_hint              │
│                                                             │
│ [Filter: category | metric | severity]                      │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation order (MVP)

### Phase 1 — Data layer (1-2h)
1. `app/reto1/data_loader.py`:
   - `load_artifacts()` — loads all parquets + YAMLs, returns dict
   - `@st.cache_data` on all loads
   - Freshness check: compare `insight_engine_report.json` timestamp

### Phase 2 — Planner mock (2-3h)
2. `app/reto1/planner.py`:
   - `classify_intent(text) -> dict` — keyword-based mock first, LLM later
   - `validate_plan(plan) -> dict` — from NB40 `validate_plan_v2()`
   - `extract_entity(text) -> dict` — regex-based COUNTRY/CITY/ZONE extraction

### Phase 3 — Tool adapter layer (4-6h)
3. `app/reto1/tools.py`:
   - Implement 9 tools from NB40 tool_detail
   - Start with: `route_insight_request`, `rank_by_metric`, `compare_segments`, `get_trend`
   - Stub remaining: return empty DataFrame with correct schema

### Phase 4 — Response renderer (2-3h)
4. `app/reto1/renderer.py`:
   - `build_response(tool_result, intent, plan) -> dict` — UI_RESPONSE_SCHEMA
   - `apply_language_guards(response, metric_id) -> dict` — from NB40 language guards
   - `build_chart_spec(result, chart_type) -> dict | None`

### Phase 5 — Chart rendering (2-3h)
5. `app/reto1/charts.py`:
   - `render_chart(chart_spec: dict) -> plotly.Figure | None`
   - Map chart_type to plotly figure factory
   - Fallback: st.dataframe if chart fails

### Phase 6 — Session state (1-2h)
6. `app/reto1/session.py`:
   - `ChatSessionState` class (dataclass)
   - `update_state(state, plan, result) -> ChatSessionState`
   - `apply_follow_up(state, new_plan) -> dict` — inherits last entity/metric

### Phase 7 — Streamlit app shell (3-4h)
7. `app/reto1/app.py`:
   - Sidebar: filters + insight panel
   - Chat: input → planner → tool → renderer → display
   - Response sections: answer + evidence + chart + caveat + followups
   - Debug expander (optional)

### Phase 8 — Golden flow tests (2-3h)
8. `app/reto1/tests/test_golden_flows.py`:
   - 6 MVP golden flows as pytest cases
   - Assert: intent_classified, tool_calls_made, caveat present, no causal language

---

## What's already ready (no build needed)

| Component | Source | Ready |
|---|---|---|
| Semantic contract | `config/*.yaml` + NB20 | ✓ |
| Planner schema (JSON) | `reports/reto1/chatbot_planner_schema.json` | ✓ |
| Tool contracts | NB40 `nb40-tool-detail` | ✓ |
| validate_plan() function | NB40 `nb40-validate-v2` | ✓ |
| Language guard functions | NB40 `nb40-lang-guards` | ✓ |
| UI response schema | NB40 `nb40-response-ui` | ✓ |
| Sample state | `app/reto1/sample_state.json` | ✓ |
| Sample response | `app/reto1/sample_response.json` | ✓ |
| streamlit_insights.parquet | NB30 (run to generate) | ✓ after NB30 run |
| top_insights_final.parquet | NB30 (run to generate) | ✓ after NB30 run |

---

## What blocks production use

| Blocker | Who resolves |
|---|---|
| `desired_direction` validation for 13 metrics | Business team |
| Detector threshold calibration | Analytics + business |
| LLM planner prompt (structured output) | Engineering |
| Tool adapter layer implementation | Engineering |
| `lead_penetration` denominator clarification | Data team |
