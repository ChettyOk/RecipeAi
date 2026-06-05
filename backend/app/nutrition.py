"""Compute recipe nutrition using multiple sources (best available wins).

Priority:
  1. Creator-stated macros in video description/caption (most accurate when present)
  2. Per-ingredient USDA FoodData Central (if USDA_API_KEY) + built-in reference fallback per line
  3. Google Gemini ingredient estimate (if ENABLE_GEMINI_NUTRITION=true)
"""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request

from app.config import ENABLE_GEMINI_NUTRITION, GEMINI_API_KEY, USDA_API_KEY
from app.schemas import Nutrition, NutritionReport

_SEARCH_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

_WEIGHT_G = {
    "g": 1.0, "gram": 1.0, "grams": 1.0,
    "kg": 1000.0, "kilogram": 1000.0,
    "oz": 28.3495, "ounce": 28.3495, "ounces": 28.3495,
    "lb": 453.592, "lbs": 453.592, "pound": 453.592, "pounds": 453.592,
}
_VOLUME_ML = {
    "ml": 1.0, "milliliter": 1.0, "millilitre": 1.0,
    "l": 1000.0, "liter": 1000.0, "litre": 1000.0,
    "tsp": 4.92892, "teaspoon": 4.92892, "teaspoons": 4.92892,
    "tbsp": 14.7868, "tbs": 14.7868, "tablespoon": 14.7868, "tablespoons": 14.7868,
    "cup": 240.0, "cups": 240.0, "pint": 473.176, "quart": 946.353,
    "fl": 29.5735, "floz": 29.5735,
}
_UNICODE_FRACTIONS = {
    "¼": 0.25, "½": 0.5, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3,
    "⅛": 0.125, "⅜": 0.375, "⅝": 0.625, "⅞": 0.875,
}
_NUM = {"calories": "208", "protein_g": "203", "fat_g": "204", "carbs_g": "205", "fiber_g": "291"}
_NAME_HINT = {
    "calories": "energy", "protein_g": "protein", "fat_g": "total lipid",
    "carbs_g": "carbohydrate", "fiber_g": "fiber",
}
_QTY_RE = re.compile(r"^\s*([\d¼½¾⅓⅔⅛⅜⅝⅞./\s-]+)?\s*([a-zA-Z]+)?\.?\s+(.*)$")


def _parse_number(token: str) -> float | None:
    token = token.strip()
    if not token:
        return None
    total = 0.0
    matched = False
    lead = ""
    for ch in token:
        if ch in _UNICODE_FRACTIONS:
            total += _UNICODE_FRACTIONS[ch]
            matched = True
        else:
            lead += ch
    lead = lead.strip()
    if lead:
        for part in lead.split():
            if "/" in part:
                try:
                    num, den = part.split("/", 1)
                    total += float(num) / float(den)
                    matched = True
                    continue
                except (ValueError, ZeroDivisionError):
                    return None if not matched else total
            try:
                total += float(part)
                matched = True
            except ValueError:
                return None if not matched else total
    return total if matched else None


def parse_ingredient(line: str) -> tuple[float | None, str | None, str]:
    s = re.sub(r"\(.*?\)", "", line).strip()
    s = re.sub(r"^[-•*·▪►]\s*", "", s)
    m = _QTY_RE.match(s)
    if not m:
        return None, None, s.strip()
    qty_raw, unit_raw, rest = m.group(1), m.group(2), m.group(3) or ""
    qty = _parse_number(qty_raw) if qty_raw else None
    unit = None
    if unit_raw:
        u = unit_raw.lower().rstrip(".")
        if u in _WEIGHT_G or u in _VOLUME_ML:
            unit = u
        else:
            rest = f"{unit_raw} {rest}".strip()
    name = rest.strip(" ,.-") or s
    return qty, unit, name


def to_grams(qty: float | None, unit: str | None) -> float | None:
    if qty is None or unit is None:
        return None
    if unit in _WEIGHT_G:
        return qty * _WEIGHT_G[unit]
    if unit in _VOLUME_ML:
        return qty * _VOLUME_ML[unit]
    return None


def _http_get_json(url: str, timeout: int = 12) -> dict | None:
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None


def _search_food(name: str) -> dict | None:
    from app.nutrition_ingredient import search_queries

    for query in search_queries(name):
        params = urllib.parse.urlencode(
            {
                "query": query,
                "pageSize": "3",
                "dataType": "Foundation,SR Legacy,Survey (FNDDS)",
                "api_key": USDA_API_KEY,
            }
        )
        data = _http_get_json(f"{_SEARCH_URL}?{params}")
        if not data:
            continue
        foods = data.get("foods") or []
        if foods:
            return foods[0]
    return None


def _per_100g(food: dict) -> Nutrition:
    out = {k: None for k in _NUM}
    for n in food.get("foodNutrients") or []:
        num = str(n.get("nutrientNumber") or "")
        nm = str(n.get("nutrientName") or "").lower()
        val = n.get("value")
        if val is None:
            continue
        for key in _NUM:
            if num == _NUM[key] or _NAME_HINT[key] in nm:
                if out[key] is None:
                    try:
                        out[key] = float(val)
                    except (ValueError, TypeError):
                        pass
    return Nutrition(**out)


def _estimate_line_usda(search_name: str, grams: float) -> Nutrition | None:
    food = _search_food(search_name)
    if not food:
        return None
    per100 = _per_100g(food)
    if all(getattr(per100, k) is None for k in _NUM):
        return None
    factor = grams / 100.0
    return Nutrition(
        calories=round((per100.calories or 0) * factor, 2),
        protein_g=round((per100.protein_g or 0) * factor, 2) if per100.protein_g else None,
        carbs_g=round((per100.carbs_g or 0) * factor, 2) if per100.carbs_g else None,
        fat_g=round((per100.fat_g or 0) * factor, 2) if per100.fat_g else None,
        fiber_g=round((per100.fiber_g or 0) * factor, 2) if per100.fiber_g else None,
    )


def _add_nutrition(acc: dict[str, float], n: Nutrition) -> None:
    for key in _NUM:
        v = getattr(n, key)
        if v is not None:
            acc[key] = acc.get(key, 0.0) + v


def compute_ingredient_nutrition(
    ingredients: list[str],
    servings: int | None,
) -> NutritionReport:
    """Per-ingredient nutrition: USDA when keyed, local table fallback, best coverage."""
    from app.nutrition_ingredient import resolve_ingredient_line
    from app.nutrition_local import estimate_line

    srv = max(servings or 1, 1)
    report = NutritionReport(servings=srv)
    totals: dict[str, float] = {}
    usda_hits = 0
    local_hits = 0
    approx_volume = False

    for line in ingredients[:40]:
        resolved = resolve_ingredient_line(line)
        if resolved is None:
            stripped = line.strip()
            if stripped and not stripped.endswith(":"):
                report.unmatched.append(line)
            continue

        if resolved.approx:
            approx_volume = True

        contrib: Nutrition | None = None
        if USDA_API_KEY:
            usda_n = _estimate_line_usda(resolved.search_name, resolved.grams)
            if usda_n is not None:
                contrib = usda_n
                usda_hits += 1

        if contrib is None:
            local_n = estimate_line(
                resolved.search_name,
                resolved.grams,
                raw_line=resolved.line,
                qty=resolved.qty,
            )
            if local_n is not None:
                contrib = local_n
                local_hits += 1

        if contrib is not None:
            _add_nutrition(totals, contrib)
            report.matched += 1
        else:
            report.unmatched.append(line)

    if not totals.get("calories"):
        report.source = "Built-in estimates"
        return report

    if usda_hits and local_hits:
        report.source = "USDA FoodData Central + built-in averages"
    elif usda_hits:
        report.source = "USDA FoodData Central"
    else:
        report.source = "Built-in estimates (USDA-style averages)"

    report.total = _round_nutrition(totals)
    report.per_serving = Nutrition(
        **{k: round((totals.get(k) or 0) / srv, 1) for k in _NUM}
    )

    if approx_volume:
        report.notes.append("Volume amounts (cups/tsp) approximated at ~1 g/ml where noted.")
    if usda_hits:
        report.notes.append(f"{usda_hits} ingredient(s) matched via USDA FoodData Central.")
    if local_hits:
        report.notes.append(f"{local_hits} ingredient(s) from built-in reference averages.")
    if report.unmatched:
        report.notes.append(
            f"{len(report.unmatched)} line(s) could not be quantified — add weights/units or paste video macros."
        )
    if not USDA_API_KEY:
        report.notes.append(
            "Tip: set USDA_API_KEY in backend/.env for more accurate per-ingredient lookups (free at fdc.nal.usda.gov)."
        )
    return report


def _round_nutrition(totals: dict[str, float]) -> Nutrition:
    def _r(x: float | None) -> float | None:
        return round(x, 1) if x is not None else None

    return Nutrition(**{k: _r(totals.get(k)) for k in _NUM})


def _has_calories(report: NutritionReport | None) -> bool:
    if report is None:
        return False
    return report.total.calories is not None or report.per_serving.calories is not None


def estimate_yield_g(ingredients: list[str]) -> float | None:
    """Sum ingredient weights (g) and volume (ml≈g) to estimate total recipe yield."""
    from app.nutrition_ingredient import resolve_ingredient_line

    total = 0.0
    counted = 0
    for line in ingredients[:40]:
        resolved = resolve_ingredient_line(line)
        if resolved and resolved.grams > 0:
            total += resolved.grams
            counted += 1
    if counted < 2 or total < 80:
        return None
    return round(total, 1)


def attach_yield(report: NutritionReport, ingredients: list[str]) -> NutritionReport:
    """Add estimated_yield_g and per_serving_weight_g for gram/ml portion scaling."""
    yield_g = estimate_yield_g(ingredients)
    srv = max(report.servings or 1, 1)
    report.estimated_yield_g = yield_g
    report.per_serving_weight_g = round(yield_g / srv, 1) if yield_g else None
    if yield_g and report.per_serving_weight_g:
        unit = report.serving_label or "serving"
        report.notes.append(
            f"One {unit} ≈ {report.per_serving_weight_g:.0f} g (from ingredient amounts) — "
            "use g/ml/oz to log your exact portion."
        )
    return report


def _sync_totals_from_per_serving(report: NutritionReport, servings: int) -> None:
    """Keep per-serving as source of truth; recompute total for the given serving count."""
    p = report.per_serving
    report.servings = servings
    report.total = Nutrition(
        calories=round(p.calories * servings, 1) if p.calories else None,
        protein_g=round(p.protein_g * servings, 1) if p.protein_g else None,
        carbs_g=round(p.carbs_g * servings, 1) if p.carbs_g else None,
        fat_g=round(p.fat_g * servings, 1) if p.fat_g else None,
        fiber_g=round(p.fiber_g * servings, 1) if p.fiber_g else None,
    )


def compute_nutrition(
    ingredients: list[str],
    servings: int | None,
    *,
    context_text: str | None = None,
) -> NutritionReport:
    """Try caption parse → per-ingredient USDA/local → optional Gemini."""
    if not ingredients:
        return NutritionReport(
            servings=servings,
            notes=["No ingredients to analyze."],
        )

    srv = max(servings or 1, 1)

    # 1) Creator-stated macros in caption (TikTok often includes these).
    from app.nutrition_parse import parse_stated_nutrition

    stated = parse_stated_nutrition(context_text, servings, ingredients=ingredients)
    if _has_calories(stated):
        assert stated is not None
        # Caption piece count wins over a stale "1 serving" default on the form.
        use_srv = stated.servings or srv
        if stated.per_serving.calories:
            _sync_totals_from_per_serving(stated, use_srv)
        return attach_yield(stated, ingredients)

    # 2) Per-ingredient: USDA (when keyed) + built-in reference averages per line.
    ing = compute_ingredient_nutrition(ingredients, srv)
    if _has_calories(ing):
        return attach_yield(ing, ingredients)

    # 3) Gemini AI estimate — disabled by default (non-deterministic; ignores video macros).
    if ENABLE_GEMINI_NUTRITION and GEMINI_API_KEY:
        from app.nutrition_gemini import estimate_with_gemini

        gem = estimate_with_gemini(ingredients, srv)
        if _has_calories(gem):
            gem.notes.append("AI estimate — values may change on recalculate. Re-import for video-stated macros.")
            return attach_yield(gem, ingredients)  # type: ignore[arg-type]

    # 4) Nothing quantifiable.
    notes = ["Could not estimate calories for this recipe."]
    if not USDA_API_KEY:
        notes.append(
            "Add USDA_API_KEY in backend/.env for USDA lookups (free at fdc.nal.usda.gov), "
            "or paste video-stated macros in the caption field."
        )
    if context_text and "calor" not in context_text.lower():
        notes.append("No per-serving calories found in the video description.")
    elif not context_text:
        notes.append(
            "No video caption stored — re-import the video or paste the description "
            "so stated macros can be parsed."
        )
    return NutritionReport(servings=srv, unmatched=ing.unmatched, notes=notes)
