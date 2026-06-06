export type UnitSystem = "metric" | "imperial";

export const BODY_STAT_DEFAULTS = {
  age: 30,
  heightCm: 170,
  weightKg: 70,
} as const;

export function resolveBodyStats(stats: {
  heightCm: number | null;
  weightKg: number | null;
  age: number | null;
}): { heightCm: number; weightKg: number; age: number } {
  return {
    heightCm: stats.heightCm ?? BODY_STAT_DEFAULTS.heightCm,
    weightKg: stats.weightKg ?? BODY_STAT_DEFAULTS.weightKg,
    age: stats.age ?? BODY_STAT_DEFAULTS.age,
  };
}

const UNITS_KEY = "recipeai-body-units";

export function getPreferredUnits(): UnitSystem {
  const v = localStorage.getItem(UNITS_KEY);
  return v === "imperial" ? "imperial" : "metric";
}

export function setPreferredUnits(u: UnitSystem): void {
  localStorage.setItem(UNITS_KEY, u);
}

export function cmToFeetInches(cm: number): { ft: number; inches: number } {
  const totalIn = Math.round(cm / 2.54);
  const ft = Math.floor(totalIn / 12);
  const inches = totalIn % 12;
  return { ft, inches };
}

export function feetInchesToCm(ft: number, inches: number): number {
  return Math.round((ft * 12 + inches) * 2.54);
}

export function kgToLb(kg: number): number {
  return Math.round(kg * 2.20462);
}

export function lbToKg(lb: number): number {
  return Math.round(lb / 2.20462 * 10) / 10;
}

export function range(start: number, end: number, step = 1): number[] {
  const out: number[] = [];
  for (let v = start; v <= end; v += step) out.push(v);
  return out;
}
