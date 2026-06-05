import type { Recipe } from "./api";

function safeFilenameBase(title: string): string {
  const s = title
    .trim()
    .replace(/[^\p{L}\p{N}\s_-]/gu, "")
    .replace(/\s+/g, "-")
    .slice(0, 80);
  return s || "recipe";
}

function metaLine(r: Recipe): string {
  const bits: string[] = [];
  if (r.prep_time_min != null) bits.push(`Prep ${r.prep_time_min} min`);
  if (r.cook_time_min != null) bits.push(`Cook ${r.cook_time_min} min`);
  if (r.servings != null) bits.push(`Serves ${r.servings}`);
  return bits.join(" · ");
}

function macrosLine(r: Recipe): string {
  const n = r.nutrition?.per_serving;
  if (!n) return "";
  const parts: string[] = [];
  if (n.calories != null) parts.push(`${Math.round(n.calories)} kcal`);
  if (n.protein_g != null) parts.push(`${Math.round(n.protein_g)}g protein`);
  if (n.carbs_g != null) parts.push(`${Math.round(n.carbs_g)}g carbs`);
  if (n.fat_g != null) parts.push(`${Math.round(n.fat_g)}g fat`);
  if (n.fiber_g != null) parts.push(`${Math.round(n.fiber_g)}g fiber`);
  return parts.length ? `Per serving: ${parts.join(", ")}` : "";
}

export function recipeToMarkdown(r: Recipe): string {
  const ing = r.ingredients.map((line) => `- ${line}`).join("\n");
  const steps = r.steps.map((line, i) => `${i + 1}. ${line}`).join("\n");
  const meta = metaLine(r);
  const macros = macrosLine(r);
  const flags = r.dietary_flags?.length ? `**Dietary:** ${r.dietary_flags.join(", ")}\n\n` : "";
  return `# ${r.title}

${meta ? `_${meta}_\n\n` : ""}${flags}${macros ? `**${macros}**\n\n` : ""}## Ingredients

${ing || "_None listed_"}

## Steps

${steps || "_None listed_"}

---
_Exported ${r.created_at} (updated ${r.updated_at})_
`;
}

export function recipeToPlainText(r: Recipe): string {
  const ing = r.ingredients.map((line) => `• ${line}`).join("\n");
  const steps = r.steps.map((line, i) => `${i + 1}. ${line}`).join("\n");
  const meta = metaLine(r);
  const macros = macrosLine(r);
  const flags = r.dietary_flags?.length ? `Dietary: ${r.dietary_flags.join(", ")}\n` : "";
  return `${r.title}
${"=".repeat(Math.min(r.title.length, 60))}
${meta ? `${meta}\n` : ""}${flags}${macros ? `${macros}\n` : ""}
INGREDIENTS
${ing || "(none)"}

STEPS
${steps || "(none)"}

---
Created: ${r.created_at}
Updated: ${r.updated_at}
`;
}

export function recipeToJson(r: Recipe): string {
  return JSON.stringify(r, null, 2);
}

export function downloadText(filename: string, body: string, mime: string): void {
  const blob = new Blob([body], { type: mime });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noopener";
  a.click();
  URL.revokeObjectURL(url);
}

export function downloadRecipe(r: Recipe, format: "md" | "txt" | "json"): void {
  const base = safeFilenameBase(r.title);
  if (format === "md") {
    downloadText(`${base}.md`, recipeToMarkdown(r), "text/markdown;charset=utf-8");
  } else if (format === "txt") {
    downloadText(`${base}.txt`, recipeToPlainText(r), "text/plain;charset=utf-8");
  } else {
    downloadText(`${base}.json`, recipeToJson(r), "application/json;charset=utf-8");
  }
}
