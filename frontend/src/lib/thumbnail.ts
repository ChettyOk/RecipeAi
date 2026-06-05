import { normalizeVideoUrl, platformDisplayName } from "./videoUrl";

export function youtubeVideoId(url: string): string | null {
  try {
    const u = new URL(normalizeVideoUrl(url));
    const host = u.hostname.replace(/^www\./, "").toLowerCase();
    if (host === "youtu.be") {
      const id = u.pathname.slice(1).split("/")[0];
      return id && id.length >= 6 ? id : null;
    }
    if (host.includes("youtube.com")) {
      const v = u.searchParams.get("v");
      if (v) return v;
    }
  } catch {
    /* ignore */
  }
  return null;
}

export function thumbnailFromSourceUrl(sourceUrl: string | null | undefined): string | null {
  if (!sourceUrl?.trim()) return null;
  const id = youtubeVideoId(sourceUrl);
  if (id) return `https://i.ytimg.com/vi/${id}/hqdefault.jpg`;
  return null;
}

export function resolveThumbnailUrl(
  thumbnailUrl: string | null | undefined,
  sourceUrl: string | null | undefined,
): string | null {
  const stored = thumbnailUrl?.trim();
  if (stored) return stored;
  return thumbnailFromSourceUrl(sourceUrl);
}

/** Stable hue (0–360) from title for fallback gradients. */
export function titleHue(title: string): number {
  let h = 0;
  for (let i = 0; i < title.length; i++) h = (h * 31 + title.charCodeAt(i)) >>> 0;
  return h % 360;
}

export function platformLabel(platform: string | null | undefined): string | null {
  if (!platform) return null;
  const name = platformDisplayName(platform);
  if (name === "Instagram") return "IG";
  return name.length > 12 ? name.slice(0, 12) : name;
}
