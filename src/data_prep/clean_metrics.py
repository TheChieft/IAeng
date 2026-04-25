from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List

import pandas as pd

from common import (
    coerce_numeric,
    default_excel_path,
    detect_week_columns,
    get_paths,
    load_sheet,
    normalize_text,
    safe_write,
)

METRICS_SHEET = "RAW_INPUT_METRICS"
TEXT_DIM_COLS = ["COUNTRY", "CITY", "ZONE", "ZONE_TYPE", "ZONE_PRIORITIZATION", "METRIC"]


def clean_metrics(excel_path: Path, output_dir: Path) -> Dict[str, object]:
    raw_df = load_sheet(excel_path, METRICS_SHEET)
    source_columns = list(raw_df.columns)

    profile: Dict[str, object] = {
        "source_table": METRICS_SHEET,
        "raw_shape": [int(raw_df.shape[0]), int(raw_df.shape[1])],
        "blank_rows_removed": 0,
        "exact_duplicates_removed": 0,
        "week_column_mapping": {},
        "numeric_coercion_failures": {},
        "missing_by_column_after_clean": {},
    }

    raw_df = raw_df.copy()
    raw_df["_SOURCE_ROW_NUMBER"] = raw_df.index + 2

    blank_rows = raw_df.isna().all(axis=1)
    profile["blank_rows_removed"] = int(blank_rows.sum())
    df = raw_df.loc[~blank_rows].copy()

    exact_dup_mask = df.duplicated(subset=source_columns, keep="first")
    profile["exact_duplicates_removed"] = int(exact_dup_mask.sum())
    df = df.loc[~exact_dup_mask].copy()

    for col in TEXT_DIM_COLS:
        if col not in df.columns:
            continue
        original_col = f"{col}_ORIGINAL"
        df[original_col] = df[col]
        df[col] = df[col].map(lambda x: normalize_text(x, upper=(col == "COUNTRY")))

    week_mapping = detect_week_columns(df.columns)
    profile["week_column_mapping"] = dict(sorted(week_mapping.items()))

    for src_col, canonical_col in week_mapping.items():
        numeric_series, failures = coerce_numeric(df[src_col])
        df[canonical_col] = numeric_series
        profile["numeric_coercion_failures"][canonical_col] = (
            profile["numeric_coercion_failures"].get(canonical_col, 0) + failures
        )

    canonical_week_cols = [f"L{i}W" for i in range(8, -1, -1)]
    present_week_cols = [c for c in canonical_week_cols if c in df.columns]

    df["SOURCE_TABLE"] = METRICS_SHEET

    ordered_cols: List[str] = [
        "COUNTRY",
        "CITY",
        "ZONE",
        "ZONE_TYPE",
        "ZONE_PRIORITIZATION",
        "METRIC",
        "SOURCE_TABLE",
        "_SOURCE_ROW_NUMBER",
    ]
    ordered_cols += [f"{c}_ORIGINAL" for c in TEXT_DIM_COLS if f"{c}_ORIGINAL" in df.columns]

    original_week_cols = [c for c in df.columns if c.endswith("_ROLL") or c.endswith("_VALUE")]
    ordered_cols += sorted(original_week_cols)
    ordered_cols += present_week_cols

    remainder = [c for c in df.columns if c not in ordered_cols]
    ordered_cols += remainder

    cleaned = df[ordered_cols].copy()
    profile["clean_shape"] = [int(cleaned.shape[0]), int(cleaned.shape[1])]
    profile["missing_by_column_after_clean"] = {
        c: int(v) for c, v in cleaned.isna().sum().sort_values(ascending=False).items() if int(v) > 0
    }

    safe_write(
        cleaned,
        output_dir / "metrics_raw_cleaned.csv",
        output_dir / "metrics_raw_cleaned.parquet",
    )

    return profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Clean RAW_INPUT_METRICS sheet.")
    parser.add_argument("--excel-path", type=str, default=None)
    parser.add_argument("--project-root", type=str, default=None)
    args = parser.parse_args()

    paths = get_paths(args.project_root)
    excel_path = Path(args.excel_path) if args.excel_path else default_excel_path(paths)

    profile = clean_metrics(excel_path, paths.processed_dir)
    print(profile)


if __name__ == "__main__":
    main()
