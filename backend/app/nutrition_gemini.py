"""Estimate recipe nutrition with Google Gemini (works without USDA key)."""

from __future__ import annotations

import json
import re
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.config import GEMINI_API_KEY, GEMINI_MODEL, GEMINI_MODEL_FALLBACKS
from app.schemas import Nutrition, NutritionReport

_SYSTEM = """You estimate total nutrition for a home-cooking recipe from its ingredient list.
Rules:
- Use typical USDA-style values for each ingredient and quantity.
- total_* fields = entire recipe (all ingredients combined).
- per_serving_* = total divided by servings (use servings given, else guess 4).
- Be realistic for home cooking (include oil, sauces, etc. when listed).
- Respond with JSON only, no markdown.
JSON keys: total_calories, total_protein_g, total_carbs_g, total_fat_g, total_fiber_g,
per_serving_calories, per_serving_protein_g, per_serving_carbs_g, per_serving_fat_g, per_serving_fiber_g, servings_used
All numbers are floats or null."""

_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "total_calories": {"type": "number", "nullable": True},
        "total_protein_g": {"type": "number", "nullable": True},
        "total_carbs_g": {"type": "number", "nullable": True},
        "total_fat_g": {"type": "number", "nullable": True},
        "total_fiber_g": {"type": "number", "nullable": True},
        "per_serving_calories": {"type": "number", "nullable": True},
        "per_serving_protein_g": {"type": "number", "nullable": True},
        "per_serving_carbs_g": {"type": "number", "nullable": True},
        "per_serving_fat_g": {"type": "number", "nullable": True},
        "per_serving_fiber_g": {"type": "number", "nullable": True},
        "servings_used": {"type": "integer", "nullable": True},
    },
}


def _models() -> list[str]:
    out: list[str] = []
    if GEMINI_MODEL:
        out.append(GEMINI_MODEL)
    for m in GEMINI_MODEL_FALLBACKS.split(","):
        m = m.strip()
        if m and m not in out:
            out.append(m)
    return out or ["gemini-2.0-flash-lite"]


def _parse_json(text: str) -> dict[str, Any]:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.I)
        t = re.sub(r"\s*```$", "", t)
    return json.loads(t)


def _n(data: dict, *keys: str) -> float | None:
    for k in keys:
        v = data.get(k)
        if v is not None:
            try:
                return float(v)
            except (ValueError, TypeError):
                pass
    return None


def estimate_with_gemini(ingredients: list[str], servings: int | None) -> NutritionReport | None:
    if not GEMINI_API_KEY or not ingredients:
        return None

    ing_block = "\n".join(f"- {x}" for x in ingredients[:40])
    srv_hint = f"{servings}" if servings else "unknown (estimate)"
    prompt = (
        f"Estimate total and per-serving nutrition for this recipe.\n"
        f"Stated servings: {srv_hint}\n\nIngredients:\n{ing_block}"
    )

    client = genai.Client(api_key=GEMINI_API_KEY)
    for model in _models():
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=_SYSTEM,
                    temperature=0.1,
                    response_mime_type="application/json",
                    response_schema=_SCHEMA,
                ),
            )
            raw = (resp.text or "").strip()
            if not raw:
                continue
            data = _parse_json(raw)
            srv = int(data.get("servings_used") or servings or 1)
            srv = max(srv, 1)

            total = Nutrition(
                calories=_n(data, "total_calories"),
                protein_g=_n(data, "total_protein_g"),
                carbs_g=_n(data, "total_carbs_g"),
                fat_g=_n(data, "total_fat_g"),
                fiber_g=_n(data, "total_fiber_g"),
            )
            per = Nutrition(
                calories=_n(data, "per_serving_calories"),
                protein_g=_n(data, "per_serving_protein_g"),
                carbs_g=_n(data, "per_serving_carbs_g"),
                fat_g=_n(data, "per_serving_fat_g"),
                fiber_g=_n(data, "per_serving_fiber_g"),
            )
            # Fill gaps from the other side.
            if total.calories is None and per.calories is not None:
                total.calories = round(per.calories * srv, 1)
            if per.calories is None and total.calories is not None:
                per.calories = round(total.calories / srv, 1)
            for key in ("protein_g", "carbs_g", "fat_g", "fiber_g"):
                tv, pv = getattr(total, key), getattr(per, key)
                if tv is None and pv is not None:
                    setattr(total, key, round(pv * srv, 1))
                if pv is None and tv is not None:
                    setattr(per, key, round(tv / srv, 1))

            if total.calories is None and per.calories is None:
                continue

            return NutritionReport(
                per_serving=per,
                total=total,
                servings=srv,
                matched=len(ingredients),
                source=f"Gemini estimate ({model})",
                notes=["AI-estimated from ingredients — approximate; verify before tracking."],
            )
        except (genai_errors.ClientError, genai_errors.ServerError, ValueError, json.JSONDecodeError):
            continue
    return None
