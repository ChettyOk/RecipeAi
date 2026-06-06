const STORAGE_KEY = "recipeai-favorites";

export function loadFavoriteIds(): number[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((n): n is number => Number.isInteger(n) && n > 0);
  } catch {
    return [];
  }
}

export function saveFavoriteIds(ids: number[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
}

export function toggleFavoriteId(ids: number[], recipeId: number): number[] {
  if (ids.includes(recipeId)) return ids.filter((id) => id !== recipeId);
  return [...ids, recipeId];
}
