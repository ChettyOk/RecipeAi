import { formatQty, parseIngredientLine, type ParsedIngredient } from "./parseIngredient";

const STORAGE_KEY = "macroreel-shopping-cart";
const OLD_STORAGE_KEY = "recipeai-shopping-cart";

export type CartRecipeEntry = {
  entryId: string;
  recipeId: number;
  title: string;
  lines: ParsedIngredient[];
  addedAt: string;
};

export type MergedIngredient = {
  mergeKey: string;
  name: string;
  unit: string | null;
  qty: number | null;
  count: number;
  displayLines: string[];
};

export type ShoppingCartState = {
  entries: CartRecipeEntry[];
  checked: Record<string, boolean>;
};

export function emptyCart(): ShoppingCartState {
  return { entries: [], checked: {} };
}

export function loadCart(): ShoppingCartState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY) ?? localStorage.getItem(OLD_STORAGE_KEY);
    if (!raw) return emptyCart();
    const parsed = JSON.parse(raw) as ShoppingCartState;
    if (!parsed || !Array.isArray(parsed.entries)) return emptyCart();
    return {
      entries: parsed.entries,
      checked: parsed.checked ?? {},
    };
  } catch {
    return emptyCart();
  }
}

export function saveCart(state: ShoppingCartState): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  localStorage.removeItem(OLD_STORAGE_KEY);
}

export function mergeIngredients(entries: CartRecipeEntry[]): MergedIngredient[] {
  const map = new Map<string, MergedIngredient>();

  for (const entry of entries) {
    for (const line of entry.lines) {
      let item = map.get(line.mergeKey);
      if (!item) {
        item = {
          mergeKey: line.mergeKey,
          name: line.name,
          unit: line.unit,
          qty: null,
          count: 0,
          displayLines: [],
        };
        map.set(line.mergeKey, item);
      }

      if (line.qty != null) {
        item.qty = (item.qty ?? 0) + line.qty;
      } else {
        item.count += 1;
        if (!item.displayLines.includes(line.raw)) {
          item.displayLines.push(line.raw);
        }
      }
    }
  }

  return Array.from(map.values()).sort((a, b) => a.name.localeCompare(b.name));
}

export function formatMergedIngredient(item: MergedIngredient): string {
  if (item.qty != null && item.qty > 0) {
    const q = formatQty(item.qty);
    if (item.unit) return `${q} ${item.unit} ${item.name}`;
    return `${q} ${item.name}`;
  }
  if (item.count > 1) return `${item.displayLines[0] ?? item.name} (×${item.count})`;
  return item.displayLines[0] ?? item.name;
}

export function createEntry(recipeId: number, title: string, ingredients: string[]): CartRecipeEntry {
  return {
    entryId: crypto.randomUUID(),
    recipeId,
    title,
    lines: ingredients.map(parseIngredientLine),
    addedAt: new Date().toISOString(),
  };
}

export function addRecipeToCart(
  state: ShoppingCartState,
  recipeId: number,
  title: string,
  ingredients: string[],
): ShoppingCartState {
  if (!ingredients.length) return state;
  return {
    ...state,
    entries: [...state.entries, createEntry(recipeId, title, ingredients)],
  };
}

export function removeEntryFromCart(state: ShoppingCartState, entryId: string): ShoppingCartState {
  const entries = state.entries.filter((e) => e.entryId !== entryId);
  const activeKeys = new Set(mergeIngredients(entries).map((m) => m.mergeKey));
  const checked: Record<string, boolean> = {};
  for (const [key, val] of Object.entries(state.checked)) {
    if (activeKeys.has(key) && val) checked[key] = true;
  }
  return { entries, checked };
}

export function toggleIngredientChecked(state: ShoppingCartState, mergeKey: string): ShoppingCartState {
  const next = { ...state.checked };
  if (next[mergeKey]) delete next[mergeKey];
  else next[mergeKey] = true;
  return { ...state, checked: next };
}

export function clearCart(): ShoppingCartState {
  return emptyCart();
}
