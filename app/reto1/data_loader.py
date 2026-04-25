"""Load and cache all data artifacts at startup."""
import streamlit as st
import pandas as pd
import yaml
from app.reto1.config import CONFIG_DIR, DATA_DIR, REPORTS_DIR


@st.cache_data
def load_artifacts() -> dict:
    metrics_cfg = yaml.safe_load((CONFIG_DIR / "metrics.yaml").read_text())
    biz_rules = yaml.safe_load((CONFIG_DIR / "business_rules.yaml").read_text())
    q_types = yaml.safe_load((CONFIG_DIR / "question_types.yaml").read_text())

    ic_path = REPORTS_DIR / "insight_candidates.parquet"
    return {
        "streamlit_insights": pd.read_parquet(REPORTS_DIR / "streamlit_insights.parquet"),
        "top_insights_final": pd.read_parquet(REPORTS_DIR / "top_insights_final.parquet"),
        "insight_candidates": pd.read_parquet(ic_path) if ic_path.exists() else pd.DataFrame(),
        "metrics_long": pd.read_parquet(DATA_DIR / "metrics_long.parquet"),
        "zone_master": pd.read_parquet(DATA_DIR / "zone_master.parquet"),
        "metrics_cfg": metrics_cfg,
        "business_rules": biz_rules,
        "question_types": q_types,
    }


def get_metric_ids(artifacts: dict) -> list[str]:
    return [m["id"] for m in artifacts["metrics_cfg"]["metrics"]]


def get_metric_display(artifacts: dict) -> dict[str, str]:
    return {m["id"]: m["display_name"] for m in artifacts["metrics_cfg"]["metrics"]}


def get_countries(artifacts: dict) -> list[str]:
    return sorted(artifacts["zone_master"]["COUNTRY"].dropna().unique().tolist())
