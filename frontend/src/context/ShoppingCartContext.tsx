import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import {
  addRecipeToCart,
  clearCart,
  loadCart,
  mergeIngredients,
  removeEntryFromCart,
  saveCart,
  toggleIngredientChecked,
  type CartRecipeEntry,
  type MergedIngredient,
  type ShoppingCartState,
} from "../lib/shoppingCart";

type ShoppingCartContextValue = {
  entries: CartRecipeEntry[];
  merged: MergedIngredient[];
  uncheckedCount: number;
  addRecipe: (recipe: { id: number; title: string; ingredients: string[] }) => void;
  removeEntry: (entryId: string) => void;
  clearAll: () => void;
  toggleChecked: (mergeKey: string) => void;
  isChecked: (mergeKey: string) => boolean;
  recipeEntryCount: (recipeId: number) => number;
};

const ShoppingCartContext = createContext<ShoppingCartContextValue | null>(null);

export function ShoppingCartProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<ShoppingCartState>(() => loadCart());

  useEffect(() => {
    saveCart(state);
  }, [state]);

  const merged = useMemo(() => mergeIngredients(state.entries), [state.entries]);

  const uncheckedCount = useMemo(
    () => merged.filter((m) => !state.checked[m.mergeKey]).length,
    [merged, state.checked],
  );

  const addRecipe = useCallback((recipe: { id: number; title: string; ingredients: string[] }) => {
    setState((prev) => addRecipeToCart(prev, recipe.id, recipe.title, recipe.ingredients));
  }, []);

  const removeEntry = useCallback((entryId: string) => {
    setState((prev) => removeEntryFromCart(prev, entryId));
  }, []);

  const clearAll = useCallback(() => {
    setState(clearCart());
  }, []);

  const toggleChecked = useCallback((mergeKey: string) => {
    setState((prev) => toggleIngredientChecked(prev, mergeKey));
  }, []);

  const isChecked = useCallback((mergeKey: string) => !!state.checked[mergeKey], [state.checked]);

  const recipeEntryCount = useCallback(
    (recipeId: number) => state.entries.filter((e) => e.recipeId === recipeId).length,
    [state.entries],
  );

  const value = useMemo(
    () => ({
      entries: state.entries,
      merged,
      uncheckedCount,
      addRecipe,
      removeEntry,
      clearAll,
      toggleChecked,
      isChecked,
      recipeEntryCount,
    }),
    [state.entries, merged, uncheckedCount, addRecipe, removeEntry, clearAll, toggleChecked, isChecked, recipeEntryCount],
  );

  return <ShoppingCartContext.Provider value={value}>{children}</ShoppingCartContext.Provider>;
}

export function useShoppingCart(): ShoppingCartContextValue {
  const ctx = useContext(ShoppingCartContext);
  if (!ctx) throw new Error("useShoppingCart must be used within ShoppingCartProvider");
  return ctx;
}
