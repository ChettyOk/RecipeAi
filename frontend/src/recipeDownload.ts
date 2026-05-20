import type { Recipe } from "./api";

function safeFilenameBase(title: string): string {
  const s = title
    .trim()
    .replace(/[^\p{L}\p{N}\s_-]/gu, "")
    .replace(/\s+/g, "-")
    .slice(0, 80);
  return s || "recipe";
}

export function recipeToMarkdown(r: Recipe): string {
  const ing = r.ingredients.map((line) => `- ${line}`).join("\n");
  const steps = r.steps.map((line, i) => `${i + 1}. ${line}`).join("\n");
  return `# ${r.title}

## Ingredients

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
  return `${r.title}
${"=".repeat(Math.min(r.title.length, 60))}

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
