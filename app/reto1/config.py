"""App configuration and paths.

Loads .env from project root via python-dotenv (if present).
All LLM config is optional — app works without it.
"""
import os
from pathlib import Path

# ── project root ─────────────────────────────────────────────────────────────

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

# ── load .env (silent if missing) ────────────────────────────────────────────

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", override=False)  # override=False: real env vars win
except ImportError:
    pass  # python-dotenv optional

# ── LLM config ───────────────────────────────────────────────────────────────

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "none").lower()   # "gemini" | "none"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
USE_LLM = os.getenv("USE_LLM", "false").lower() in ("true", "1", "yes")

HAS_GEMINI_KEY = bool(GEMINI_API_KEY)
LLM_ACTIVE = USE_LLM and LLM_PROVIDER == "gemini" and HAS_GEMINI_KEY

# ── app constants ─────────────────────────────────────────────────────────────

WEEK_OPTIONS = ["L0W", "L1W", "L2W", "L3W", "L4W", "L8W"]
SEVERITY_COLORS = {"HIGH": "#FF4B4B", "MEDIUM": "#FFA500", "LOW": "#4CAF50"}

SUSPENDED_METRICS = {"lead_penetration"}
LOWER_IS_BETTER = {"restaurants_markdowns_gmv"}
LOW_COVERAGE_PEER = {"turbo_adoption"}

LLM_TIMEOUT_SECONDS = 8
