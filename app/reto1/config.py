"""App configuration and paths."""
import os
from pathlib import Path

def find_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "data" / "processed").exists() and (parent / "notebooks").exists():
            return parent
    return p.parents[2]

ROOT = find_root()
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data" / "processed"
REPORTS_DIR = ROOT / "reports" / "reto1"

# LLM config — optional; app works without it
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "none")  # "openai" | "anthropic" | "none"
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-4-6")

USE_LLM = LLM_PROVIDER != "none" and bool(LLM_API_KEY)

WEEK_OPTIONS = ["L0W", "L1W", "L2W", "L3W", "L4W", "L8W"]
SEVERITY_COLORS = {"HIGH": "#FF4B4B", "MEDIUM": "#FFA500", "LOW": "#4CAF50"}

SUSPENDED_METRICS = {"lead_penetration"}
LOWER_IS_BETTER = {"restaurants_markdowns_gmv"}
LOW_COVERAGE_PEER = {"turbo_adoption"}
