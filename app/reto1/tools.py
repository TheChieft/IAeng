"""P1 deterministic tools — consume pre-computed artifacts only.

No metric computation here — only filtering, aggregation, lookup.
"""
from __future__ import annotations
import pandas as pd
from app.reto1.config import SUSPENDED_METRICS, LOWER_IS_BETTER, LOW_COVERAGE_PEER


# ── helpers ──────────────────────────────────────────────────────────────────

def _id_to_display(metric_id: str, metrics_cfg: dict) -> str:
    """Map metric ID → display name used in metrics_long METRIC column."""
    for m in metrics_cfg.get("metrics", []):
        if m["id"] == metric_id:
            return m["display_name"]
    return metric_id  # fallback: pass through


def _filter_long(ml: pd.DataFrame, metric_display: str, country: str | None,
                 week: str = "L0W", zone: str | None = None,
                 city: str | None = None) -> pd.DataFrame:
    df = ml[ml["METRIC"] == metric_display].copy()
    df = df[df["WEEK_OFFSET"] == week]
    if country:
        df = df[df["COUNTRY"] == country]
    if city:
        df = df[df["CITY"] == city]
    if zone:
        df = df[df["ZONE"] == zone]
    return df


def _caveat_for(metric: str, peer_n: int | None, metrics_cfg: dict) -> str | None:
    caveats = []
    for m in metrics_cfg.get("metrics", []):
        if m["id"] == metric:
            if m.get("direction_confidence") == "provisional":
                caveats.append(f"Dirección de {m['display_name']} provisional — no validada.")
            if m.get("validation_status") == "suspended_pending_definition":
                caveats.append(f"{m['display_name']} suspendida — definición pendiente.")
            break
    if peer_n is not None and peer_n < 10:
        caveats.append(f"Peer group pequeño (n={peer_n}) — benchmark frágil.")
    if metric in LOW_COVERAGE_PEER:
        caveats.append("Cobertura baja en algunos peer groups — benchmark puede ser incompleto.")
    return " | ".join(caveats) if caveats else None


# ── P1 tools ─────────────────────────────────────────────────────────────────

def route_insight_request(plan: dict, artifacts: dict) -> dict:
    """Return pre-curated insights filtered by country/metric."""
    si: pd.DataFrame = artifacts["streamlit_insights"].copy()

    country = (plan.get("entity_scope") or {}).get("country")
    metric = plan.get("metric")

    if country:
        si = si[si["display_entity"].str.match(f"^{country}\\s*\\|", na=False)]
    if metric:
        metric_name = next(
            (m["display_name"] for m in artifacts["metrics_cfg"]["metrics"] if m["id"] == metric),
            None
        )
        if metric_name:
            si = si[si["metric_display_name"].str.contains(metric_name, na=False, case=False)]

    si = si.sort_values("final_rank_score", ascending=False)
    rows = si.head(10)

    return {
        "tool": "route_insight_request",
        "rows": rows.to_dict(orient="records"),
        "total_found": len(si),
        "filters": {"country": country, "metric": metric},
    }


def rank_by_metric(plan: dict, artifacts: dict) -> dict:
    """Rank zones by metric value at given week."""
    metric = plan.get("metric")
    if not metric or metric in SUSPENDED_METRICS:
        return {"tool": "rank_by_metric", "error": "metric required or suspended", "rows": []}

    ml: pd.DataFrame = artifacts["metrics_long"]
    country = (plan.get("entity_scope") or {}).get("country")
    week = plan.get("time_window", "L0W")
    top_n = plan.get("top_n", 5)
    metric_dn = _id_to_display(metric, artifacts["metrics_cfg"])

    df = _filter_long(ml, metric_dn, country, week)
    if df.empty:
        return {"tool": "rank_by_metric", "error": "no data for filters", "rows": []}

    ascending = metric in LOWER_IS_BETTER
    df = df.sort_values("VALUE", ascending=ascending).dropna(subset=["VALUE"])
    top_rows = df.head(top_n)[["COUNTRY", "CITY", "ZONE", "ZONE_TYPE", "VALUE"]].copy()
    top_rows["rank"] = range(1, len(top_rows) + 1)

    display_name = next(
        (m["display_name"] for m in artifacts["metrics_cfg"]["metrics"] if m["id"] == metric),
        metric
    )

    return {
        "tool": "rank_by_metric",
        "metric": metric,
        "metric_display_name": display_name,
        "week": week,
        "country_filter": country,
        "ascending": ascending,
        "rows": top_rows.to_dict(orient="records"),
        "total_zones": len(df),
        "caveat": _caveat_for(metric, None, artifacts["metrics_cfg"]),
        "chart_type": "ranked_table",
    }


def compare_segments(plan: dict, artifacts: dict) -> dict:
    """Compare two ZONE_TYPE segments for a metric."""
    metric = plan.get("metric")
    if not metric or metric in SUSPENDED_METRICS:
        return {"tool": "compare_segments", "error": "metric required or suspended", "rows": []}

    comparison = plan.get("comparison") or {"segment_a": "Wealthy", "segment_b": "Non Wealthy", "dimension": "ZONE_TYPE"}
    seg_a = comparison.get("segment_a", "Wealthy")
    seg_b = comparison.get("segment_b", "Non Wealthy")
    dimension = comparison.get("dimension", "ZONE_TYPE")

    ml: pd.DataFrame = artifacts["metrics_long"]
    country = (plan.get("entity_scope") or {}).get("country")
    week = plan.get("time_window", "L0W")
    metric_dn = _id_to_display(metric, artifacts["metrics_cfg"])

    df = _filter_long(ml, metric_dn, country, week)
    if df.empty or dimension not in df.columns:
        return {"tool": "compare_segments", "error": "no data or invalid dimension", "rows": []}

    def seg_stats(seg_val: str) -> dict:
        seg_df = df[df[dimension] == seg_val].dropna(subset=["VALUE"])
        if seg_df.empty:
            return {"value": None, "n_zones": 0, "confidence_level": "insufficient"}
        med = float(seg_df["VALUE"].median())
        n = len(seg_df)
        confidence = "reliable" if n >= 10 else "low_confidence"
        return {"value": round(med, 4), "n_zones": n, "confidence_level": confidence}

    stats_a = seg_stats(seg_a)
    stats_b = seg_stats(seg_b)

    delta = None
    if stats_a["value"] is not None and stats_b["value"] is not None:
        delta = round(stats_a["value"] - stats_b["value"], 4)

    display_name = next(
        (m["display_name"] for m in artifacts["metrics_cfg"]["metrics"] if m["id"] == metric),
        metric
    )

    min_n = min(stats_a["n_zones"], stats_b["n_zones"])
    caveat = _caveat_for(metric, min_n if min_n < 10 else None, artifacts["metrics_cfg"])

    return {
        "tool": "compare_segments",
        "metric": metric,
        "metric_display_name": display_name,
        "week": week,
        "country_filter": country,
        "dimension": dimension,
        "segment_a": {"name": seg_a, **stats_a},
        "segment_b": {"name": seg_b, **stats_b},
        "delta": delta,
        "rows": [
            {"segment": seg_a, **stats_a},
            {"segment": seg_b, **stats_b},
        ],
        "caveat": caveat,
        "chart_type": "side_by_side_bar",
    }


def get_trend(plan: dict, artifacts: dict) -> dict:
    """Return weekly values for a metric/entity across available offsets."""
    metric = plan.get("metric")
    if not metric or metric in SUSPENDED_METRICS:
        return {"tool": "get_trend", "error": "metric required or suspended", "rows": []}

    ml: pd.DataFrame = artifacts["metrics_long"]
    scope = plan.get("entity_scope") or {}
    country = scope.get("country")
    city = scope.get("city")
    zone = scope.get("zone")

    metric_dn = _id_to_display(metric, artifacts["metrics_cfg"])
    df = ml[ml["METRIC"] == metric_dn].copy()
    if country:
        df = df[df["COUNTRY"] == country]
    if city:
        df = df[df["CITY"] == city]
    if zone:
        df = df[df["ZONE"] == zone]

    df = df.dropna(subset=["VALUE"])
    # aggregate by week (median across zones if no zone specified)
    trend = (
        df.groupby(["WEEK_OFFSET", "week_offset_num"])["VALUE"]
        .median()
        .reset_index()
        .sort_values("week_offset_num")
    )

    display_name = next(
        (m["display_name"] for m in artifacts["metrics_cfg"]["metrics"] if m["id"] == metric),
        metric
    )

    rows = trend[["WEEK_OFFSET", "VALUE"]].rename(columns={"WEEK_OFFSET": "week", "VALUE": "value"}).to_dict(orient="records")
    for r in rows:
        r["value"] = round(float(r["value"]), 4)

    return {
        "tool": "get_trend",
        "metric": metric,
        "metric_display_name": display_name,
        "scope": {"country": country, "city": city, "zone": zone},
        "n_weeks": len(rows),
        "rows": rows,
        "caveat": _caveat_for(metric, None, artifacts["metrics_cfg"]),
        "chart_type": "line_chart",
    }


def aggregate_metric(plan: dict, artifacts: dict) -> dict:
    """Simple aggregation: median/mean of metric for given filters."""
    metric = plan.get("metric")
    if not metric or metric in SUSPENDED_METRICS:
        return {"tool": "aggregate_metric", "error": "metric required or suspended", "rows": []}

    ml: pd.DataFrame = artifacts["metrics_long"]
    country = (plan.get("entity_scope") or {}).get("country")
    week = plan.get("time_window", "L0W")

    metric_dn = _id_to_display(metric, artifacts["metrics_cfg"])
    df = _filter_long(ml, metric_dn, country, week).dropna(subset=["VALUE"])
    if df.empty:
        return {"tool": "aggregate_metric", "error": "no data", "rows": []}

    display_name = next(
        (m["display_name"] for m in artifacts["metrics_cfg"]["metrics"] if m["id"] == metric),
        metric
    )

    val = float(df["VALUE"].median())
    n = len(df)
    return {
        "tool": "aggregate_metric",
        "metric": metric,
        "metric_display_name": display_name,
        "week": week,
        "country_filter": country,
        "value": round(val, 4),
        "n_zones": n,
        "aggregation": "median",
        "rows": [{"week": week, "value": round(val, 4), "n_zones": n}],
        "caveat": _caveat_for(metric, n if n < 10 else None, artifacts["metrics_cfg"]),
        "chart_type": "kpi_card",
    }


def generate_hypothesis_candidates(plan: dict, artifacts: dict) -> dict:
    """Return association-based hypothesis from pre-curated possible_driver insights."""
    # prefer insight_candidates (has possible_driver); fallback to top_insights_final
    ic: pd.DataFrame = artifacts.get("insight_candidates", pd.DataFrame())
    if ic.empty or "insight_category" not in ic.columns:
        ic = artifacts["top_insights_final"]

    drivers = ic[ic["insight_category"] == "possible_driver"].copy()
    country = (plan.get("entity_scope") or {}).get("country")
    metric = plan.get("metric")

    if country and "display_entity" in drivers.columns:
        drivers = drivers[drivers["display_entity"].str.match(f"^{country}\\s*\\|", na=False)]
    # Note: possible_driver rows correlate orders vs zone performance — metric_id is always
    # 'orders_total'. Filtering by target metric would eliminate all rows, so skip it.

    drivers = drivers.sort_values("confidence_score", ascending=False).head(5)

    evidence_cols = [c for c in ["display_entity", "metric_display_name", "summary_text", "caveat_text"] if c in drivers.columns]

    return {
        "tool": "generate_hypothesis_candidates",
        "rows": drivers[evidence_cols].to_dict(orient="records") if not drivers.empty else [],
        "n_found": len(drivers),
        "caveat": "Asociación, no causalidad. Correlación entre métricas no implica relación causal.",
        "chart_type": None,
    }


# ── dispatch ─────────────────────────────────────────────────────────────────

TOOL_DISPATCH: dict[str, callable] = {
    "insight_request": route_insight_request,
    "follow_up_scope_refine": route_insight_request,
    "rank": rank_by_metric,
    "compare": compare_segments,
    "trend": get_trend,
    "query": aggregate_metric,
    "hypothesis_request": generate_hypothesis_candidates,
}


_TERMINAL_INTENTS = {
    "greeting", "help", "no_intent", "about_data",
    "explain_result", "explain_metric", "explain_table", "no_intent_guided",
    "clarify_metric", "clarify_country_scope",
    "explain_segments", "available_metrics", "available_metrics_for_scope",
    "explain_signals", "explain_result_simple",
}


def run_tool(plan: dict, artifacts: dict) -> dict:
    intent = plan.get("intent", "insight_request")
    if intent in _TERMINAL_INTENTS:
        return {"tool": "none", "rows": [], "intent": intent}
    fn = TOOL_DISPATCH.get(intent)
    if fn is None:
        return {"tool": "unknown", "error": f"No tool for intent '{intent}'", "rows": []}
    return fn(plan, artifacts)
