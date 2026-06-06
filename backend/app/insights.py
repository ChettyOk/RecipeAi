"""Personalized nutrition insights, allergy scanning, and ingredient substitution suggestions.

Daily targets follow published guidance:
- BMI: WHO classification (kg/m²)
- BMR: Mifflin–St Jeor (1990)
- TDEE: BMR × physical-activity level (DRI / NIH PAL factors)
- Weight change: NIH ~500–1000 kcal/day deficit or modest surplus, scaled by BMI
- Minimum intake: NIH floors (1,200 kcal women, 1,500 kcal men)
- Macros: USDA Acceptable Macronutrient Distribution Ranges (AMDR)

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

# Physical activity level multipliers (DRI / NIH consensus).
_ACTIVITY_FACTOR = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

# NIH minimum daily calories when reducing intake.
_MIN_CALORIES = {"female": 1200, "male": 1500, "other": 1350}

# USDA AMDR midpoints used for fat % of calories by goal.
_FAT_PCT = {"lose": 0.25, "maintain": 0.30, "gain": 0.25}

# Minimum carbohydrate intake (IOM RDA ~130 g/day for brain glucose).
_MIN_CARBS_G = 130


def compute_bmi(weight_kg: float, height_cm: float) -> float:
    height_m = height_cm / 100
    if height_m <= 0:
        return 0.0
    return weight_kg / (height_m * height_m)


def bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "underweight"
    if bmi < 25:
        return "normal"
    if bmi < 30:
        return "overweight"
    return "obese"


_BMI_LABEL = {
    "underweight": "underweight (BMI < 18.5)",
    "normal": "healthy weight (BMI 18.5–24.9)",
    "overweight": "overweight (BMI 25–29.9)",
    "obese": "obese (BMI ≥ 30)",
}


def _mifflin_st_jeor_bmr(weight_kg: float, height_cm: float, age: int, sex: str) -> float:
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    if sex == "male":
        return base + 5
    if sex == "female":
        return base - 161
    return base - 78  # average of male (+5) and female (−161) constants


def _calorie_delta(goal: str, bmi_cat: str, bmi: float) -> tuple[int, str]:
    if goal == "maintain":
        return 0, "maintenance calories (no deficit or surplus)"

    if goal == "lose":
        if bmi_cat == "underweight":
            return 0, "maintenance only — BMI is underweight (WHO); weight loss is not recommended"
        if bmi_cat in ("normal", "overweight"):
            return -500, "a ~500 kcal/day deficit (~1 lb/week, NIH)"
        if bmi >= 35:
            return -1000, "a ~1000 kcal/day deficit (BMI ≥ 35, upper NIH range, capped at safe minimum)"
        return -750, "a ~750 kcal/day deficit (BMI ≥ 30, NIH range 500–1000 kcal/day)"

    if bmi_cat == "underweight":
        return 500, "a ~500 kcal/day surplus for gradual healthy gain (underweight BMI)"
    if bmi_cat == "normal":
        return 350, "a ~350 kcal/day surplus for lean gain"
    return 250, "a modest ~250 kcal/day surplus (BMI already elevated)"


def _protein_g_per_kg(goal: str, bmi_cat: str) -> float:
    """Protein g/kg — above IOM RDA (0.8), higher when cutting or BMI is elevated."""
    if goal == "lose":
        return 2.0 if bmi_cat in ("overweight", "obese") else 1.6
    if goal == "gain":
        return 1.8
    return 1.0  # maintain — modestly above RDA


def _minimum_calories(sex: str) -> int:
    return _MIN_CALORIES.get(sex, _MIN_CALORIES["other"])


def _macro_split(target_cal: float, weight_kg: float, goal: str, bmi_cat: str) -> tuple[float, float, float]:
    """Return protein_g, fat_g, carbs_g using USDA AMDR-aligned splits."""
    protein_g = min(
        _protein_g_per_kg(goal, bmi_cat) * weight_kg,
        (target_cal * 0.35) / 4,  # AMDR protein ceiling (35% of kcal)
    )
    min_fat_g = (target_cal * 0.20) / 9
    fat_g = max((target_cal * _FAT_PCT.get(goal, 0.30)) / 9, min_fat_g)
    carbs_g = max((target_cal - protein_g * 4 - fat_g * 9) / 4, 0)

    # IOM RDA: 130 g carbohydrate/day when the calorie budget allows.
    if carbs_g < _MIN_CARBS_G:
        carbs_try = _MIN_CARBS_G
        fat_try = max((target_cal - protein_g * 4 - carbs_try * 4) / 9, min_fat_g)
        if protein_g * 4 + carbs_try * 4 + fat_try * 9 <= target_cal * 1.02:
            carbs_g, fat_g = carbs_try, fat_try
        else:
            carbs_g = max((target_cal - protein_g * 4 - min_fat_g * 9) / 4, 0)
            fat_g = min_fat_g

    return protein_g, fat_g, carbs_g


def compute_targets(p: ProfileBase) -> DailyTargets | None:
    if p.weight_kg is None or p.height_cm is None or p.age is None:
        return None

    sex = (p.sex or "other").lower()
    bmi = compute_bmi(p.weight_kg, p.height_cm)
    cat = bmi_category(bmi)

    bmr = _mifflin_st_jeor_bmr(p.weight_kg, p.height_cm, p.age, sex)
    factor = _ACTIVITY_FACTOR.get(p.activity_level or "", 1.2)
    tdee = bmr * factor
    goal = p.goal or "maintain"
    delta, delta_note = _calorie_delta(goal, cat, bmi)
    target_cal = tdee + delta

    floor = _minimum_calories(sex)
    if target_cal < floor:
        target_cal = float(floor)

    protein_g, fat_g, carbs_g = _macro_split(target_cal, p.weight_kg, goal, cat)

    return DailyTargets(
        bmr=round(bmr),
        tdee=round(tdee),
        target_calories=round(target_cal),
        protein_g=round(protein_g),
        carbs_g=round(carbs_g),
        fat_g=round(fat_g),
        bmi=round(bmi, 1),
        bmi_category=cat,
        basis=(
            f"WHO BMI {round(bmi, 1)} ({_BMI_LABEL[cat]}). "
            f"Mifflin–St Jeor BMR × {factor} activity (TDEE {round(tdee)} kcal), "
            f"adjusted for {delta_note}. "
            f"Macros within USDA AMDR; minimum intake {floor} kcal (NIH)."
        ),
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
