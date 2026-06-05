"""Personalized nutrition insights, allergy scanning, and ingredient substitution suggestions.

Targets use the Mifflin-St Jeor BMR + activity multiplier (TDEE), then adjust for the user's goal.
Substitutions are rule-based (no API needed) and filtered by the user's goal + allergies.
These are general wellness estimates, not medical advice.
"""

from __future__ import annotations

import re

from app.schemas import (
    DailyTargets,
    Nutrition,
    NutritionReport,
    ProfileBase,
    RecipeInsights,
    Substitution,
)

_ACTIVITY_FACTOR = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}
# Protein g per kg bodyweight by goal.
_PROTEIN_PER_KG = {"lose": 2.0, "maintain": 1.6, "gain": 1.8}
_CALORIE_DELTA = {"lose": -500, "maintain": 0, "gain": 350}


def compute_targets(p: ProfileBase) -> DailyTargets | None:
    if p.weight_kg is None or p.height_cm is None or p.age is None:
        return None
    s = (p.sex or "other").lower()
    base = 10 * p.weight_kg + 6.25 * p.height_cm - 5 * p.age
    if s == "male":
        bmr = base + 5
    elif s == "female":
        bmr = base - 161
    else:
        bmr = base - 78  # average of +5 and -161
    factor = _ACTIVITY_FACTOR.get(p.activity_level or "", 1.2)
    tdee = bmr * factor
    goal = p.goal or "maintain"
    target_cal = tdee + _CALORIE_DELTA.get(goal, 0)

    protein_g = _PROTEIN_PER_KG.get(goal, 1.6) * p.weight_kg
    fat_g = (target_cal * 0.27) / 9  # ~27% of calories from fat
    carbs_g = max((target_cal - protein_g * 4 - fat_g * 9) / 4, 0)

    goal_word = {"lose": "a ~500 kcal deficit", "gain": "a ~350 kcal surplus", "maintain": "maintenance"}.get(
        goal, "maintenance"
    )
    return DailyTargets(
        bmr=round(bmr),
        tdee=round(tdee),
        target_calories=round(target_cal),
        protein_g=round(protein_g),
        carbs_g=round(carbs_g),
        fat_g=round(fat_g),
        basis=f"Mifflin-St Jeor BMR × {factor} activity, adjusted for {goal_word}.",
    )


# ── Allergen scanning ──

_ALLERGEN_KEYWORDS: dict[str, list[str]] = {
    "dairy": ["milk", "cream", "butter", "cheese", "yogurt", "yoghurt", "ghee", "parmesan", "mozzarella", "whey"],
    "gluten": ["flour", "wheat", "bread", "pasta", "noodle", "soy sauce", "breadcrumb", "couscous", "barley", "panko"],
    "nuts": ["almond", "cashew", "walnut", "pecan", "hazelnut", "pistachio", "macadamia", "nut butter"],
    "peanuts": ["peanut"],
    "egg": ["egg", "eggs", "mayonnaise", "mayo", "aioli"],
    "soy": ["soy", "tofu", "edamame", "tempeh", "miso"],
    "shellfish": ["shrimp", "prawn", "crab", "lobster", "scallop", "clam", "mussel", "oyster"],
    "fish": ["salmon", "tuna", "cod", "anchovy", "tilapia", "fish sauce", "sardine"],
    "sesame": ["sesame", "tahini"],
}


def scan_allergens(ingredients: list[str], allergies: list[str]) -> list[str]:
    if not allergies:
        return []
    warnings: list[str] = []
    text = " | ".join(i.lower() for i in ingredients)
    for allergen in allergies:
        keywords = _ALLERGEN_KEYWORDS.get(allergen, [allergen])
        hits = sorted({kw for kw in keywords if re.search(rf"\b{re.escape(kw)}", text)})
        if hits:
            warnings.append(
                f"Contains possible {allergen} ({', '.join(hits[:4])}). You listed {allergen} as an allergy."
            )
    return warnings


# ── Substitution rules ──
# Each rule: trigger keywords -> suggestion. `goals` limits when it's surfaced (empty = any goal).
# `allergen` (optional) means the swap is primarily to avoid that allergen.
_SUB_RULES: list[dict] = [
    {"match": ["heavy cream", "double cream", "cream"], "suggestion": "plain Greek yogurt or evaporated skim milk",
     "reason": "cuts saturated fat and calories while keeping it creamy", "goals": ["lose", "maintain"], "allergen": None},
    {"match": ["sour cream"], "suggestion": "plain Greek yogurt",
     "reason": "more protein, far less fat", "goals": ["lose", "maintain", "gain"], "allergen": None},
    {"match": ["mayonnaise", "mayo"], "suggestion": "Greek yogurt or mashed avocado",
     "reason": "lower calories, added nutrients", "goals": ["lose", "maintain"], "allergen": None},
    {"match": ["butter"], "suggestion": "olive oil (cooking) or mashed banana/avocado (baking)",
     "reason": "swaps saturated for unsaturated fat", "goals": ["lose", "maintain"], "allergen": None},
    {"match": ["sugar", "honey", "syrup"], "suggestion": "monk fruit or stevia (to taste)",
     "reason": "cuts added sugar and calories", "goals": ["lose", "maintain"], "allergen": None},
    {"match": ["white rice"], "suggestion": "brown rice or cauliflower rice",
     "reason": "more fiber / fewer carbs per serving", "goals": ["lose", "maintain"], "allergen": None},
    {"match": ["noodle", "pasta", "linguine", "spaghetti"], "suggestion": "edamame/chickpea pasta or zucchini noodles",
     "reason": "more protein and fiber, fewer refined carbs", "goals": ["lose", "gain"], "allergen": None},
    {"match": ["ground beef", "beef mince"], "suggestion": "lean ground turkey or 93% lean beef",
     "reason": "more protein per calorie, less fat", "goals": ["lose", "maintain", "gain"], "allergen": None},
    {"match": ["vegetable oil", "canola oil", "frying"], "suggestion": "an oil spray or air-frying",
     "reason": "big calorie savings from less added oil", "goals": ["lose"], "allergen": None},
    {"match": ["bacon"], "suggestion": "turkey bacon or smoked paprika for flavor",
     "reason": "lower fat and sodium", "goals": ["lose", "maintain"], "allergen": None},
    {"match": ["regular soy sauce", "soy sauce"], "suggestion": "low-sodium soy sauce or coconut aminos",
     "reason": "less sodium (coconut aminos is also soy/gluten-free)", "goals": [], "allergen": None},
    # Allergen-driven swaps (surfaced whenever the user has that allergy regardless of goal):
    {"match": ["milk", "cream", "butter", "cheese", "yogurt"], "suggestion": "a dairy-free alternative (oat/soy/coconut)",
     "reason": "avoids dairy", "goals": [], "allergen": "dairy"},
    {"match": ["flour", "pasta", "noodle", "bread", "soy sauce"], "suggestion": "a certified gluten-free version",
     "reason": "avoids gluten", "goals": [], "allergen": "gluten"},
    {"match": ["egg", "mayonnaise", "mayo"], "suggestion": "a flax egg or vegan mayo",
     "reason": "avoids egg", "goals": [], "allergen": "egg"},
]


def suggest_substitutions(ingredients: list[str], profile: ProfileBase | None) -> list[Substitution]:
    goal = (profile.goal if profile else None) or None
    allergies = set(profile.allergies) if profile else set()
    text_lines = [i.lower() for i in ingredients]
    out: list[Substitution] = []
    seen: set[tuple[str, str]] = set()

    for line in text_lines:
        for rule in _SUB_RULES:
            allergen = rule["allergen"]
            # Allergen rules only apply if the user has that allergy.
            if allergen is not None and allergen not in allergies:
                continue
            # Goal rules: if goal-specific and the user's goal doesn't match, skip (unless allergen-driven).
            if allergen is None and rule["goals"] and goal and goal not in rule["goals"]:
                continue
            matched = next((kw for kw in rule["match"] if kw in line), None)
            if not matched:
                continue
            key = (matched, rule["suggestion"])
            if key in seen:
                continue
            seen.add(key)
            out.append(
                Substitution(
                    ingredient=matched,
                    suggestion=rule["suggestion"],
                    reason=rule["reason"],
                )
            )
            break  # one suggestion per ingredient line
    return out[:12]


def build_insights(
    ingredients: list[str],
    nutrition: NutritionReport | None,
    servings: int | None,
    profile: ProfileBase | None,
) -> RecipeInsights:
    per_serving = nutrition.per_serving if nutrition else Nutrition()
    insights = RecipeInsights(has_profile=profile is not None, per_serving=per_serving)

    targets = compute_targets(profile) if profile else None

    cal = per_serving.calories
    protein = per_serving.protein_g
    if targets and targets.target_calories and cal is not None:
        insights.calories_pct_of_target = round(cal / targets.target_calories * 100)
    if targets and targets.protein_g and protein is not None:
        insights.protein_pct_of_target = round(protein / targets.protein_g * 100)

    # Goal-aware fit notes.
    if protein is not None:
        if protein >= 30:
            insights.fit_notes.append(f"High protein: {round(protein)} g per serving.")
        elif protein < 15 and (not profile or profile.goal != "lose"):
            insights.fit_notes.append(f"Lower protein ({round(protein)} g/serving) — consider adding a protein source.")
    if targets and insights.calories_pct_of_target is not None:
        pct = insights.calories_pct_of_target
        if profile and profile.goal == "lose" and pct > 45:
            insights.fit_notes.append(f"This serving is ~{pct}% of your daily target — sizable for a cut.")
        elif profile and profile.goal == "gain" and pct < 25:
            insights.fit_notes.append(f"Only ~{pct}% of your daily target — pair with sides to hit a surplus.")
        else:
            insights.fit_notes.append(f"About {pct}% of your daily calorie target per serving.")

    if profile:
        insights.allergy_warnings = scan_allergens(ingredients, profile.allergies)
        # Dietary-preference conflicts (e.g. wants vegan but recipe has meat/dairy).
        text = " | ".join(i.lower() for i in ingredients)
        prefs = set(profile.dietary_prefs)
        if "vegan" in prefs or "vegetarian" in prefs:
            meat = [m for m in ("chicken", "beef", "pork", "bacon", "shrimp", "fish", "turkey", "lamb") if m in text]
            if meat:
                insights.dietary_conflicts.append(f"Contains meat/seafood ({', '.join(meat[:3])}) but you prefer {'/'.join(prefs & {'vegan', 'vegetarian'})}.")
        if "vegan" in prefs:
            dairy = [d for d in ("milk", "cheese", "butter", "cream", "yogurt", "egg") if d in text]
            if dairy:
                insights.dietary_conflicts.append(f"Contains animal products ({', '.join(dairy[:3])}) but you prefer vegan.")

    insights.substitutions = suggest_substitutions(ingredients, profile)
    return insights
