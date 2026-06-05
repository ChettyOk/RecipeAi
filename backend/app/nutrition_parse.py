"""Parse creator-stated macros from video descriptions/captions (TikTok/Instagram).

Handles:
  - "Per Serving (of 3): 406 cal, 52g carbs..."
  - "Per tender: 120 calories, 15g protein"
  - "120 kcal per piece" / "120 cal each tender"
  - "Macros for one (makes 8)" + "396 calories" + "38g C | 14g F | 32g P"
  - "Macros: 670cal, 52g P, 40g C, 34g F" + "Total Servings: 4"
  - Serving count from "of 8", "makes 8 tenders", or ingredient lines ("4 chicken tenders")
"""

from __future__ import annotations

import re

from app.schemas import Nutrition, NutritionReport

# Words creators use instead of "serving" (1 unit = 1 piece/tender/etc.).
_PIECE_UNITS = (
    "serving",
    "piece",
    "pieces",
    "tender",
    "tenders",
    "strip",
    "strips",
    "nugget",
    "nuggets",
    "patty",
    "patties",
    "wing",
    "wings",
    "cutlet",
    "cutlets",
    "cookie",
    "cookies",
    "muffin",
    "muffins",
    "roll",
    "rolls",
    "slice",
    "slices",
)
_PIECE_ALT = "|".join(re.escape(u) for u in _PIECE_UNITS)

# "Per tender (of 8):", "Each piece -", "Approx per serving:"
_HEADER_RE = re.compile(
    rf"(?is)(?:approx\.?\s*)?"
    rf"(?:per|each)\s+"
    rf"(?P<unit>{_PIECE_ALT})"
    rf"(?:\s*\(\s*of\s+(?P<count>\d{{1,3}})\s*\))?"
    rf"\s*[:\-]?"
)

# "120 kcal per tender", "120 calories each piece"
_INLINE_CAL_RE = re.compile(
    rf"(?i)(\d+(?:\.\d+)?)\s*(?:kcal|calories?|cals?)\s*(?:per|each|/)\s*(?P<unit>{_PIECE_ALT})\b"
)
# "per tender: 120 cal"
_REVERSE_HEADER_RE = re.compile(
    rf"(?i)(?:per|each)\s+(?P<unit>{_PIECE_ALT})\s*[:\-]\s*"
)

_CAL_RE = re.compile(r"(?i)(\d+(?:\.\d+)?)\s*(?:kcal|calories?|cals?)\b")
# Compact inline: "670cal, 52g P, 40g C, 34g F"
_INLINE_MACRO_PACK_RE = re.compile(
    r"(?i)(\d+(?:\.\d+)?)\s*(?:kcal|calories?|cals?)\s*,?\s*"
    r"(\d+(?:\.\d+)?)\s*g?\s*P\b\s*,?\s*"
    r"(\d+(?:\.\d+)?)\s*g?\s*C\b\s*,?\s*"
    r"(\d+(?:\.\d+)?)\s*g?\s*F\b"
)
# "Macros:" / "Nutrition:" header (TikTok inline captions)
_MACROS_COLON_RE = re.compile(r"(?is)\b(?:macros?|nutrition)\s*:")
_TOTAL_SERVINGS_RE = re.compile(
    r"(?i)(?:total\s+)?(?:servings?|serves?|yields?|makes?)\s*[:\-]\s*(\d{1,3})\b"
)
# "38g C | 14g F | 32g P" or "38C · 14F · 32P"
_ABBREV_C = re.compile(r"(?i)(?<!\w)(\d+(?:\.\d+)?)\s*g?\s*C\b(?!\w)")
_ABBREV_F = re.compile(r"(?i)(?<!\w)(\d+(?:\.\d+)?)\s*g?\s*F\b(?!\w)")
_ABBREV_P = re.compile(r"(?i)(?<!\w)(\d+(?:\.\d+)?)\s*g?\s*P\b(?!\w)")
_MACRO_RES: list[tuple[str, re.Pattern[str]]] = [
    ("protein_g", re.compile(r"(?i)(\d+(?:\.\d+)?)\s*g?\s*(?:protein|prot)\b")),
    ("carbs_g", re.compile(r"(?i)(\d+(?:\.\d+)?)\s*g?\s*(?:carbs?|carbohydrates?|carb)\b")),
    ("fat_g", re.compile(r"(?i)(\d+(?:\.\d+)?)\s*g?\s*(?:fat|fats)\b")),
    ("fiber_g", re.compile(r"(?i)(\d+(?:\.\d+)?)\s*g?\s*(?:fiber|fibre)\b")),
]

# "Macros for one (makes 8)", "Macro breakdown (serves 6)"
_MACROS_FOR_ONE_RE = re.compile(
    r"(?is)\bmacros?\s+(?:for\s+)?(?:one|1(?:\s+serving)?|each|per\s+serving)"
    r"(?:\s*\(\s*(?:makes?|yields?|serves?)\s+(?P<count>\d{1,3})\s*\))?"
    r"\s*[:\-]?"
)
_MACROS_BLOCK_RE = re.compile(
    r"(?is)\b(?:macro\s+breakdown|nutrition\s+(?:info|facts)|full\s+recipe\s+breakdown)"
    r"(?:\s*\(\s*(?:makes?|yields?|serves?)\s+(?P<count>\d{1,3})\s*\))?"
    r"\s*[:\-]?"
)

_MAKES_RE = re.compile(rf"(?i)\b(?:makes?|yields?|serves?)\s+(\d{{1,3}})\s*(?:{_PIECE_ALT})?\b")
_MAKES_PAREN_RE = re.compile(r"(?i)\(\s*(?:makes?|yields?|serves?)\s+(\d{1,3})\s*\)")
_COUNT_ING_RE = re.compile(rf"(?i)\b(\d{{1,3}})\s+(?:\w+\s+){{0,3}}?(?:{_PIECE_ALT})\b")
_SERVINGS_OF_RE = re.compile(r"(?i)per\s+\w+\s*\(\s*of\s+(\d{1,3})\s*\)")


def _f(x: str | None) -> float | None:
    if x is None:
        return None
    try:
        return float(x)
    except (ValueError, TypeError):
        return None


def _normalize_unit(unit: str | None) -> str:
    if not unit:
        return "serving"
    u = unit.lower().strip()
    if u in ("servings", "serving"):
        return "serving"
    if u.endswith("s") and u[:-1] in _PIECE_UNITS:
        return u[:-1] if u != "pieces" else "piece"
    return u


def infer_piece_count(text: str | None, ingredients: list[str] | None) -> int | None:
    """Guess how many pieces/servings the recipe makes."""
    blob = " ".join(filter(None, [text or "", " ".join(ingredients or [])]))
    for rx in (_TOTAL_SERVINGS_RE, _SERVINGS_OF_RE, _MAKES_PAREN_RE, _MAKES_RE):
        m = rx.search(blob)
        if m:
            return int(m.group(1))
    counts: list[int] = []
    for rx in (_COUNT_ING_RE,):
        for m in rx.finditer(blob):
            n = int(m.group(1))
            if 1 <= n <= 100:
                counts.append(n)
    if counts:
        return max(counts)
    return None


def _extract_macros_from_segment(segment: str) -> Nutrition | None:
    cal_m = _CAL_RE.search(segment)
    if not cal_m:
        return None
    per = Nutrition(calories=_f(cal_m.group(1)))
    for key, rx in _MACRO_RES:
        mm = rx.search(segment)
        if mm:
            setattr(per, key, _f(mm.group(1)))
    # Abbreviated C / F / P (only fill gaps — full words win).
    if per.carbs_g is None:
        cm = _ABBREV_C.search(segment)
        if cm:
            per.carbs_g = _f(cm.group(1))
    if per.fat_g is None:
        fm = _ABBREV_F.search(segment)
        if fm:
            per.fat_g = _f(fm.group(1))
    if per.protein_g is None:
        pm = _ABBREV_P.search(segment)
        if pm:
            per.protein_g = _f(pm.group(1))
    return per if per.calories is not None else None


def _extract_inline_macro_pack(segment: str) -> Nutrition | None:
    m = _INLINE_MACRO_PACK_RE.search(segment)
    if not m:
        return None
    return Nutrition(
        calories=_f(m.group(1)),
        protein_g=_f(m.group(2)),
        carbs_g=_f(m.group(3)),
        fat_g=_f(m.group(4)),
    )


def _servings_from_text(
    text: str,
    piece_count: int | None,
    servings: int | None,
) -> int:
    return piece_count or servings or 1


def _parse_macros_block(
    text: str,
    header: re.Match[str],
    *,
    piece_count: int | None,
    servings: int | None,
) -> NutritionReport | None:
    stated_count = int(header.group("count")) if header.group("count") else None
    srv = stated_count or piece_count or servings or 1
    segment = text[header.end() : header.end() + 600]
    per = _extract_macros_from_segment(segment)
    if not per:
        return None
    return _build_report(
        per,
        srv,
        "serving",
        "Macros taken from the video description (matches creator's stated values).",
    )


def _build_report(
    per: Nutrition,
    srv: int,
    unit: str,
    note: str,
) -> NutritionReport:
    total = Nutrition(
        calories=round(per.calories * srv, 1) if per.calories else None,
        protein_g=round(per.protein_g * srv, 1) if per.protein_g else None,
        carbs_g=round(per.carbs_g * srv, 1) if per.carbs_g else None,
        fat_g=round(per.fat_g * srv, 1) if per.fat_g else None,
        fiber_g=round(per.fiber_g * srv, 1) if per.fiber_g else None,
    )
    label = _normalize_unit(unit)
    return NutritionReport(
        per_serving=per,
        total=total,
        servings=srv,
        serving_label=label if label != "serving" else None,
        matched=1,
        source="Creator caption (stated macros)",
        notes=[note],
    )


def parse_stated_nutrition(
    text: str | None,
    servings: int | None,
    *,
    ingredients: list[str] | None = None,
) -> NutritionReport | None:
    """Return fixed per-unit macros from the video caption when present."""
    if not text or not text.strip():
        return None

    t = text.strip()
    piece_count = infer_piece_count(t, ingredients)
    srv = _servings_from_text(t, piece_count, servings)

    # "Macros: 670cal, 52g P, 40g C, 34g F" (common TikTok inline format)
    mc = _MACROS_COLON_RE.search(t)
    if mc:
        segment = t[mc.end() : mc.end() + 250]
        per = _extract_inline_macro_pack(segment) or _extract_macros_from_segment(segment)
        if per:
            return _build_report(
                per,
                srv,
                "serving",
                "Per-serving macros from the video caption (fixed — will not change on recalculate).",
            )

    # Compact pack anywhere in caption (no header required)
    pack = _INLINE_MACRO_PACK_RE.search(t)
    if pack:
        per = _extract_inline_macro_pack(t[pack.start() : pack.end() + 80])
        if per:
            return _build_report(
                per,
                srv,
                "serving",
                "Macros parsed from the video caption.",
            )

    # "Macros for one (makes 8)" + calories + "38g C | 14g F | 32g P"
    for block_rx in (_MACROS_FOR_ONE_RE, _MACROS_BLOCK_RE):
        bm = block_rx.search(t)
        if bm:
            report = _parse_macros_block(t, bm, piece_count=piece_count, servings=servings)
            if report:
                return report

    # Pattern: "120 kcal per tender"
    im = _INLINE_CAL_RE.search(t)
    if im:
        unit = im.group("unit")
        per = Nutrition(calories=_f(im.group(1)))
        for key, rx in _MACRO_RES:
            mm = rx.search(t[max(0, im.start() - 80) : im.end() + 200])
            if mm:
                setattr(per, key, _f(mm.group(1)))
        srv = piece_count or servings or 1
        return _build_report(
            per,
            srv,
            unit,
            f"Per-{ _normalize_unit(unit)} macros from the video caption (fixed — will not change on recalculate).",
        )

    hm = _HEADER_RE.search(t)
    if hm:
        unit = hm.group("unit") or "serving"
        stated_count = int(hm.group("count")) if hm.group("count") else None
        srv = stated_count or piece_count or servings or 1
        segment = t[hm.end() : hm.end() + 500]
        per = _extract_macros_from_segment(segment)
        if per:
            return _build_report(
                per,
                srv,
                unit,
                "Macros taken from the video description (matches creator's stated values).",
            )

    rm = _REVERSE_HEADER_RE.search(t)
    if rm:
        unit = rm.group("unit") or "serving"
        segment = t[rm.end() : rm.end() + 500]
        per = _extract_macros_from_segment(segment)
        if per:
            srv = piece_count or servings or 1
            return _build_report(
                per,
                srv,
                unit,
                "Macros taken from the video description.",
            )

    if re.search(
        r"(?i)(?:per\s+serving|per\s+\w+|each\s+\w+|macros?\s*:|macros?\s+for\s+one|macro\s+breakdown)",
        t,
    ):
        per = _extract_macros_from_segment(t)
        if per:
            sm = _SERVINGS_OF_RE.search(t)
            use_srv = int(sm.group(1)) if sm else srv
            return _build_report(
                per,
                use_srv,
                "serving",
                "Calories/macros parsed from the video description.",
            )

    return None
