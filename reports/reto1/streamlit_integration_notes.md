# Streamlit Integration Notes — Reto 1

> Generated: 2026-04-25

## What to load at app startup

```python
# app/reto1/data_loader.py
import streamlit as st
import pandas as pd
import yaml
from pathlib import Path

ROOT = Path(__file__).parents[2]

@st.cache_data
def load_artifacts():
    return {
        'streamlit_insights': pd.read_parquet(ROOT / 'reports/reto1/streamlit_insights.parquet'),
        'top_insights_final': pd.read_parquet(ROOT / 'reports/reto1/top_insights_final.parquet'),
        'metrics_long':       pd.read_parquet(ROOT / 'data/processed/metrics_long.parquet'),
        'zone_master':        pd.read_parquet(ROOT / 'data/processed/zone_master.parquet'),
        'metrics_cfg':        yaml.safe_load((ROOT / 'config/metrics.yaml').read_text()),
        'business_rules':     yaml.safe_load((ROOT / 'config/business_rules.yaml').read_text()),
        'question_types':     yaml.safe_load((ROOT / 'config/question_types.yaml').read_text()),
    }
```

## Response schema (copy from NB40 `UI_RESPONSE_SCHEMA`)

```python
response = {
    'answer_short':        str,           # 1-2 sentences
    'headline_metric':     str | None,    # metric + value + direction
    'supporting_evidence': list[dict],    # max 10 rows
    'filters_used':        dict,          # scope
    'chart_spec':          dict | None,   # see ui_schema.json
    'caveat':              str | None,    # from build_uncertainty_caveat()
    'suggested_followups': list[str],     # 2-3 next questions
    'intent_classified':   str,
    'tool_calls_made':     list[str],
    'debug_meta':          dict | None,
}
```

## MVP intent support matrix

| Intent | Tool | Status |
|---|---|---|
| rank | rank_by_metric | build first |
| compare | compare_segments | build second |
| insight_request | route_insight_request | reads parquet — easiest |
| trend | get_trend + render_chart_data | build third |
| hypothesis_request | generate_hypothesis_candidates | partial (NB30 rows) |
| follow_up_scope_refine | reuse last tool + new filter | state-dependent |
| follow_up_visualization | render_chart_data | needs chart layer |
| query | get_metric_value | simplest |

## Severity colors (for alert_cards)

```python
SEVERITY_COLORS = {'HIGH': '#FF4B4B', 'MEDIUM': '#FFA500', 'LOW': '#4CAF50'}
```

## Key caveats to always show

1. `direction provisional` → `st.warning("Dirección de {metric} provisional — no validada.")`
2. `peer_confidence low_confidence` → `st.warning("Peer group pequeño (n={n}) — benchmark frágil.")`
3. `insight thresholds provisional` → in insight_request responses always
4. `association_not_causation` → in hypothesis_request responses always

## What NOT to do in the app

- Do not compute metrics from raw data in the app layer
- Do not use `lead_penetration` anywhere in the UI
- Do not show raw `insight_candidates.parquet` to users (use `streamlit_insights` only)
- Do not make causal claims in response text
- Do not skip caveats to make responses cleaner
