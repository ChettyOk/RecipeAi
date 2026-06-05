import type { Nutrition, NutritionReport } from "./api";

/** Units users can log their portion in. */
export const PORTION_UNITS = [
  { value: "serving", label: "Servings" },
  { value: "g", label: "Grams (g)" },
  { value: "kg", label: "Kilograms (kg)" },
  { value: "oz", label: "Ounces (oz)" },
  { value: "lb", label: "Pounds (lb)" },
  { value: "ml", label: "Millilitres (ml)" },
  { value: "cup", label: "Cups" },
  { value: "tbsp", label: "Tbsp" },
  { value: "floz", label: "Fl oz" },
] as const;

export type PortionUnit = (typeof PORTION_UNITS)[number]["value"];

export type PortionInput = {
  amount: number;
  unit: PortionUnit;
};

const TO_GRAMS: Record<string, number> = {
  g: 1,
  kg: 1000,
  oz: 28.3495,
  lb: 453.592,
};

const TO_ML: Record<string, number> = {
  ml: 1,
  l: 1000,
  tsp: 4.92892,
  tbsp: 14.7868,
  cup: 240,
  floz: 29.5735,
  fl: 29.5735,
};

export function unitLabel(nutrition: NutritionReport, count = 1): string {
  const u = nutrition.serving_label ?? "serving";
  if (count === 1) return u;
  return u.endsWith("s") ? u : `${u}s`;
}

export function portionToReferenceG(amount: number, unit: string): number | null {
  const u = unit.toLowerCase();
  if (u === "serving" || u === "servings") return null;
  if (u in TO_GRAMS) return amount * TO_GRAMS[u];
  if (u in TO_ML) return amount * TO_ML[u];
  return null;
}

export function portionScaleFactor(
  nutrition: NutritionReport,
  amount: number,
  unit: string,
): { factor: number; warning: string | null } {
  const u = unit.toLowerCase();
  if (u === "serving" || u === "servings") {
    return { factor: amount > 0 ? amount : 1, warning: null };
  }

  const refG = portionToReferenceG(amount, u);
  if (refG == null || refG <= 0) {
    return { factor: 1, warning: `Unknown unit “${unit}”.` };
  }

  const perG = nutrition.per_serving_weight_g;
  if (!perG || perG <= 0) {
    return {
      factor: 1,
      warning:
        "Cannot scale by weight yet — ingredients need g, oz, cup, or tbsp amounts so we can estimate serving size.",
    };
  }

  return { factor: refG / perG, warning: null };
}

export function scaleNutrition(n: Nutrition, factor: number): Nutrition {
  const m = (v: number | null) => (v == null ? null : Math.round(v * factor * 10) / 10);
  return {
    calories: m(n.calories),
    protein_g: m(n.protein_g),
    carbs_g: m(n.carbs_g),
    fat_g: m(n.fat_g),
    fiber_g: m(n.fiber_g),
  };
}

export function portionNutrition(
  nutrition: NutritionReport,
  input: PortionInput,
): { portion: Nutrition; factor: number; warning: string | null } {
  const { factor, warning } = portionScaleFactor(nutrition, input.amount, input.unit);
  return {
    portion: scaleNutrition(nutrition.per_serving, factor),
    factor,
    warning,
  };
}

export function formatPortionLabel(input: PortionInput, nutrition?: NutritionReport): string {
  if (input.unit === "serving") {
    const word = nutrition ? unitLabel(nutrition, input.amount) : "serving";
    return input.amount === 1 ? `1 ${word}` : `${input.amount} ${word}`;
  }
  const u = PORTION_UNITS.find((x) => x.value === input.unit);
  return `${input.amount} ${u?.label ?? input.unit}`;
}
