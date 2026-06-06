import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { loadFavoriteIds, saveFavoriteIds, toggleFavoriteId } from "../lib/favorites";

type FavoritesContextValue = {
  favoriteIds: number[];
  isFavorite: (recipeId: number) => boolean;
  toggleFavorite: (recipeId: number) => void;
  removeFavorite: (recipeId: number) => void;
  favoriteCount: number;
};

const FavoritesContext = createContext<FavoritesContextValue | null>(null);

export function FavoritesProvider({ children }: { children: ReactNode }) {
  const [favoriteIds, setFavoriteIds] = useState<number[]>(() => loadFavoriteIds());

  useEffect(() => {
    saveFavoriteIds(favoriteIds);
  }, [favoriteIds]);

  const isFavorite = useCallback((recipeId: number) => favoriteIds.includes(recipeId), [favoriteIds]);

  const toggleFavorite = useCallback((recipeId: number) => {
    setFavoriteIds((prev) => toggleFavoriteId(prev, recipeId));
  }, []);

  const removeFavorite = useCallback((recipeId: number) => {
    setFavoriteIds((prev) => prev.filter((id) => id !== recipeId));
  }, []);

  const value = useMemo(
    () => ({
      favoriteIds,
      isFavorite,
      toggleFavorite,
      removeFavorite,
      favoriteCount: favoriteIds.length,
    }),
    [favoriteIds, isFavorite, toggleFavorite, removeFavorite],
  );

  return <FavoritesContext.Provider value={value}>{children}</FavoritesContext.Provider>;
}

export function useFavorites(): FavoritesContextValue {
  const ctx = useContext(FavoritesContext);
  if (!ctx) throw new Error("useFavorites must be used within FavoritesProvider");
  return ctx;
}
