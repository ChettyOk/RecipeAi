"""Resolve ingredient lines to gram amounts and normalized food names for nutrition lookup."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.nutrition import parse_ingredient, to_grams

# Typical gram weight when sold by count (USDA-style averages).
_COUNT_G: dict[str, float] = {
    "egg": 50,
    "eggs": 50,
    "large egg": 50,
    "clove": 3,
    "cloves": 3,
    "tender": 56,
    "tenders": 56,
    "tenderloin": 56,
    "tenderloins": 56,
    "strip": 28,
    "strips": 28,
    "nugget": 20,
    "nuggets": 20,
    "wing": 90,
    "wings": 90,
    "slice": 30,
    "slices": 30,
    "patty": 85,
    "patties": 85,
    "muffin": 60,
    "muffins": 60,
    "cookie": 30,
    "cookies": 30,
    "roll": 50,
    "rolls": 50,
    "stalk": 40,
    "stalks": 40,
    "fillet": 150,
    "fillets": 150,
    "breast": 174,
    "breasts": 174,
    "thigh": 130,
    "thighs": 130,
    "piece": 45,
    "pieces": 45,
}

# Search aliases → cleaner USDA / local lookup terms (longest match wins in normalize).
_ALIASES: list[tuple[str, str]] = [
    ("chicken tenderloin", "chicken breast raw"),
    ("chicken tenderloins", "chicken breast raw"),
    ("chicken breast", "chicken breast raw"),
    ("ground beef", "ground beef 85 lean"),
    ("ground turkey", "ground turkey raw"),
    ("all purpose flour", "all purpose wheat flour"),
    ("all-purpose flour", "all purpose wheat flour"),
    ("corn starch", "cornstarch"),
    ("cornstarch", "cornstarch"),
    ("corn flakes", "corn flakes cereal"),
    ("cornflakes", "corn flakes cereal"),
    ("crushed cornflakes", "corn flakes cereal"),
    ("cooking spray", "cooking spray"),
    ("olive oil", "olive oil"),
    ("vegetable oil", "vegetable oil"),
    ("canola oil", "canola oil"),
    ("chicken bouillon", "chicken broth"),
    ("bouillon", "chicken broth"),
    ("garlic powder", "garlic powder"),
    ("onion powder", "onion powder"),
    ("paprika", "paprika"),
    ("black pepper", "black pepper"),
    ("seasoned salt", "salt"),
    ("kosher salt", "salt"),
    ("sea salt", "salt"),
    ("red pepper flake", "red pepper flakes"),
    ("red pepper flakes", "red pepper flakes"),
    ("soy sauce", "soy sauce"),
    ("greek yogurt", "greek yogurt plain"),
    ("plain yogurt", "yogurt plain"),
    ("cream cheese", "cream cheese"),
    ("parmesan", "parmesan cheese"),
    ("mozzarella", "mozzarella cheese"),
    ("cheddar", "cheddar cheese"),
    ("brown sugar", "brown sugar"),
    ("powdered sugar", "powdered sugar"),
    ("confectioners sugar", "powdered sugar"),
    ("maple syrup", "maple syrup"),
    ("breadcrumbs", "bread crumbs dry"),
    ("panko", "panko bread crumbs"),
    ("protein powder", "whey protein powder"),
    ("almond milk", "almond milk unsweetened"),
    ("oat milk", "oat milk"),
    ("coconut oil", "coconut oil"),
    ("rice vinegar", "rice vinegar"),
    ("apple cider vinegar", "apple cider vinegar"),
    ("balsamic vinegar", "balsamic vinegar"),
    ("tomato paste", "tomato paste"),
    ("tomato sauce", "tomato sauce"),
    ("canned tomato", "canned tomatoes"),
    ("black beans", "black beans cooked"),
    ("kidney beans", "kidney beans cooked"),
    ("chickpea", "chickpeas cooked"),
    ("chickpeas", "chickpeas cooked"),
    ("quinoa", "quinoa cooked"),
    ("cottage cheese", "cottage cheese low fat"),
    ("turkey breast", "turkey breast raw"),
    ("pork chop", "pork chop raw"),
    ("bacon", "bacon cooked"),
    ("sausage", "pork sausage"),
    ("tortilla", "flour tortilla"),
    ("tortillas", "flour tortilla"),
    ("wrap", "flour tortilla"),
]

_HEADER_ONLY = re.compile(
    r"(?i)^(?:seasonings?(?:\s+for\s+\w+)?|for\s+the\s+\w+|marinade|dressing|optional)\s*:?\s*$"
)
_PREP_WORDS = re.compile(
    r"(?i)\b(beaten|crushed|chopped|diced|minced|sliced|shredded|grated|"
    r"melted|softened|room\s+temperature|optional|to\s+taste|divided|"
    r"freshly|ground|packed|heaping|thinly|roughly)\b"
)


@dataclass
class ResolvedIngredient:
    line: str
    name: str
    search_name: str
    grams: float
    qty: float | None
    unit: str | None
    approx: bool = False


def normalize_food_name(name: str) -> str:
    s = _PREP_WORDS.sub("", name.lower())
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^\w\s-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip(" ,.-")
    for needle, alias in sorted(_ALIASES, key=lambda x: -len(x[0])):
        if needle in s:
            return alias
    return s or name.lower().strip()


def search_queries(name: str) -> list[str]:
    base = normalize_food_name(name)
    queries = [base]
    # Drop leading size words.
    trimmed = re.sub(r"^(?:large|medium|small|fresh|raw|cooked|boneless|skinless)\s+", "", base)
    if trimmed and trimmed not in queries:
        queries.append(trimmed)
    # First two words often enough for USDA.
    parts = base.split()
    if len(parts) > 2:
        queries.append(" ".join(parts[:2]))
    if len(parts) > 1:
        queries.append(parts[0])
    out: list[str] = []
    for q in queries:
        q = q.strip()
        if q and q not in out:
            out.append(q)
    return out


def _grams_from_count(qty: float, name: str) -> float | None:
    low = name.lower()
    for token, grams in sorted(_COUNT_G.items(), key=lambda x: -len(x[0])):
        if re.search(rf"\b{re.escape(token)}\b", low):
            return qty * grams
    return None


def resolve_ingredient_line(line: str) -> ResolvedIngredient | None:
    """Parse a line into grams + normalized name, or None if not quantifiable."""
    raw = line.strip()
    if not raw or _HEADER_ONLY.match(raw):
        return None

    qty, unit, name = parse_ingredient(raw)
    if not name.strip():
        return None

    grams: float | None = None
    approx = False

    if qty is not None and unit is not None:
        grams = to_grams(qty, unit)
        if unit in ("tsp", "teaspoon", "teaspoons", "tbsp", "tablespoon", "tablespoons", "cup", "cups"):
            approx = True
    elif qty is not None:
        grams = _grams_from_count(qty, name)
        if grams is None and re.search(r"(?i)\b(?:egg|eggs)\b", name):
            grams = qty * _COUNT_G["egg"]

    if grams is None or grams <= 0:
        return None

    search = normalize_food_name(name)
    return ResolvedIngredient(
        line=raw,
        name=name.strip(),
        search_name=search,
        grams=grams,
        qty=qty,
        unit=unit,
        approx=approx,
    )
