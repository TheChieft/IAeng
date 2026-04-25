from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Tuple

import numpy as np
import pandas as pd

WEEK_COL_REGEX = re.compile(r"^L(?P<offset>[0-8])W(?:_(?:ROLL|VALUE))?$", re.IGNORECASE)


def normalize_col(col: str) -> str:
    return re.sub(r"\s+", "_", str(col).strip()).upper()


def normalize_text(value: object, upper: bool = False) -> object:
    if pd.isna(value):
        return np.nan
    text = re.sub(r"\s+", " ", str(value).strip())
    return text.upper() if upper else text


def load_sheet(excel_path: Path, sheet_name: str) -> pd.DataFrame:
    df = pd.read_excel(excel_path, sheet_name=sheet_name)
    df.columns = [normalize_col(c) for c in df.columns]
    return df


def detect_week_columns(columns) -> Dict[str, str]:
    """Return mapping original_col -> canonical L{n}W."""
    mapping: Dict[str, str] = {}
    for col in columns:
        m = WEEK_COL_REGEX.match(str(col).strip().upper())
        if m:
            mapping[col] = f"L{m.group('offset')}W"
    return mapping


def coerce_numeric(series: pd.Series) -> Tuple[pd.Series, int]:
    converted = pd.to_numeric(series, errors="coerce")
    failures = int(series.notna().sum() - converted.notna().sum())
    return converted, failures


def write_parquet(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path
