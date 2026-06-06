"""Download and serve recipe cover images locally (avoids expired CDN hotlinks)."""

from __future__ import annotations

import logging
import re
import urllib.error
import urllib.request
from pathlib import Path

from app.config import BACKEND_DIR
from app.thumbnail import pick_best_thumbnail

_log = logging.getLogger(__name__)

THUMB_DIR = BACKEND_DIR / "data" / "thumbnails"
_UA = "Mozilla/5.0 (compatible; RecipeAI/1.0)"


def _youtube_id_from_url(url: str) -> str | None:
    m = re.search(r"(?:youtu\.be/|[?&]v=|/shorts/|/embed/)([\w-]{11})", url)
    return m.group(1) if m else None


def resolve_remote_thumbnail_url(thumbnail_url: str | None, source_url: str | None) -> str | None:
    if thumbnail_url and thumbnail_url.strip():
        return thumbnail_url.strip()
    if source_url:
        vid = _youtube_id_from_url(source_url)
        if vid:
            return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    return None


def thumb_path(recipe_id: int) -> Path | None:
    for ext in (".jpg", ".jpeg", ".webp", ".png"):
        p = THUMB_DIR / f"{recipe_id}{ext}"
        if p.is_file():
            return p
    return None


def cache_thumbnail(recipe_id: int, thumbnail_url: str | None, source_url: str | None) -> Path | None:
    """Download remote cover to data/thumbnails/{id}.jpg. Returns path or None."""
    existing = thumb_path(recipe_id)
    if existing:
        return existing

    url = resolve_remote_thumbnail_url(thumbnail_url, source_url)
    if not url:
        return None

    THUMB_DIR.mkdir(parents=True, exist_ok=True)
    dest = THUMB_DIR / f"{recipe_id}.jpg"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA, "Referer": url})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
            ctype = (resp.headers.get("Content-Type") or "").lower()
        if len(data) < 200:
            return None
        if "webp" in ctype:
            dest = THUMB_DIR / f"{recipe_id}.webp"
        elif "png" in ctype:
            dest = THUMB_DIR / f"{recipe_id}.png"
        dest.write_bytes(data)
        return dest
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        _log.warning("thumbnail cache failed for recipe %s: %s", recipe_id, e)
        return None


def get_or_cache_thumbnail(recipe_id: int, thumbnail_url: str | None, source_url: str | None) -> Path | None:
    return thumb_path(recipe_id) or cache_thumbnail(recipe_id, thumbnail_url, source_url)


def delete_thumbnail(recipe_id: int) -> None:
    for ext in (".jpg", ".jpeg", ".webp", ".png"):
        p = THUMB_DIR / f"{recipe_id}{ext}"
        if p.is_file():
            p.unlink(missing_ok=True)
