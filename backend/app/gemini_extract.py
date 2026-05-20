"""Use Google Gemini (Google AI Studio / free-tier Gemini API) to structure video text into a recipe draft."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MODEL_FALLBACKS
from app.schemas import RecipeBase
from app.video_context import VideoContext

SYSTEM = """You extract one cooking recipe from text taken from a social video (title, description, and/or subtitles).
Rules:
- title: concise recipe name suitable for a recipe card (not clickbait).
- ingredients: each item one string with amounts/units when stated in the source.
- steps: ordered prep/cook steps; one clear action per string.
- Only use information supported by the provided text. If there is no real recipe, return a sensible title like "Could not parse recipe" with empty ingredients and steps, or minimal notes in steps explaining why.
- Respond with JSON only, no markdown fences. Schema: {"title": string, "ingredients": string[], "steps": string[]}
"""


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


def _draft_from_parsed(data: dict[str, Any]) -> RecipeBase:
    title = str(data.get("title") or "").strip() or "Imported recipe"
    ingredients = data.get("ingredients")
    steps = data.get("steps")
    if not isinstance(ingredients, list):
        ingredients = []
    if not isinstance(steps, list):
        steps = []
    ingredients = [str(x).strip() for x in ingredients if str(x).strip()]
    steps = [str(x).strip() for x in steps if str(x).strip()]
    return RecipeBase.model_validate(
        {
            "title": title,
            "ingredients": ingredients,
            "steps": steps,
        }
    )


def _quota_error_message(exc: genai_errors.ClientError) -> str:
    msg = getattr(exc, "message", None) or str(exc)
    low = msg.lower()
    if "limit: 0" in low or "free_tier" in low:
        return (
            "Gemini free-tier quota for this model is 0 (model may be unavailable on your key or region). "
            "Try GEMINI_MODEL=gemini-2.0-flash-lite in backend/.env, wait and retry, check https://ai.dev/rate-limit , "
            "or uncheck “Use Gemini” for heuristic-only import."
        )
    if "retry in" in low or "retrydelay" in low:
        return (
            f"Gemini rate limit (429): {msg}. Wait a minute and retry, or use heuristic import (uncheck Use Gemini)."
        )
    return (
        "Gemini quota or rate limit (429). Free tier has caps — wait and retry, try GEMINI_MODEL=gemini-2.0-flash-lite, "
        "or see https://ai.google.dev/gemini-api/docs/rate-limits"
    )


def _generate_once(client: genai.Client, model: str, user_msg: str) -> RecipeBase:
    response = client.models.generate_content(
        model=model,
        contents=user_msg,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM,
            temperature=0.2,
            response_mime_type="application/json",
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


def extract_recipe_draft(ctx: VideoContext) -> AiExtractionOutcome:
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY (or GOOGLE_API_KEY) is not set — create a free key at https://aistudio.google.com/app/apikey"
        )

    block = ctx.as_prompt_block()
    if not block.strip():
        raise ValueError("No usable text from this URL (no title, description, or captions).")

    client = genai.Client(api_key=GEMINI_API_KEY)
    user_msg = (
        "Extract the recipe from the following content.\n\n"
        f"{block}\n\n"
        "Return JSON with keys title, ingredients, steps only."
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
                "api key" in msg
                or "api_key_invalid" in msg
                or "invalid argument" in msg
                or "permission" in msg
            ):
                raise GeminiUpstreamError(
                    "Gemini rejected the API key or access (check GEMINI_API_KEY in backend/.env). "
                    "Create a key at https://aistudio.google.com/app/apikey",
                    401 if code != 403 else 403,
                ) from e
            if code == 404 or "not found" in msg and "model" in msg:
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
