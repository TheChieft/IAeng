from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from common import get_paths, safe_write, sorted_canonical_week_cols, week_offset_num


def _infer_metric_group(metric: object) -> object:
    if metric is None:
        return pd.NA
    if isinstance(metric, float) and pd.isna(metric):
        return pd.NA
    text = str(metric)
    if ">" in text:
        return text.split(">", 1)[0].strip()
    return text.split(" ", 1)[0].strip()


def _make_long(df: pd.DataFrame, id_vars: List[str], value_name: str = "VALUE") -> Tuple[pd.DataFrame, Dict[str, int]]:
    week_cols = [c for c in df.columns if c.startswith("L") and c.endswith("W") and len(c) == 3]
    week_cols = sorted_canonical_week_cols(week_cols)

    long_df = df.melt(
        id_vars=id_vars,
        value_vars=week_cols,
        var_name="WEEK_OFFSET",
        value_name=value_name,
    )
    long_df["week_offset_num"] = long_df["WEEK_OFFSET"].map(week_offset_num)
    long_df["is_current_week"] = long_df["week_offset_num"].eq(0)

    stats = {"input_rows": int(df.shape[0]), "output_rows": int(long_df.shape[0]), "week_cols": len(week_cols)}
    return long_df, stats


def build_long_tables(processed_dir: Path) -> Dict[str, object]:
    metrics_raw = pd.read_parquet(processed_dir / "metrics_raw_cleaned.parquet")
    orders_raw = pd.read_parquet(processed_dir / "orders_raw_cleaned.parquet")

    metrics_id_vars = [
        "COUNTRY",
        "CITY",
        "ZONE",
        "ZONE_TYPE",
        "ZONE_PRIORITIZATION",
        "METRIC",
        "SOURCE_TABLE",
        "_SOURCE_ROW_NUMBER",
    ]
    metrics_id_vars = [c for c in metrics_id_vars if c in metrics_raw.columns]

    orders_id_vars = ["COUNTRY", "CITY", "ZONE", "METRIC", "SOURCE_TABLE", "_SOURCE_ROW_NUMBER"]
    orders_id_vars = [c for c in orders_id_vars if c in orders_raw.columns]

    metrics_long, metrics_stats = _make_long(metrics_raw, metrics_id_vars)
    metrics_long["metric_group"] = metrics_long["METRIC"].map(_infer_metric_group)

    metrics_hist_key = [c for c in ["COUNTRY", "CITY", "ZONE", "METRIC"] if c in metrics_long.columns]
    metrics_long["has_missing_history"] = (
        metrics_long.groupby(metrics_hist_key)["VALUE"].transform(lambda s: s.isna().any())
    )

    metrics_long = metrics_long[
        [
            "COUNTRY",
            "CITY",
            "ZONE",
            "ZONE_TYPE",
            "ZONE_PRIORITIZATION",
            "METRIC",
            "metric_group",
            "WEEK_OFFSET",
            "week_offset_num",
            "VALUE",
            "SOURCE_TABLE",
            "is_current_week",
            "has_missing_history",
            "_SOURCE_ROW_NUMBER",
        ]
    ]

    orders_long, orders_stats = _make_long(orders_raw, orders_id_vars)
    orders_hist_key = [c for c in ["COUNTRY", "CITY", "ZONE", "METRIC"] if c in orders_long.columns]
    orders_long["has_missing_history"] = orders_long.groupby(orders_hist_key)["VALUE"].transform(
        lambda s: s.isna().any()
    )

    orders_long = orders_long[
        [
            "COUNTRY",
            "CITY",
            "ZONE",
            "METRIC",
            "WEEK_OFFSET",
            "week_offset_num",
            "VALUE",
            "SOURCE_TABLE",
            "is_current_week",
            "has_missing_history",
            "_SOURCE_ROW_NUMBER",
        ]
    ]

    safe_write(metrics_long, processed_dir / "metrics_long.csv", processed_dir / "metrics_long.parquet")
    safe_write(orders_long, processed_dir / "orders_long.csv", processed_dir / "orders_long.parquet")

    return {"metrics_long": metrics_stats, "orders_long": orders_stats}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build long/tidy weekly tables.")
    parser.add_argument("--project-root", type=str, default=None)
    args = parser.parse_args()

    paths = get_paths(args.project_root)
    stats = build_long_tables(paths.processed_dir)
    print(stats)


if __name__ == "__main__":
    main()
