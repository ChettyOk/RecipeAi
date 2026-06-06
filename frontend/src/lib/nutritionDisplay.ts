import type { NutritionReport } from "../api";

export function nutritionSourceLabel(report: NutritionReport | null | undefined): string | null {
  if (!report?.source) return null;
  const s = report.source.toLowerCase();
  if (s.includes("caption") || s.includes("creator")) return "From video caption";
  if (s.includes("usda") && s.includes("built-in")) return "USDA + ingredient estimates";
  if (s.includes("usda")) return "USDA ingredient data";
  if (s.includes("built-in") || s.includes("average")) return "Ingredient estimates";
  if (s.includes("gemini") || s.includes("ai")) return "AI estimate";
  return report.source;
}

export function nutritionTrustLevel(report: NutritionReport | null | undefined): "high" | "medium" | "low" {
  const label = nutritionSourceLabel(report)?.toLowerCase() ?? "";
  if (label.includes("caption")) return "high";
  if (label.includes("usda")) return "medium";
  return "low";
}
