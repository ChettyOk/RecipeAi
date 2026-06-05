"""Gemini multimodal helpers: transcribe audio and read on-screen text from video frames.

Keeps everything on the Google AI free tier (no OpenAI Whisper / GPT-4o Vision needed).
All functions degrade gracefully: on any error they return "" so the pipeline can continue.
"""

from __future__ import annotations

from pathlib import Path

from google import genai
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MODEL_FALLBACKS

_AUDIO_MIME = {
    ".mp3": "audio/mp3",
    ".m4a": "audio/mp4",
    ".aac": "audio/aac",
    ".wav": "audio/wav",
    ".ogg": "audio/ogg",
    ".flac": "audio/flac",
}
_IMAGE_MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}

MAX_TRANSCRIPT_CHARS = 18_000
MAX_OCR_CHARS = 8_000


def _models() -> list[str]:
    out: list[str] = []
    if GEMINI_MODEL:
        out.append(GEMINI_MODEL)
    for m in GEMINI_MODEL_FALLBACKS.split(","):
        m = m.strip()
        if m and m not in out:
            out.append(m)
    return out or ["gemini-2.0-flash-lite"]


def _generate(parts: list[object], *, prompt: str) -> str:
    if not GEMINI_API_KEY:
        return ""
    client = genai.Client(api_key=GEMINI_API_KEY)
    contents = [prompt, *parts]
    last_err: Exception | None = None
    for model in _models():
        try:
            resp = client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(temperature=0.0),
            )
            return (resp.text or "").strip()
        except Exception as e:  # noqa: BLE001 — best-effort, degrade to ""
            last_err = e
            continue
    if last_err is not None:
        return ""
    return ""


def transcribe_audio(audio_path: Path) -> str:
    """Transcribe spoken instructions from an audio file using Gemini. Returns "" on failure."""
    suffix = audio_path.suffix.lower()
    mime = _AUDIO_MIME.get(suffix)
    if mime is None or not audio_path.is_file():
        return ""
    try:
        data = audio_path.read_bytes()
    except OSError:
        return ""
    part = types.Part.from_bytes(data=data, mime_type=mime)
    prompt = (
        "Transcribe the spoken words in this cooking video audio. "
        "Return only the transcript text, no commentary."
    )
    text = _generate([part], prompt=prompt)
    return text[:MAX_TRANSCRIPT_CHARS]


def read_frames_text(frame_paths: list[Path]) -> str:
    """OCR/read on-screen text (ingredients, measurements) from video frames. Returns "" on failure."""
    parts: list[object] = []
    for p in frame_paths:
        mime = _IMAGE_MIME.get(p.suffix.lower())
        if mime is None or not p.is_file():
            continue
        try:
            parts.append(types.Part.from_bytes(data=p.read_bytes(), mime_type=mime))
        except OSError:
            continue
    if not parts:
        return ""
    prompt = (
        "These are still frames from a cooking video. Extract any on-screen text relevant to the recipe "
        "(ingredient names, quantities, units, step captions). Return only the extracted text, deduplicated, "
        "one item per line. If there is no recipe text, return an empty response."
    )
    text = _generate(parts, prompt=prompt)
    return text[:MAX_OCR_CHARS]
