from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
EXTERNAL_ROOT = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else PROJECT_ROOT
load_dotenv(EXTERNAL_ROOT / ".env")

VAT_CERTIFICATION_DAYS = 360
INVALIDATION_WARNING_RATE = 0.02
THREE_WAY_MATCH_TOLERANCE = 0.0
REIMBURSEMENT_TARGET_DAYS = 5

LLM_ENABLED = os.getenv("LLM_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai-compatible").strip() or "openai-compatible"
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.openai.com/v1").strip() or "https://api.openai.com/v1"
LLM_API_KEY = os.getenv("LLM_API_KEY", "").strip()
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "60").strip() or "60")
LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2").strip() or "0.2")
LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "1200").strip() or "1200")
LLM_FALLBACK_TO_RULES = os.getenv("LLM_FALLBACK_TO_RULES", "true").strip().lower() in {"1", "true", "yes", "on"}
RUN_MODE = os.getenv("DEMO_RUN_MODE", "demo").strip().lower() or "demo"


def is_full_mode() -> bool:
    return RUN_MODE == "full"


def is_demo_mode() -> bool:
    return RUN_MODE != "full"


def is_llm_runtime_enabled() -> bool:
    return is_full_mode() and LLM_ENABLED


def get_missing_llm_config() -> list[str]:
    missing: list[str] = []
    if not LLM_ENABLED:
        missing.append("LLM_ENABLED=true")
    if not LLM_API_KEY:
        missing.append("LLM_API_KEY")
    return missing
