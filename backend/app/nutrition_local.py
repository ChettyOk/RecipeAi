"""Offline macro estimates for common ingredients (no API key). Per-line fallback for hybrid nutrition."""

from __future__ import annotations

import re

from app.schemas import Nutrition

# Per 100 g: calories, protein_g, carbs_g, fat_g, fiber_g (USDA SR Legacy / Foundation averages).
_FOODS: list[tuple[str, tuple[float, float, float, float, float | None]]] = [
    ("chicken breast", (120, 22.5, 0, 2.6, 0)),
    ("chicken tenderloin", (120, 22.5, 0, 2.6, 0)),
    ("chicken thigh", (177, 19.7, 0, 10.9, 0)),
    ("ground beef", (250, 17.2, 0, 20, 0)),
    ("ground turkey", (170, 20, 0, 9, 0)),
    ("turkey breast", (135, 29, 0, 1, 0)),
    ("pork chop", (165, 20, 0, 9, 0)),
    ("salmon", (208, 20, 0, 13, 0)),
    ("tuna", (132, 28, 0, 1.3, 0)),
    ("shrimp", (99, 24, 0.2, 0.3, 0)),
    ("egg", (143, 12.6, 0.7, 9.5, 0)),
    ("rice", (130, 2.7, 28, 0.3, 0.4)),
    ("brown rice", (111, 2.6, 23, 0.9, 1.8)),
    ("pasta", (131, 5, 25, 1.1, 1.8)),
    ("noodle", (131, 5, 25, 1.1, 1.8)),
    ("linguine", (131, 5, 25, 1.1, 1.8)),
    ("quinoa", (120, 4.4, 21, 1.9, 2.8)),
    ("oats", (389, 17, 66, 7, 10.6)),
    ("flour", (364, 10, 76, 1, 2.7)),
    ("all purpose wheat flour", (364, 10, 76, 1, 2.7)),
    ("cornstarch", (381, 0.3, 91, 0.1, 0.9)),
    ("corn flakes", (357, 7, 84, 0.4, 3.3)),
    ("bread crumbs", (395, 13, 72, 5.3, 4.9)),
    ("panko", (395, 13, 72, 5.3, 4.9)),
    ("bread", (265, 9, 49, 3.2, 2.7)),
    ("tortilla", (304, 8, 50, 7.4, 3.5)),
    ("sugar", (387, 0, 100, 0, 0)),
    ("brown sugar", (380, 0, 98, 0, 0)),
    ("powdered sugar", (389, 0, 99.8, 0, 0)),
    ("honey", (304, 0.3, 82, 0, 0.2)),
    ("maple syrup", (260, 0, 67, 0.1, 0)),
    ("olive oil", (884, 0, 0, 100, 0)),
    ("vegetable oil", (884, 0, 0, 100, 0)),
    ("canola oil", (884, 0, 0, 100, 0)),
    ("coconut oil", (892, 0, 0, 99.1, 0)),
    ("sesame oil", (884, 0, 0, 100, 0)),
    ("cooking spray", (792, 0, 0, 88, 0)),
    ("butter", (717, 0.9, 0.1, 81, 0)),
    ("milk", (42, 3.4, 5, 1, 0)),
    ("almond milk", (15, 0.6, 0.3, 1.2, 0.4)),
    ("cream", (340, 2, 3, 36, 0)),
    ("cream cheese", (342, 6, 4, 34, 0)),
    ("cheese", (402, 25, 1.3, 33, 0)),
    ("parmesan cheese", (431, 38, 4, 29, 0)),
    ("mozzarella cheese", (280, 28, 3, 17, 0)),
    ("cheddar cheese", (403, 25, 1.3, 33, 0)),
    ("cottage cheese", (98, 11, 3.4, 4.3, 0)),
    ("yogurt plain", (61, 3.5, 4.7, 3.3, 0)),
    ("greek yogurt", (97, 9, 3.6, 5, 0)),
    ("onion", (40, 1.1, 9.3, 0.1, 1.7)),
    ("garlic", (149, 6.4, 33, 0.5, 2.1)),
    ("garlic powder", (331, 17, 73, 0.7, 9.9)),
    ("onion powder", (341, 10, 79, 1, 15)),
    ("green onion", (32, 1.8, 7.3, 0.2, 2.6)),
    ("carrot", (41, 0.9, 10, 0.2, 2.8)),
    ("broccoli", (34, 2.8, 7, 0.4, 2.6)),
    ("bell pepper", (31, 1, 6, 0.3, 2.1)),
    ("red pepper flakes", (318, 12, 56, 17, 27)),
    ("spinach", (23, 2.9, 3.6, 0.4, 2.2)),
    ("tomato", (18, 0.9, 3.9, 0.2, 1.2)),
    ("tomato paste", (82, 4.3, 19, 0.5, 4.1)),
    ("tomato sauce", (29, 1.3, 6.6, 0.2, 1.5)),
    ("potato", (77, 2, 17, 0.1, 2.2)),
    ("sweet potato", (86, 1.6, 20, 0.1, 3)),
    ("avocado", (160, 2, 9, 15, 7)),
    ("banana", (89, 1.1, 23, 0.3, 2.6)),
    ("apple", (52, 0.3, 14, 0.2, 2.4)),
    ("soy sauce", (53, 8, 4.9, 0.6, 0.8)),
    ("hot sauce", (12, 0.5, 2.5, 0.2, 0.5)),
    ("salt", (0, 0, 0, 0, 0)),
    ("black pepper", (251, 10, 64, 3.3, 25)),
    ("paprika", (282, 14, 54, 13, 35)),
    ("cumin", (375, 18, 44, 22, 11)),
    ("cinnamon", (247, 4, 81, 1.2, 53)),
    ("chicken broth", (15, 1.2, 0.5, 0.5, 0)),
    ("beef broth", (17, 2.2, 0.5, 0.5, 0)),
    ("tofu", (76, 8, 1.9, 4.8, 0.3)),
    ("black beans", (132, 8.9, 24, 0.5, 8.7)),
    ("kidney beans", (127, 8.7, 23, 0.5, 6.4)),
    ("chickpeas", (164, 8.9, 27, 2.6, 7.6)),
    ("lentils", (116, 9, 20, 0.4, 7.9)),
    ("peanut butter", (588, 25, 20, 50, 6)),
    ("almond butter", (614, 21, 19, 56, 10)),
    ("whey protein powder", (400, 80, 10, 5, 0)),
    ("corn", (86, 3.3, 19, 1.2, 2.7)),
    ("mushroom", (22, 3.1, 3.3, 0.3, 1)),
    ("zucchini", (17, 1.2, 3.1, 0.3, 1)),
    ("coconut milk", (230, 2.3, 6, 24, 0)),
    ("bacon", (541, 37, 1.4, 42, 0)),
    ("sausage", (301, 12, 2, 27, 0)),
    ("mayonnaise", (680, 1, 0.6, 75, 0)),
    ("mustard", (66, 4, 5, 4, 3)),
    ("ketchup", (112, 1.7, 27, 0.1, 0.3)),
    ("vinegar", (18, 0, 0.9, 0, 0)),
    ("rice vinegar", (18, 0, 0.9, 0, 0)),
    ("apple cider vinegar", (22, 0, 0.9, 0, 0)),
    ("balsamic vinegar", (88, 0.5, 17, 0, 0)),
    ("stevia", (0, 0, 0, 0, 0)),
    ("monk fruit", (0, 0, 0, 0, 0)),
    ("sweetener", (0, 0, 0, 0, 0)),
]

_COUNT: dict[str, tuple[float, float, float, float]] = {
    "egg": (70, 6, 0.5, 5),
    "eggs": (70, 6, 0.5, 5),
}


def _match(name: str) -> tuple[str, tuple[float, float, float, float, float | None]] | None:
    low = name.lower()
    best: tuple[str, tuple[float, float, float, float, float | None]] | None = None
    best_len = 0
    for kw, vals in _FOODS:
        if kw in low and len(kw) > best_len:
            best = (kw, vals)
            best_len = len(kw)
    return best


def _count_qty(line: str, qty: float | None) -> float | None:
    if qty is not None:
        return qty
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s+", line)
    return float(m.group(1)) if m else None


def estimate_line(
    search_name: str,
    grams: float,
    *,
    raw_line: str = "",
    qty: float | None = None,
) -> Nutrition | None:
    """Return nutrition contribution for one ingredient line, or None if unknown."""
    hit = _match(search_name)
    if hit and grams > 0:
        _, (cal, p, c, f, fib) = hit
        factor = grams / 100.0
        return Nutrition(
            calories=round(cal * factor, 2),
            protein_g=round(p * factor, 2),
            carbs_g=round(c * factor, 2),
            fat_g=round(f * factor, 2),
            fiber_g=round(fib * factor, 2) if fib is not None else None,
        )

    low = search_name.lower()
    for token, (cal, p, c, f) in _COUNT.items():
        if re.search(rf"\b{re.escape(token)}\b", low):
            n = _count_qty(raw_line, qty)
            if n is not None:
                return Nutrition(
                    calories=round(cal * n, 2),
                    protein_g=round(p * n, 2),
                    carbs_g=round(c * n, 2),
                    fat_g=round(f * n, 2),
                    fiber_g=0,
                )
    return None
