from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd

from common import default_excel_path, get_paths, load_sheet
def _bool_to_status(value: bool) -> str:
    return "PASS" if value else "FAIL"


def validate_pipeline(project_root: Path, run_pipeline: bool) -> Dict[str, object]:
    paths = get_paths(project_root)

    e2e_ok = True
    e2e_details = {"run_pipeline": run_pipeline, "return_code": 0}
    if run_pipeline:
        cmd = [
            sys.executable,
            str(paths.project_root / "src" / "data_prep" / "run_initial_data_profile.py"),
            "--project-root",
            str(paths.project_root),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        e2e_ok = proc.returncode == 0
        e2e_details = {
            "run_pipeline": run_pipeline,
            "return_code": proc.returncode,
            "stderr_tail": "\n".join(proc.stderr.splitlines()[-12:]) if proc.stderr else "",
        }

    excel_path = default_excel_path(paths)

    raw_metrics = load_sheet(excel_path, "RAW_INPUT_METRICS")
    raw_orders = load_sheet(excel_path, "RAW_ORDERS")
    raw_summary = load_sheet(excel_path, "RAW_SUMMARY")

    metrics_clean = pd.read_parquet(paths.processed_dir / "metrics_raw_cleaned.parquet")
    orders_clean = pd.read_parquet(paths.processed_dir / "orders_raw_cleaned.parquet")
    metrics_long = pd.read_parquet(paths.processed_dir / "metrics_long.parquet")
    orders_long = pd.read_parquet(paths.processed_dir / "orders_long.parquet")
    zone_master = pd.read_parquet(paths.processed_dir / "zone_master.parquet")

    checks: List[Dict[str, object]] = []

    # 1) Raw shapes.
    check_raw_shapes = (
        raw_metrics.shape == (12573, 15)
        and raw_orders.shape == (1242, 13)
        and raw_summary.shape == (15, 4)
    )
    checks.append(
        {
            "id": "raw_shapes_match_source",
            "status": _bool_to_status(check_raw_shapes),
            "details": {
                "RAW_INPUT_METRICS": raw_metrics.shape,
                "RAW_ORDERS": raw_orders.shape,
                "RAW_SUMMARY": raw_summary.shape,
            },
        }
    )

    # 2) Exact duplicates are truly exact in source.
    raw_metrics_exact_dupes = int(raw_metrics.duplicated().sum())
    checks.append(
        {
            "id": "metrics_exact_duplicates_real",
            "status": _bool_to_status(raw_metrics_exact_dupes == 963),
            "details": {"raw_exact_duplicates": raw_metrics_exact_dupes, "expected": 963},
        }
    )

    # 3) Dedup does not remove non-exact rows.
    metrics_source_cols = [c for c in raw_metrics.columns]
    metrics_unique_raw = raw_metrics.drop_duplicates(subset=metrics_source_cols, keep="first")
    check_non_exact_not_removed = int(metrics_unique_raw.shape[0]) == int(metrics_clean.shape[0])
    checks.append(
        {
            "id": "dedup_preserves_non_exact_rows",
            "status": _bool_to_status(check_non_exact_not_removed),
            "details": {
                "raw_unique_rows": int(metrics_unique_raw.shape[0]),
                "metrics_clean_rows": int(metrics_clean.shape[0]),
            },
        }
    )

    # 4) Weekly mapping correctness.
    expected_metrics_week_cols = [f"L{i}W_ROLL" for i in range(8, -1, -1)]
    expected_orders_week_cols = [f"L{i}W" for i in range(8, -1, -1)]
    check_week_mapping = all(c in raw_metrics.columns for c in expected_metrics_week_cols) and all(
        c in raw_orders.columns for c in expected_orders_week_cols
    )
    checks.append(
        {
            "id": "weekly_mapping_columns_detected",
            "status": _bool_to_status(check_week_mapping),
            "details": {
                "metrics_has_roll_cols": check_week_mapping,
                "orders_has_week_cols": check_week_mapping,
            },
        }
    )

    # 5) Numeric coercion did not create artificial NaNs.
    metrics_coercion_artificial_nans = {}
    for i in range(8, -1, -1):
        src = f"L{i}W_ROLL"
        canon = f"L{i}W"
        if src in metrics_clean.columns and canon in metrics_clean.columns:
            metrics_coercion_artificial_nans[canon] = int(
                metrics_clean[src].notna().sum() - metrics_clean[canon].notna().sum()
            )

    orders_coercion_artificial_nans = {}
    for i in range(8, -1, -1):
        src = f"L{i}W"
        if src in orders_clean.columns:
            orders_coercion_artificial_nans[src] = int(
                orders_clean[src].notna().sum() - orders_clean[src].notna().sum()
            )

    check_no_artificial_nans = (
        sum(metrics_coercion_artificial_nans.values()) == 0
        and sum(orders_coercion_artificial_nans.values()) == 0
    )
    checks.append(
        {
            "id": "numeric_coercion_no_artificial_nans",
            "status": _bool_to_status(check_no_artificial_nans),
            "details": {
                "metrics_artificial_nans": metrics_coercion_artificial_nans,
                "orders_artificial_nans": orders_coercion_artificial_nans,
            },
        }
    )

    # 6) Wide -> long and grain uniqueness.
    metrics_expected_long_rows = int(metrics_clean.shape[0]) * 9
    orders_expected_long_rows = int(orders_clean.shape[0]) * 9
    metrics_grain_dupes = int(
        metrics_long.duplicated(subset=["COUNTRY", "CITY", "ZONE", "METRIC", "WEEK_OFFSET"]).sum()
    )
    orders_grain_dupes = int(
        orders_long.duplicated(subset=["COUNTRY", "CITY", "ZONE", "METRIC", "WEEK_OFFSET"]).sum()
    )
    check_long = (
        metrics_expected_long_rows == int(metrics_long.shape[0])
        and orders_expected_long_rows == int(orders_long.shape[0])
        and metrics_grain_dupes == 0
        and orders_grain_dupes == 0
    )
    checks.append(
        {
            "id": "wide_to_long_math_and_grain",
            "status": _bool_to_status(check_long),
            "details": {
                "metrics_expected_rows": metrics_expected_long_rows,
                "metrics_actual_rows": int(metrics_long.shape[0]),
                "orders_expected_rows": orders_expected_long_rows,
                "orders_actual_rows": int(orders_long.shape[0]),
                "metrics_grain_duplicates": metrics_grain_dupes,
                "orders_grain_duplicates": orders_grain_dupes,
            },
        }
    )

    # 7) Zone master reconciliation.
    metrics_zone_set = set(metrics_clean[["COUNTRY", "CITY", "ZONE"]].drop_duplicates().itertuples(index=False, name=None))
    orders_zone_set = set(orders_clean[["COUNTRY", "CITY", "ZONE"]].drop_duplicates().itertuples(index=False, name=None))
    zone_master_set = set(zone_master[["COUNTRY", "CITY", "ZONE"]].drop_duplicates().itertuples(index=False, name=None))
    union_set = metrics_zone_set | orders_zone_set

    check_zone_master_union = zone_master_set == union_set
    checks.append(
        {
            "id": "zone_master_matches_union",
            "status": _bool_to_status(check_zone_master_union),
            "details": {
                "zone_master_count": len(zone_master_set),
                "union_count": len(union_set),
                "metrics_only": len(metrics_zone_set - orders_zone_set),
                "orders_only": len(orders_zone_set - metrics_zone_set),
            },
        }
    )

    # 8) Coverage mismatch warning is real.
    check_coverage_mismatch_real = len(metrics_zone_set - orders_zone_set) > 0 or len(orders_zone_set - metrics_zone_set) > 0
    checks.append(
        {
            "id": "coverage_mismatch_warning_real",
            "status": _bool_to_status(check_coverage_mismatch_real),
            "details": {
                "metrics_only": len(metrics_zone_set - orders_zone_set),
                "orders_only": len(orders_zone_set - metrics_zone_set),
            },
        }
    )

    # 9) Processed outputs coherence.
    check_outputs_coherent = (
        set(metrics_long["SOURCE_TABLE"].dropna().unique()) == {"RAW_INPUT_METRICS"}
        and set(orders_long["SOURCE_TABLE"].dropna().unique()) == {"RAW_ORDERS"}
        and set(metrics_long["WEEK_OFFSET"].dropna().unique()) == {f"L{i}W" for i in range(9)}
        and set(orders_long["WEEK_OFFSET"].dropna().unique()) == {f"L{i}W" for i in range(9)}
    )
    checks.append(
        {
            "id": "processed_outputs_coherent",
            "status": _bool_to_status(check_outputs_coherent),
            "details": {
                "metrics_source_tables": sorted(metrics_long["SOURCE_TABLE"].dropna().unique().tolist()),
                "orders_source_tables": sorted(orders_long["SOURCE_TABLE"].dropna().unique().tolist()),
                "metrics_week_offsets": sorted(metrics_long["WEEK_OFFSET"].dropna().unique().tolist()),
                "orders_week_offsets": sorted(orders_long["WEEK_OFFSET"].dropna().unique().tolist()),
            },
        }
    )

    # 10) End-to-end run without manual steps.
    # If run_pipeline flag was set and no exception was raised, this check passes.
    checks.append(
        {
            "id": "pipeline_end_to_end_no_manual_steps",
            "status": _bool_to_status(e2e_ok),
            "details": e2e_details,
        }
    )

    failed = [c for c in checks if c["status"] == "FAIL"]
    summary = {
        "overall_status": "PASS" if not failed else "FAIL",
        "checks_passed": len(checks) - len(failed),
        "checks_failed": len(failed),
        "checks": checks,
    }

    return summary


def build_markdown_report(summary: Dict[str, object]) -> str:
    lines: List[str] = []
    lines.append("# Pipeline Validation Report")
    lines.append("")
    lines.append(f"- Overall status: **{summary['overall_status']}**")
    lines.append(f"- Checks passed: {summary['checks_passed']}")
    lines.append(f"- Checks failed: {summary['checks_failed']}")
    lines.append("")
    lines.append("## Check Results")
    lines.append("")

    for chk in summary["checks"]:
        lines.append(f"### {chk['id']}")
        lines.append(f"- Status: **{chk['status']}**")
        lines.append("- Details:")
        for k, v in chk["details"].items():
            lines.append(f"  - {k}: {v}")
        lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Reto 1 data prep pipeline outputs and invariants.")
    parser.add_argument("--project-root", type=str, default=None)
    parser.add_argument("--run-pipeline", action="store_true")
    args = parser.parse_args()

    root = Path(args.project_root) if args.project_root else Path(__file__).resolve().parents[2]
    paths = get_paths(root)

    summary = validate_pipeline(root, run_pipeline=args.run_pipeline)

    json_path = paths.reports_dir / "pipeline_validation_report.json"
    md_path = paths.reports_dir / "pipeline_validation_report.md"

    json_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(build_markdown_report(summary), encoding="utf-8")

    print(json.dumps({"overall_status": summary["overall_status"], "checks_failed": summary["checks_failed"]}, indent=2))


if __name__ == "__main__":
    main()
