/** Shared layout class names — styles live in index.css */

export function linesToList(text: string): string[] {
  return text
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

export function numOrNull(text: string): number | null {
  const v = parseFloat(text);
  return Number.isFinite(v) && v >= 0 ? v : null;
}
