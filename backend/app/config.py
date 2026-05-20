import os
from pathlib import Path

from dotenv import load_dotenv

_backend_dir = Path(__file__).resolve().parent.parent
load_dotenv(_backend_dir.parent / ".env", override=True)
load_dotenv(_backend_dir / ".env", override=True)

BACKEND_DIR = _backend_dir


def _clean_secret(value: str) -> str:
    """Strip BOM, quotes, and accidental newlines from .env secrets (common .env editor issues)."""
    if not value:
        return ""
    s = value.strip()
    if s.startswith("\ufeff"):
        s = s.lstrip("\ufeff")
    if len(s) >= 2 and ((s[0] == s[-1] == '"') or (s[0] == s[-1] == "'")):
        s = s[1:-1].strip()
    s = s.replace("\r", "").replace("\n", "")
    return s.strip()


# Google AI Studio / Gemini API (free tier): https://aistudio.google.com/app/apikey
GEMINI_API_KEY: str = _clean_secret(os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", ""))
# Default flash-lite: better free-tier availability than gemini-2.0-flash for many keys.
GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite").strip()
GEMINI_MODEL_FALLBACKS: str = os.getenv(
    "GEMINI_MODEL_FALLBACKS",
    "gemini-2.0-flash-lite,gemini-1.5-flash,gemini-2.0-flash",
).strip()
GEMINI_FALLBACK_ON_QUOTA: bool = os.getenv("GEMINI_FALLBACK_ON_QUOTA", "true").strip().lower() in (
    "1",
    "true",
    "yes",
    "on",
)

# YouTube often blocks unauthenticated yt-dlp; pass cookies (see README / .env.example).
YTDLP_COOKIES_FILE: str = os.getenv("YTDLP_COOKIES_FILE", "").strip()
YTDLP_COOKIES_FROM_BROWSER: str = os.getenv("YTDLP_COOKIES_FROM_BROWSER", "").strip()

# Comma-separated yt-dlp YouTube player_client fallbacks (empty = built-in default list). Set to "off" to disable.
YTDLP_YOUTUBE_PLAYER_CLIENTS: str = os.getenv("YTDLP_YOUTUBE_PLAYER_CLIENTS", "").strip()
