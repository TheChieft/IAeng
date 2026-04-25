from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd

EXPECTED_SHEETS = ["RAW_INPUT_METRICS", "RAW_ORDERS", "RAW_SUMMARY"]
WEEK_COL_REGEX = re.compile(r"^L(?P<offset>[0-8])W(?:_(?:ROLL|VALUE))?$", re.IGNORECASE)


@dataclass(frozen=True)
class Paths:
    project_root: Path
    raw_dir: Path
    processed_dir: Path
    reports_dir: Path


def get_paths(project_root: str | Path | None = None) -> Paths:
    root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
    return Paths(
        project_root=root,
        raw_dir=root / "data" / "raw",
        processed_dir=root / "data" / "processed",
        reports_dir=root / "reports",
    )


def default_excel_path(paths: Paths) -> Path:
    candidates = sorted(paths.raw_dir.glob("*.xlsx"))
    if not candidates:
        raise FileNotFoundError(f"No .xlsx files found in {paths.raw_dir}")
    return candidates[0]


def normalize_column_name(col: str) -> str:
    return re.sub(r"\s+", "_", str(col).strip()).upper()


def normalize_text(value: object, upper: bool = False) -> object:
    if pd.isna(value):
        return np.nan
    text = re.sub(r"\s+", " ", str(value).strip())
    return text.upper() if upper else text


def load_sheet(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    df.columns = [normalize_column_name(c) for c in df.columns]
    return df


def detect_week_columns(columns: Iterable[str]) -> Dict[str, str]:
    """
    Returns mapping: original_week_column -> canonical_week_column (L8W..L0W).
    """
    mapping: Dict[str, str] = {}
    for col in columns:
        match = WEEK_COL_REGEX.match(col.strip().upper())
        if not match:
            continue
        offset = int(match.group("offset"))
        mapping[col] = f"L{offset}W"
    return mapping


def sorted_canonical_week_cols(week_columns: Iterable[str]) -> List[str]:
    def _key(col: str) -> int:
        match = re.match(r"^L([0-8])W$", col)
        if not match:
            return 99
        return int(match.group(1))

    return sorted(set(week_columns), key=_key, reverse=True)


def week_offset_num(week_offset: str) -> int:
    match = re.match(r"^L([0-8])W$", str(week_offset).upper())
    if not match:
        raise ValueError(f"Invalid week offset: {week_offset}")
    return int(match.group(1))


def coerce_numeric(series: pd.Series) -> Tuple[pd.Series, int]:
    converted = pd.to_numeric(series, errors="coerce")
    failures = int(series.notna().sum() - converted.notna().sum())
    return converted, failures


def safe_write(
    df: pd.DataFrame,
    csv_path: Path,
    parquet_path: Path,
    write_csv: bool = False,
) -> None:
    if write_csv:
        csv_path.parent.mkdir(parents=True, exist_ok=True)
    parquet_path.parent.mkdir(parents=True, exist_ok=True)
    if write_csv:
        df.to_csv(csv_path, index=False)
    df.to_parquet(parquet_path, index=False)


def markdown_table(headers: List[str], rows: List[List[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x) for x in row) + " |")
    return "\n".join(lines)
