from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Paths:
    project_root: Path
    raw_dir: Path
    interim_dir: Path
    processed_dir: Path
    reports_dir: Path


def find_root(start: Path | None = None) -> Path:
    start = (start or Path.cwd()).resolve()
    for p in [start] + list(start.parents):
        if (p / "data" / "processed").exists() and (p / "notebooks").exists():
            return p
    raise FileNotFoundError(f"Cannot infer project root from {start}")


def get_paths(root: str | Path | None = None) -> Paths:
    r = Path(root) if root else find_root()
    return Paths(
        project_root=r,
        raw_dir=r / "data" / "raw",
        interim_dir=r / "data" / "interim",
        processed_dir=r / "data" / "processed",
        reports_dir=r / "reports",
    )


def default_excel(paths: Paths) -> Path:
    candidates = sorted(paths.raw_dir.glob("*.xlsx"))
    if not candidates:
        raise FileNotFoundError(f"No .xlsx found in {paths.raw_dir}")
    return candidates[0]
