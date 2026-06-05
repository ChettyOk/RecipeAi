"""Use Google Gemini (Google AI Studio / free-tier Gemini API) to structure recipe text into JSON."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MODEL_FALLBACKS
from app.schemas import DIETARY_FLAGS, RecipeBase

SYSTEM = f"""You extract ONE cooking recipe from text taken from a social cooking video.
The text may include the title, the description/caption, on-screen text (OCR), and an audio transcript.
Rules:
- title: concise recipe name suitable for a recipe card (not clickbait).
- ingredients: each item one string, include quantity + unit when stated (e.g. "2 cups flour").
- steps: ordered prep/cook instructions; one clear action per string.
- prep_time_min / cook_time_min: integers in minutes if stated or clearly implied, else null.
- servings: integer if stated or clearly implied, else null.
- dietary_flags: subset of {DIETARY_FLAGS} that clearly apply, else [].
- Only use information supported by the provided text. If there is no real recipe, use title "Could not parse recipe" with empty ingredients/steps.
- Respond with JSON only, no markdown fences.
JSON schema: {{"title": string, "ingredients": string[], "steps": string[], "prep_time_min": int|null, "cook_time_min": int|null, "servings": int|null, "dietary_flags": string[]}}
"""

_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "ingredients": {"type": "array", "items": {"type": "string"}},
        "steps": {"type": "array", "items": {"type": "string"}},
        "prep_time_min": {"type": "integer", "nullable": True},
        "cook_time_min": {"type": "integer", "nullable": True},
        "servings": {"type": "integer", "nullable": True},
        "dietary_flags": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title", "ingredients", "steps"],
}


class GeminiUpstreamError(Exception):
    """Gemini / Google API returned a client-visible error; HTTP status is chosen in the route."""

    __slots__ = ("status_code",)

    def __init__(self, message: str, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass
class AiExtractionOutcome:
    draft: RecipeBase
    model_used: str


def _models_to_try() -> list[str]:
    ordered: list[str] = []
    if GEMINI_MODEL:
        ordered.append(GEMINI_MODEL)
    for part in GEMINI_MODEL_FALLBACKS.split(","):
        m = part.strip()
        if m and m not in ordered:
            ordered.append(m)
    return ordered or ["gemini-2.0-flash-lite"]


def _parse_json_from_model(text: str) -> dict[str, Any]:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE)
        t = re.sub(r"\s*```$", "", t)
    return json.loads(t)


def _coerce_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (ValueError, TypeError):
        return None


def _draft_from_parsed(data: dict[str, Any]) -> RecipeBase:
    title = str(data.get("title") or "").strip() or "Imported recipe"
    ingredients = data.get("ingredients") if isinstance(data.get("ingredients"), list) else []
    steps = data.get("steps") if isinstance(data.get("steps"), list) else []
    flags = data.get("dietary_flags") if isinstance(data.get("dietary_flags"), list) else []
    return RecipeBase(
        title=title,
        ingredients=[str(x) for x in ingredients],
        steps=[str(x) for x in steps],
        prep_time_min=_coerce_int(data.get("prep_time_min")),
        cook_time_min=_coerce_int(data.get("cook_time_min")),
        servings=_coerce_int(data.get("servings")),
        dietary_flags=[str(x) for x in flags],
    )


def _quota_error_message(exc: genai_errors.ClientError) -> str:
    msg = getattr(exc, "message", None) or str(exc)
    low = msg.lower()
    if "limit: 0" in low or "free_tier" in low:
        return (
            "Gemini free-tier quota for this model is 0 (model may be unavailable on your key or region). "
            "Try GEMINI_MODEL=gemini-2.0-flash-lite in backend/.env, wait and retry, check https://ai.dev/rate-limit , "
            "or uncheck \u201cUse Gemini\u201d for heuristic-only import."
        )
    return (
        "Gemini quota or rate limit (429). Free tier has caps \u2014 wait and retry, try "
        "GEMINI_MODEL=gemini-2.0-flash-lite, or see https://ai.google.dev/gemini-api/docs/rate-limits"
    )


def _generate_once(client: "genai.Client", model: str, user_msg: str) -> RecipeBase:
    response = client.models.generate_content(
        model=model,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            temperature=0.2,
            response_mime_type="application/json",
            response_schema=_RESPONSE_SCHEMA,
        ),
    )
    try:
        raw = (response.text or "").strip()
    except ValueError as e:
        raise RuntimeError(
            "Gemini did not return usable text (content may be blocked or empty). Try heuristic import."
        ) from e
    if not raw:
        raise RuntimeError("Empty model response")
    return _draft_from_parsed(_parse_json_from_model(raw))


def structure_recipe(context_text: str) -> AiExtractionOutcome:
    """Turn combined recipe text (captions + transcript + on-screen text) into a structured draft."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) is not set \u2014 create a free key at "
            "https://aistudio.google.com/app/apikey"
        )
    if not context_text.strip():
        raise ValueError("No usable text (no title, description, captions, transcript, or on-screen text).")

    client = genai.Client(api_key=GEMINI_API_KEY)
    user_msg = (
        "Extract the recipe from the following content.\n\n"
        f"{context_text}\n\n"
        "Return JSON only with keys title, ingredients, steps, prep_time_min, cook_time_min, servings, dietary_flags."
    )

    models = _models_to_try()
    last_quota: genai_errors.ClientError | None = None

    for model in models:
        try:
            draft = _generate_once(client, model, user_msg)
            return AiExtractionOutcome(draft=draft, model_used=model)
        except genai_errors.ClientError as e:
            code = int(getattr(e, "code", 0) or 0)
            msg = (getattr(e, "message", None) or str(e)).lower()
            if code in (400, 401, 403) and (
                "api key" in msg or "api_key_invalid" in msg or "permission" in msg
            ):
                raise GeminiUpstreamError(
                    "Gemini rejected the API key or access (check GEMINI_API_KEY in backend/.env). "
                    "Create a key at https://aistudio.google.com/app/apikey",
                    401 if code != 403 else 403,
                ) from e
            if code == 404 or ("not found" in msg and "model" in msg):
                continue
            if code == 429 or "resource exhausted" in msg or "quota" in msg:
                last_quota = e
                continue
            raise RuntimeError(f"Gemini client error ({code}) on {model}: {e}") from e
        except genai_errors.ServerError as e:
            raise RuntimeError(f"Gemini server error on {model}: {e}") from e

    if last_quota is not None:
        raise GeminiUpstreamError(_quota_error_message(last_quota), 429) from last_quota
    raise RuntimeError(f"Gemini failed for all models tried: {', '.join(models)}")
