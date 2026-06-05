"""Build a recipe draft from video text without calling an LLM (rough split for user editing).

Tuned for social-video descriptions (TikTok/Instagram), which often put the whole recipe on
ONE line separated by `•` bullets and ` - ` section markers, mixed with emojis and hashtags.
"""

from __future__ import annotations

import re

from app.schemas import RecipeBase

_MAX_TITLE = 120
_MAX_LINES = 120

_ING_HEADER = re.compile(
    r"(?im)^\s*(ingredients?|what\s+you(?:'|’|ll)?\s*need|you\s+will\s+need|shopping\s+list)\b\s*[:\-]?\s*",
)
_STEP_HEADER = re.compile(
    r"(?im)^\s*(instructions?|directions?|method|steps?|how\s+to\s+make|preparation|recipe)\b\s*[:\-]?\s*",
)
_SERVINGS_RE = re.compile(r"(?i)\b(?:serves|servings?|yields?|makes)\s*[:\-]?\s*(\d{1,3})\b")
_SERVINGS_OF_RE = re.compile(r"(?i)per\s+serving\s*\(?\s*of\s+(\d{1,3})")
_PREP_RE = re.compile(r"(?i)\bprep(?:\s*time)?\s*[:\-]?\s*(\d{1,4})\s*(?:min|minutes)")
_COOK_RE = re.compile(r"(?i)\b(?:cook|bake)(?:\s*time)?\s*[:\-]?\s*(\d{1,4})\s*(?:min|minutes)")

# Lines that mark the end of the ingredient list / are not recipe content.
_STOP_RE = re.compile(
    r"(?i)^\s*(approx|per\s+serving|nutrition|macros?|calories|kcal|follow|comment|save\s+this|link\s+in|recipe\s+below)\b",
)

_BULLET_CHARS = "•·▪►●◦‣*"
_EMOJI_RE = re.compile(
    "[" 
    "\U0001F000-\U0001FAFF"  # symbols & pictographs, emoji
    "\U00002600-\U000027BF"  # misc symbols & dingbats
    "\U0001F1E6-\U0001F1FF"  # regional indicators
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U00002190-\U000021FF"  # arrows
    "\U00002B00-\U00002BFF"  # misc symbols & arrows
    "\U0001F3FB-\U0001F3FF"  # skin tone modifiers
    "\U0000200D"             # zero-width joiner
    "]+",
    flags=re.UNICODE,
)


def _strip_emoji(s: str) -> str:
    return _EMOJI_RE.sub(" ", s)


def _first_int(*patterns_text: tuple[re.Pattern[str], str]) -> int | None:
    for pattern, text in patterns_text:
        m = pattern.search(text)
        if m:
            try:
                return int(m.group(1))
            except (ValueError, TypeError):
                continue
    return None


def _normalize(blob: str) -> str:
    """Turn a bullet/emoji/hashtag-laden single-line description into clean newline-separated lines."""
    text = re.sub(r"#\w+", "", blob)  # drop hashtags
    text = _strip_emoji(text)
    text = re.sub(rf"[{re.escape(_BULLET_CHARS)}]", "\n", text)  # bullets -> newlines
    text = re.sub(r"\s[-–—]\s", "\n", text)  # " - " section markers -> newlines
    return text


def _lines(blob: str) -> list[str]:
    return [ln.strip(" \t,") for ln in blob.splitlines() if ln.strip(" \t,")]


def _looks_ingredient_line(s: str) -> bool:
    if len(s) > 200:
        return False
    if re.match(r"^[\d¼½¾⅓⅔⅛]+\s", s):
        return True
    if s[:1] in _BULLET_CHARS + "-" or re.match(r"^\d+[\).]\s+", s):
        return True
    lowered = f" {s.lower()} "
    units = (
        " cup", " cups", " tbsp", " tbs", " tsp", " tablespoon", " teaspoon", " gram", " grams",
        " g ", "g ", " ml ", " oz ", " lb ", " pound", " pinch", " clove", " can ", " handful",
        " chopped", " diced", " sliced", " minced", " shredded",
    )
    return any(u in lowered for u in units)


def _split_on_headers(text: str) -> tuple[str | None, str | None]:
    t = text.strip()
    if not t:
        return None, None
    im = _ING_HEADER.search(t)
    sm = _STEP_HEADER.search(t)
    ing_block: str | None = None
    step_block: str | None = None
    if im and sm:
        if im.start() < sm.start():
            ing_block = t[im.end() : sm.start()].strip()
            step_block = t[sm.end() :].strip()
        else:
            step_block = t[sm.end() : im.start()].strip()
            ing_block = t[im.end() :].strip()
    elif im:
        ing_block = t[im.end() :].strip()
    elif sm:
        step_block = t[sm.end() :].strip()
    return ing_block, step_block


def _clean_line(ln: str) -> str:
    s = re.sub(r"^\d+[\).]\s*", "", ln)
    s = re.sub(rf"^[{re.escape(_BULLET_CHARS)}\-]\s*", "", s)
    return s.strip(" \t,.-")


def _parse_ingredients(block: str | None) -> list[str]:
    if not block:
        return []
    out: list[str] = []
    for ln in _lines(block):
        if _STOP_RE.match(ln):
            break
        s = _clean_line(ln)
        if not s:
            continue
        if _looks_ingredient_line(ln) or _looks_ingredient_line(s) or len(out) < 40:
            out.append(s)
        elif out:
            break
    return out[:_MAX_LINES]


def _parse_steps(block: str | None) -> list[str]:
    if not block:
        return []
    lines = [ln for ln in _lines(block) if not _STOP_RE.match(ln)]
    if not lines:
        return []
    if len(lines) <= 3 and any(len(x) > 120 for x in lines):
        merged = " ".join(lines)
        parts = re.split(r"(?<=[.!?])\s+", merged)
        return [_clean_line(p) for p in parts if p.strip()][:_MAX_LINES]
    return [_clean_line(x) for x in lines][:_MAX_LINES]


def _clean_title(title: str) -> str:
    t = _strip_emoji(title or "").strip()
    # Cut at an inline "Ingredients:" header or the first sentence end, whichever comes first.
    cut = re.split(r"(?i)\b(ingredients?|what you|recipe below)\b", t, maxsplit=1)[0].strip()
    if cut:
        t = cut
    sentence = re.split(r"(?<=[.!?])\s", t, maxsplit=1)[0].strip()
    if 8 <= len(sentence) <= _MAX_TITLE:
        t = sentence
    t = t.strip(" \t,.-:")
    return t[:_MAX_TITLE] or "Imported recipe"


def draft_from_text(title: str, blob: str, *, transcript: str = "") -> RecipeBase:
    """Best-effort split of combined recipe text (description + transcript + on-screen text)."""
    raw = (blob or "").strip()
    norm = _normalize(raw)

    ing_block, step_block = _split_on_headers(norm)
    ingredients = _parse_ingredients(ing_block)
    steps = _parse_steps(step_block)

    if not ingredients and not steps and norm:
        lines = _lines(norm)
        ing_cand: list[str] = []
        rest_start = 0
        for i, ln in enumerate(lines):
            if _STOP_RE.match(ln):
                rest_start = i
                break
            if _looks_ingredient_line(ln):
                ing_cand.append(_clean_line(ln))
                rest_start = i + 1
            elif ing_cand:
                break
        if len(ing_cand) >= 2:
            ingredients = ing_cand[:_MAX_LINES]
            rest = [ln for ln in lines[rest_start:] if not _STOP_RE.match(ln)]
            steps = [_clean_line(x) for x in rest][:_MAX_LINES]
        else:
            steps = [_clean_line(x) for x in lines if not _STOP_RE.match(x)][:_MAX_LINES]

    if not steps and transcript.strip():
        steps = _lines(transcript)[:_MAX_LINES]

    return RecipeBase(
        title=_clean_title(title),
        ingredients=ingredients[:_MAX_LINES],
        steps=steps[:_MAX_LINES],
        prep_time_min=_first_int((_PREP_RE, raw)),
        cook_time_min=_first_int((_COOK_RE, raw)),
        servings=_first_int((_SERVINGS_RE, raw), (_SERVINGS_OF_RE, raw)),
    )
