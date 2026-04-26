# ── config.py — Centralized Environment Configuration ──
# Fails loudly on startup if ANY required variable is missing.
# This prevents silent runtime errors in production.

import os
import sys
from dotenv import load_dotenv

# Load .env file from the backend directory (same level as this file)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

# ── Required Environment Variables ──
# Each one is validated at import time. If any is missing, the process exits.

_REQUIRED_VARS = {
    "PAGE_ACCESS_TOKEN": "Long-lived Page Access Token from Meta Graph API Explorer",
    "APP_SECRET": "App Secret from Meta App Dashboard → Settings → Basic",
    "VERIFY_TOKEN": "Arbitrary string you set in Meta webhook config — must match exactly",
    "INSTAGRAM_ACCOUNT_ID": "Your Instagram Professional Account ID (numeric)",
    "GEMINI_API_KEY": "Google AI Studio API key for Gemini 1.5 Flash — get from https://aistudio.google.com/app/apikeys",
    "BOT_USERNAME": "Instagram @username of the bot account (without the @ symbol)",
}

def _load_required(var_name: str, description: str) -> str:
    """Load a required env var or exit with a clear error message."""
    value = os.getenv(var_name)
    if not value:
        print(
            f"\n❌ FATAL: Missing required environment variable: {var_name}\n"
            f"   Description: {description}\n"
            f"   → Set it in backend/.env or export it in your shell.\n",
            file=sys.stderr,
        )
        sys.exit(1)
    return value

# ── Exported Config Values ──
# These are module-level constants loaded once at startup.
# PAGE_ACCESS_TOKEN is mutable — token_refresh.py updates it in-memory.

PAGE_ACCESS_TOKEN: str = _load_required("PAGE_ACCESS_TOKEN", _REQUIRED_VARS["PAGE_ACCESS_TOKEN"])
APP_SECRET: str = _load_required("APP_SECRET", _REQUIRED_VARS["APP_SECRET"])
VERIFY_TOKEN: str = _load_required("VERIFY_TOKEN", _REQUIRED_VARS["VERIFY_TOKEN"])
INSTAGRAM_ACCOUNT_ID: str = _load_required("INSTAGRAM_ACCOUNT_ID", _REQUIRED_VARS["INSTAGRAM_ACCOUNT_ID"])

# ── AI Overlord — Required Config ──
GEMINI_API_KEY: str = _load_required("GEMINI_API_KEY", _REQUIRED_VARS["GEMINI_API_KEY"])
BOT_USERNAME: str = _load_required("BOT_USERNAME", _REQUIRED_VARS["BOT_USERNAME"])

# ── Optional Config ──
# Meta Graph API base URL — pinned to v19.0 as specified
GRAPH_API_BASE = os.getenv("GRAPH_API_BASE", "https://graph.facebook.com/v19.0")

# Port for uvicorn (used by main.py if running directly)
PORT: int = int(os.getenv("PORT", "8000"))

# Log level
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

# Token refresh interval in days (APScheduler uses this)
TOKEN_REFRESH_DAYS: int = int(os.getenv("TOKEN_REFRESH_DAYS", "50"))

# ── AI Overlord — Optional Config ──
# Cooldown between AI requests per user (seconds) — prevents spam and Meta API abuse
AI_COOLDOWN_SECONDS: int = int(os.getenv("AI_COOLDOWN_SECONDS", "30"))

# Pollinations.ai base URL — externalized so it can be swapped without code changes.
# Pollinations is free and requires no API key — the URL IS the image.
POLLINATIONS_BASE_URL: str = os.getenv("POLLINATIONS_BASE_URL", "https://image.pollinations.ai")

# ── Configure Gemini SDK Globally ──
# Safe to call at import time — sets the API key for all google.generativeai calls.
# This must happen before any GenerativeModel is instantiated (in ai_engine.py).
import google.generativeai as genai
genai.configure(api_key=GEMINI_API_KEY)
