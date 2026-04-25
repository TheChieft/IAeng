from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import EXPECTED_SHEETS, default_excel_path, get_paths, load_sheet


def summarize_raw(excel_path: Path, output_path: Path) -> dict:
    summary = {"excel_path": str(excel_path), "sheets": {}}
    for sheet in EXPECTED_SHEETS:
        df = load_sheet(excel_path, sheet)
        summary["sheets"][sheet] = {
            "shape": [int(df.shape[0]), int(df.shape[1])],
            "columns": list(df.columns),
            "blank_rows": int(df.isna().all(axis=1).sum()),
            "exact_duplicates": int(df.duplicated().sum()),
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Load and validate raw workbook sheets.")
    parser.add_argument("--excel-path", type=str, default=None)
    parser.add_argument("--project-root", type=str, default=None)
    args = parser.parse_args()

    paths = get_paths(args.project_root)
    excel_path = Path(args.excel_path) if args.excel_path else default_excel_path(paths)
    summary_path = paths.reports_dir / "raw_schema_summary.json"

    summary = summarize_raw(excel_path, summary_path)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
