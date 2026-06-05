"""Pick the best cover image URL from yt-dlp metadata."""

from __future__ import annotations

from typing import Any


def pick_best_thumbnail(info: dict[str, Any]) -> str | None:
    """Prefer the largest thumbnail entry; fall back to the single `thumbnail` field."""
    thumbs = info.get("thumbnails")
    if isinstance(thumbs, list) and thumbs:
        best: dict[str, Any] | None = None
        best_area = -1
        for ent in thumbs:
            if not isinstance(ent, dict):
                continue
            url = ent.get("url")
            if not url:
                continue
            w = int(ent.get("width") or 0)
            h = int(ent.get("height") or 0)
            area = w * h if w and h else 0
            if area > best_area or best is None:
                best_area = area
                best = ent
        if best and best.get("url"):
            return str(best["url"]).strip() or None

    thumb = info.get("thumbnail")
    if thumb:
        return str(thumb).strip() or None
    return None
