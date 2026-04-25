from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List

import pandas as pd

from build_long_tables import build_long_tables
from build_zone_master import build_zone_master
from clean_metrics import clean_metrics
from clean_orders import clean_orders
from common import default_excel_path, get_paths, load_sheet, markdown_table
from load_raw_data import summarize_raw


def _count_non_exact_key_dupes(df: pd.DataFrame, key_cols: List[str]) -> int:
    grouped = df.groupby(key_cols, dropna=False).size()
    return int(grouped[grouped > 1].shape[0])


def _simple_metric_ranges(metrics_long: pd.DataFrame, top_n: int = 20) -> pd.DataFrame:
    agg = (
        metrics_long.groupby("METRIC", dropna=False)["VALUE"]
        .agg(rows="count", missing=lambda s: s.isna().sum(), min="min", p25=lambda s: s.quantile(0.25), median="median", p75=lambda s: s.quantile(0.75), max="max")
        .reset_index()
        .sort_values("rows", ascending=False)
    )
    return agg.head(top_n)


def _build_data_dictionary() -> str:
    return """# Data Dictionary\n\n## Canonical Long Schema\n\n""" + markdown_table(
        ["Column", "Type", "Description"],
        [
            ["COUNTRY", "string", "Country code (standardized with trim + uppercase)."],
            ["CITY", "string", "City name (trim + whitespace normalization)."],
            ["ZONE", "string", "Zone name (trim + whitespace normalization)."],
            ["ZONE_TYPE", "string", "Zone category when available (metrics table)."],
            ["ZONE_PRIORITIZATION", "string", "Zone prioritization bucket when available (metrics table)."],
            ["METRIC", "string", "Metric name from source table."],
            ["metric_group", "string", "Optional structural grouping inferred from METRIC text."],
            ["WEEK_OFFSET", "string", "Weekly relative offset label: L8W..L0W."],
            ["week_offset_num", "int", "Numeric week offset where 0 is current week and 8 is 8 weeks ago."],
            ["VALUE", "float", "Numeric metric/order value after coercion."],
            ["SOURCE_TABLE", "string", "Origin sheet: RAW_INPUT_METRICS or RAW_ORDERS."],
            ["is_current_week", "bool", "True only when WEEK_OFFSET is L0W."],
            ["has_missing_history", "bool", "True if any weekly value is missing in the same entity history."],
            ["_SOURCE_ROW_NUMBER", "int", "Original Excel row index for traceability."],
        ],
    ) + """\n\n## Week Column Mapping Rules\n\n- RAW_INPUT_METRICS weekly columns: L8W_ROLL..L0W_ROLL mapped to canonical L8W..L0W.\n- RAW_ORDERS weekly columns: L8W..L0W mapped directly to canonical L8W..L0W.\n- If source columns follow LxW_VALUE, they are also mapped to canonical LxW.\n\n## Cleaning Rules\n\n- Conservative string cleaning only: trim and internal whitespace normalization.\n- COUNTRY additionally uppercased; CITY/ZONE names are not semantically renamed.\n- Exact duplicate rows are removed and counted.\n- Non-exact duplicates on logical keys are reported, not silently collapsed.\n- Numeric coercion warnings are tracked per weekly canonical column.\n"""


def build_reports(
    reports_dir: Path,
    raw_schema: dict,
    metrics_profile: dict,
    orders_profile: dict,
    long_stats: dict,
    zone_stats: dict,
    processed_dir: Path,
) -> Dict[str, object]:
    metrics_raw = pd.read_parquet(processed_dir / "metrics_raw_cleaned.parquet")
    orders_raw = pd.read_parquet(processed_dir / "orders_raw_cleaned.parquet")
    metrics_long = pd.read_parquet(processed_dir / "metrics_long.parquet")
    orders_long = pd.read_parquet(processed_dir / "orders_long.parquet")
    zone_master = pd.read_parquet(processed_dir / "zone_master.parquet")

    non_exact_dupes_metrics = _count_non_exact_key_dupes(
        metrics_raw,
        ["COUNTRY", "CITY", "ZONE", "ZONE_TYPE", "ZONE_PRIORITIZATION", "METRIC"],
    )
    non_exact_dupes_orders = _count_non_exact_key_dupes(orders_raw, ["COUNTRY", "CITY", "ZONE", "METRIC"])

    missing_metrics = metrics_raw.isna().sum().sort_values(ascending=False)
    missing_orders = orders_raw.isna().sum().sort_values(ascending=False)

    zone_overlap = {
        "zones_total": int(zone_master.shape[0]),
        "zones_both": int((zone_master["COVERAGE_CLASS"] == "BOTH").sum()),
        "zones_only_metrics": int((zone_master["COVERAGE_CLASS"] == "ONLY_METRICS").sum()),
        "zones_only_orders": int((zone_master["COVERAGE_CLASS"] == "ONLY_ORDERS").sum()),
    }

    metrics_per_zone = (
        metrics_long.groupby(["COUNTRY", "CITY", "ZONE"], dropna=False)["METRIC"]
        .nunique()
        .describe(percentiles=[0.25, 0.5, 0.75])
        .to_dict()
    )

    metric_ranges_df = _simple_metric_ranges(metrics_long, top_n=25)

    warnings: List[str] = []
    if metrics_profile["exact_duplicates_removed"] > 0:
        warnings.append(
            f"Metrics had {metrics_profile['exact_duplicates_removed']} exact duplicate rows removed."
        )
    if zone_overlap["zones_only_metrics"] > 0 or zone_overlap["zones_only_orders"] > 0:
        warnings.append("Zone coverage differs between metrics and orders tables.")
    if non_exact_dupes_metrics > 0:
        warnings.append(
            f"Metrics has {non_exact_dupes_metrics} logical keys with multiple records after exact-dedup (review needed)."
        )
    if non_exact_dupes_orders > 0:
        warnings.append(
            f"Orders has {non_exact_dupes_orders} logical keys with multiple records after exact-dedup (review needed)."
        )

    report_summary = {
        "raw_schema": raw_schema,
        "metrics_profile": metrics_profile,
        "orders_profile": orders_profile,
        "long_stats": long_stats,
        "zone_stats": zone_stats,
        "zone_overlap": zone_overlap,
        "non_exact_duplicate_keys": {
            "metrics": non_exact_dupes_metrics,
            "orders": non_exact_dupes_orders,
        },
        "warnings": warnings,
    }

    (reports_dir / "data_quality_report.json").write_text(
        json.dumps(report_summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    dq_lines: List[str] = ["# Data Quality Report", "", "## 1) Sanity Check Inicial", ""]
    dq_lines.append(
        markdown_table(
            ["Tabla", "Filas", "Columnas", "Blank rows", "Duplicados exactos en crudo"],
            [
                [
                    "RAW_INPUT_METRICS",
                    raw_schema["sheets"]["RAW_INPUT_METRICS"]["shape"][0],
                    raw_schema["sheets"]["RAW_INPUT_METRICS"]["shape"][1],
                    raw_schema["sheets"]["RAW_INPUT_METRICS"]["blank_rows"],
                    raw_schema["sheets"]["RAW_INPUT_METRICS"]["exact_duplicates"],
                ],
                [
                    "RAW_ORDERS",
                    raw_schema["sheets"]["RAW_ORDERS"]["shape"][0],
                    raw_schema["sheets"]["RAW_ORDERS"]["shape"][1],
                    raw_schema["sheets"]["RAW_ORDERS"]["blank_rows"],
                    raw_schema["sheets"]["RAW_ORDERS"]["exact_duplicates"],
                ],
                [
                    "RAW_SUMMARY",
                    raw_schema["sheets"]["RAW_SUMMARY"]["shape"][0],
                    raw_schema["sheets"]["RAW_SUMMARY"]["shape"][1],
                    raw_schema["sheets"]["RAW_SUMMARY"]["blank_rows"],
                    raw_schema["sheets"]["RAW_SUMMARY"]["exact_duplicates"],
                ],
            ],
        )
    )

    dq_lines += ["", "## 2) Estandarización de Columnas", ""]
    mapping_rows = []
    for k, v in sorted(metrics_profile["week_column_mapping"].items()):
        mapping_rows.append(["RAW_INPUT_METRICS", k, v])
    for k, v in sorted(orders_profile["week_column_mapping"].items()):
        mapping_rows.append(["RAW_ORDERS", k, v])
    dq_lines.append(markdown_table(["SOURCE_TABLE", "ORIGINAL_COLUMN", "CANONICAL_COLUMN"], mapping_rows))

    dq_lines += ["", "## 3) Limpieza y Tipado", ""]
    dq_lines.append(
        markdown_table(
            ["Tabla", "Duplicados exactos removidos", "Coerciones fallidas semanales"],
            [
                [
                    "metrics_raw_cleaned",
                    metrics_profile["exact_duplicates_removed"],
                    sum(metrics_profile["numeric_coercion_failures"].values()),
                ],
                [
                    "orders_raw_cleaned",
                    orders_profile["exact_duplicates_removed"],
                    sum(orders_profile["numeric_coercion_failures"].values()),
                ],
            ],
        )
    )

    dq_lines += ["", "## 4) Exploración Inicial Estructural", ""]
    dq_lines.append(
        markdown_table(
            ["Indicador", "Valor"],
            [
                ["metrics_raw_cleaned shape", str(tuple(metrics_raw.shape))],
                ["orders_raw_cleaned shape", str(tuple(orders_raw.shape))],
                ["metrics_long shape", str(tuple(metrics_long.shape))],
                ["orders_long shape", str(tuple(orders_long.shape))],
                ["Países (metrics)", int(metrics_raw["COUNTRY"].nunique(dropna=True))],
                ["Países (orders)", int(orders_raw["COUNTRY"].nunique(dropna=True))],
                ["Ciudades (metrics)", int(metrics_raw["CITY"].nunique(dropna=True))],
                ["Ciudades (orders)", int(orders_raw["CITY"].nunique(dropna=True))],
                ["Zonas (metrics)", int(metrics_raw[["COUNTRY", "CITY", "ZONE"]].drop_duplicates().shape[0])],
                ["Zonas (orders)", int(orders_raw[["COUNTRY", "CITY", "ZONE"]].drop_duplicates().shape[0])],
                ["Métricas únicas", int(metrics_raw["METRIC"].nunique(dropna=True))],
                ["Week offsets metrics", ", ".join(sorted(metrics_long["WEEK_OFFSET"].dropna().unique()))],
                ["Week offsets orders", ", ".join(sorted(orders_long["WEEK_OFFSET"].dropna().unique()))],
            ],
        )
    )

    dq_lines += ["", "### Faltantes por columna (top)", ""]
    top_missing_rows = []
    for col, val in missing_metrics.head(12).items():
        top_missing_rows.append(["metrics_raw_cleaned", col, int(val)])
    for col, val in missing_orders.head(12).items():
        top_missing_rows.append(["orders_raw_cleaned", col, int(val)])
    dq_lines.append(markdown_table(["Tabla", "Columna", "Missing"], top_missing_rows))

    dq_lines += ["", "### Overlap de zonas", ""]
    dq_lines.append(markdown_table(["Métrica", "Valor"], [[k, v] for k, v in zone_overlap.items()]))

    dq_lines += ["", "### Métricas por zona (distribución)", ""]
    dq_lines.append(
        markdown_table(
            ["Estadístico", "Valor"],
            [[k, round(float(v), 3)] for k, v in metrics_per_zone.items()],
        )
    )

    dq_lines += ["", "### Resumen simple de rangos por métrica (top 25 por volumen)", ""]
    range_rows = []
    for _, row in metric_ranges_df.iterrows():
        range_rows.append(
            [
                row["METRIC"],
                int(row["rows"]),
                int(row["missing"]),
                round(float(row["min"]), 6) if pd.notna(row["min"]) else "",
                round(float(row["p25"]), 6) if pd.notna(row["p25"]) else "",
                round(float(row["median"]), 6) if pd.notna(row["median"]) else "",
                round(float(row["p75"]), 6) if pd.notna(row["p75"]) else "",
                round(float(row["max"]), 6) if pd.notna(row["max"]) else "",
            ]
        )
    dq_lines.append(
        markdown_table(
            ["METRIC", "rows", "missing", "min", "p25", "median", "p75", "max"],
            range_rows,
        )
    )

    dq_lines += ["", "## 5) Warnings para análisis posterior", ""]
    if warnings:
        for w in warnings:
            dq_lines.append(f"- {w}")
    else:
        dq_lines.append("- No critical warnings detected in initial structural profiling.")

    dq_lines += ["", "## 6) Decisiones y Trade-offs", "", "- Se removieron solo duplicados exactos para mantener enfoque conservador y auditable.", "- No se imputaron faltantes ni se resolvieron duplicados lógicos ambiguos automáticamente.", "- No se asignaron fechas calendario; se preservó el modelo temporal por offsets L8W..L0W."]

    (reports_dir / "data_quality_report.md").write_text("\n".join(dq_lines), encoding="utf-8")
    (reports_dir / "data_dictionary.md").write_text(_build_data_dictionary(), encoding="utf-8")

    return report_summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Run end-to-end data prep and initial profiling.")
    parser.add_argument("--excel-path", type=str, default=None)
    parser.add_argument("--project-root", type=str, default=None)
    args = parser.parse_args()

    paths = get_paths(args.project_root)
    excel_path = Path(args.excel_path) if args.excel_path else default_excel_path(paths)

    raw_schema = summarize_raw(excel_path, paths.reports_dir / "raw_schema_summary.json")
    metrics_profile = clean_metrics(excel_path, paths.processed_dir)
    orders_profile = clean_orders(excel_path, paths.processed_dir)
    long_stats = build_long_tables(paths.processed_dir)
    zone_stats = build_zone_master(paths.processed_dir)

    summary = build_reports(
        paths.reports_dir,
        raw_schema,
        metrics_profile,
        orders_profile,
        long_stats,
        zone_stats,
        paths.processed_dir,
    )

    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
