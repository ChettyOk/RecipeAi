"""Build a recipe draft from video text without calling an LLM (rough split for user editing)."""

from __future__ import annotations

import re

from app.schemas import RecipeBase
from app.video_context import VideoContext

_MAX_TITLE = 200
_MAX_LINES = 120

_ING_HEADER = re.compile(
    r"(?is)(?:^|\n)\s*(ingredients?|what\s+you(?:'|’|ll)?\s*need|you\s+will\s+need|shopping\s+list)\s*[:]\s*",
)
_STEP_HEADER = re.compile(
    r"(?is)(?:^|\n)\s*(instructions?|directions|method|steps|how\s+to\s+make|preparation)\s*[:]\s*",
)


def _norm_title(ctx: VideoContext) -> str:
    t = (ctx.title or "").strip() or "Imported recipe"
    return t[:_MAX_TITLE]


def _lines(blob: str) -> list[str]:
    return [ln.strip() for ln in blob.splitlines() if ln.strip()]


def _looks_ingredient_line(s: str) -> bool:
    if len(s) > 200:
        return False
    if re.match(r"^[\d¼½¾⅓⅔⅛]+\s", s):
        return True
    if s[:1] in "-•*·▪►" or re.match(r"^\d+[\).]\s+", s):
        return True
    lowered = s.lower()
    return any(
        u in lowered
        for u in (
            " cup",
            " tbsp",
            " tbs",
            " tsp",
            " tablespoon",
            " teaspoon",
            " gram",
            " g ",
            " ml ",
            " oz ",
            " lb ",
            " pound",
            " pinch",
            " chopped",
            " diced",
            " sliced",
        )
    )


def _split_on_headers(text: str) -> tuple[str | None, str | None]:
    """Try to find ingredients and instructions blocks using common headers."""
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


def _parse_ingredients(block: str | None) -> list[str]:
    if not block:
        return []
    out: list[str] = []
    for ln in _lines(block):
        s = re.sub(r"^\d+[\).]\s*", "", ln)
        s = re.sub(r"^[-•*·▪►]\s*", "", s).strip()
        if s and (_looks_ingredient_line(ln) or _looks_ingredient_line(s) or len(out) < 40):
            out.append(s)
        elif out:
            break
    return out[:_MAX_LINES]


def _parse_steps(block: str | None) -> list[str]:
    if not block:
        return []
    lines = _lines(block)
    if not lines:
        return []
    if len(lines) <= 3 and any(len(x) > 120 for x in lines):
        merged = " ".join(lines)
        parts = re.split(r"(?<=[.!?])\s+", merged)
        return [p.strip() for p in parts if p.strip()][: _MAX_LINES]
    return lines[:_MAX_LINES]


def draft_from_video_context(ctx: VideoContext) -> RecipeBase:
    title = _norm_title(ctx)
    blob = "\n\n".join(x for x in (ctx.description.strip(), ctx.transcript.strip()) if x)

    ing_block, step_block = _split_on_headers(blob)
    ingredients = _parse_ingredients(ing_block)
    steps = _parse_steps(step_block)

    if not ingredients and not steps and blob:
        lines = _lines(blob)
        ing_cand: list[str] = []
        rest_start = 0
        for i, ln in enumerate(lines):
            if _looks_ingredient_line(ln):
                s = re.sub(r"^[-•*·▪►]\s*", "", ln)
                s = re.sub(r"^\d+[\).]\s*", "", s).strip()
                ing_cand.append(s)
                rest_start = i + 1
            elif ing_cand:
                break
        if len(ing_cand) >= 2:
            ingredients = ing_cand[:_MAX_LINES]
            steps = lines[rest_start : rest_start + _MAX_LINES] if rest_start < len(lines) else []
        else:
            steps = lines[:_MAX_LINES]

    if not steps and ctx.transcript.strip():
        steps = _lines(ctx.transcript)[:_MAX_LINES]

    return RecipeBase(
        title=title,
        ingredients=ingredients[:_MAX_LINES],
        steps=steps[:_MAX_LINES],
    )
