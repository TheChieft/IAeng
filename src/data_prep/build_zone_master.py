from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict

import pandas as pd


def build_zone_master(processed_dir: Path, write_csv: bool = False) -> Dict[str, object]:
    metrics_raw = pd.read_parquet(processed_dir / "metrics_raw_cleaned.parquet")
    orders_raw = pd.read_parquet(processed_dir / "orders_raw_cleaned.parquet")

    zone_key = ["COUNTRY", "CITY", "ZONE"]

    metrics_zones = (
        metrics_raw.groupby(zone_key, dropna=False)
        .agg(
            METRIC_COUNT=("METRIC", "nunique"),
            ZONE_TYPE_NUNIQUE=("ZONE_TYPE", "nunique"),
            ZONE_PRIORITIZATION_NUNIQUE=("ZONE_PRIORITIZATION", "nunique"),
            ZONE_TYPE=("ZONE_TYPE", "first"),
            ZONE_PRIORITIZATION=("ZONE_PRIORITIZATION", "first"),
        )
        .reset_index()
    )
    metrics_zones["IN_METRICS"] = True

    orders_zones = orders_raw[zone_key].drop_duplicates().copy()
    orders_zones["IN_ORDERS"] = True

    zone_master = metrics_zones.merge(orders_zones, on=zone_key, how="outer")
    zone_master["IN_METRICS"] = zone_master["IN_METRICS"].fillna(False)
    zone_master["IN_ORDERS"] = zone_master["IN_ORDERS"].fillna(False)

    zone_master["METRIC_COUNT"] = zone_master["METRIC_COUNT"].fillna(0).astype(int)
    zone_master["ZONE_TYPE_CONFLICT"] = zone_master["ZONE_TYPE_NUNIQUE"].fillna(0).gt(1)
    zone_master["ZONE_PRIORITIZATION_CONFLICT"] = zone_master["ZONE_PRIORITIZATION_NUNIQUE"].fillna(0).gt(1)

    zone_master["COVERAGE_CLASS"] = "ONLY_ORDERS"
    zone_master.loc[zone_master["IN_METRICS"] & ~zone_master["IN_ORDERS"], "COVERAGE_CLASS"] = "ONLY_METRICS"
    zone_master.loc[zone_master["IN_METRICS"] & zone_master["IN_ORDERS"], "COVERAGE_CLASS"] = "BOTH"

    zone_master = zone_master.sort_values(zone_key).reset_index(drop=True)

    if write_csv:
        zone_master.to_csv(processed_dir / "zone_master.csv", index=False)
    zone_master.to_parquet(processed_dir / "zone_master.parquet", index=False)

    return {
        "zone_master_rows": int(zone_master.shape[0]),
        "zones_in_both": int((zone_master["COVERAGE_CLASS"] == "BOTH").sum()),
        "zones_only_metrics": int((zone_master["COVERAGE_CLASS"] == "ONLY_METRICS").sum()),
        "zones_only_orders": int((zone_master["COVERAGE_CLASS"] == "ONLY_ORDERS").sum()),
        "zone_type_conflicts": int(zone_master["ZONE_TYPE_CONFLICT"].sum()),
        "zone_prioritization_conflicts": int(zone_master["ZONE_PRIORITIZATION_CONFLICT"].sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build zone master coverage table.")
    parser.add_argument("--project-root", type=str, default=None)
    parser.add_argument("--write-csv", action="store_true")
    args = parser.parse_args()

    from common import get_paths

    paths = get_paths(args.project_root)
    summary = build_zone_master(paths.processed_dir, write_csv=args.write_csv)
    print(summary)


if __name__ == "__main__":
    main()
