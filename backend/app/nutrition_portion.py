"""Scale nutrition to a user-defined portion (grams, ml, oz, servings, etc.)."""

from __future__ import annotations

from app.schemas import Nutrition, NutritionReport

# Convert user portion amount to grams (weight) or ml (volume, treated ≈1g/ml for scaling).
_TO_GRAMS: dict[str, float] = {
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "kg": 1000.0,
    "oz": 28.3495,
    "ounce": 28.3495,
    "ounces": 28.3495,
    "lb": 453.592,
    "lbs": 453.592,
}
_TO_ML: dict[str, float] = {
    "ml": 1.0,
    "milliliter": 1.0,
    "l": 1000.0,
    "liter": 1000.0,
    "tsp": 4.92892,
    "tbsp": 14.7868,
    "cup": 240.0,
    "cups": 240.0,
    "floz": 29.5735,
    "fl": 29.5735,
    "pint": 473.176,
}


def portion_to_reference_g(amount: float, unit: str) -> float | None:
    """Return a weight-like amount in grams for scaling (volume uses ml≈g)."""
    u = unit.strip().lower().rstrip(".")
    if u in ("serving", "servings", "srv"):
        return None  # handled separately
    if u in _TO_GRAMS:
        return amount * _TO_GRAMS[u]
    if u in _TO_ML:
        return amount * _TO_ML[u]
    return None


def scale_factor(amount: float, unit: str, report: NutritionReport) -> tuple[float, str | None]:
    """
    How many 'reference servings' the user's portion represents.
    Returns (factor, warning_or_none).
    """
    u = unit.strip().lower().rstrip(".")
    if u in ("serving", "servings", "srv"):
        if amount <= 0:
            return 1.0, None
        return amount, None

    ref_g = portion_to_reference_g(amount, u)
    if ref_g is None or ref_g <= 0:
        return 1.0, f"Unknown unit “{unit}”."

    per_g = report.per_serving_weight_g
    if not per_g or per_g <= 0:
        return (
            1.0,
            "Cannot scale by weight — add ingredients with g/cup/tbsp amounts so we can estimate serving size.",
        )

    return ref_g / per_g, None


def scale_nutrition(n: Nutrition, factor: float) -> Nutrition:
    def m(v: float | None) -> float | None:
        return round(v * factor, 1) if v is not None else None

    return Nutrition(
        calories=m(n.calories),
        protein_g=m(n.protein_g),
        carbs_g=m(n.carbs_g),
        fat_g=m(n.fat_g),
        fiber_g=m(n.fiber_g),
    )


def portion_nutrition(report: NutritionReport, amount: float, unit: str) -> tuple[Nutrition, float, str | None]:
    factor, warn = scale_factor(amount, unit, report)
    return scale_nutrition(report.per_serving, factor), factor, warn
