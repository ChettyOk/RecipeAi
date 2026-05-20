export type Recipe = {
  id: number;
  title: string;
  ingredients: string[];
  steps: string[];
  created_at: string;
  updated_at: string;
};

export type ExtractFromVideoResult = {
  title: string;
  ingredients: string[];
  steps: string[];
  source_url: string;
  source_video_title: string | null;
  had_transcript: boolean;
  had_description: boolean;
  used_ai: boolean;
  extraction_note: string | null;
};

const base = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

function parseApiError(text: string, status: number): Error {
  if (!text) return new Error(`Request failed (${status})`);
  try {
    const j = JSON.parse(text) as { detail?: unknown };
    if (typeof j.detail === "string") return new Error(j.detail);
    if (Array.isArray(j.detail)) {
      const parts = j.detail.map((item) => {
        if (item && typeof item === "object" && "msg" in item)
          return String((item as { msg: string }).msg);
        return JSON.stringify(item);
      });
      return new Error(parts.join("; "));
    }
  } catch {
    /* not JSON */
  }
  return new Error(text);
}

async function parse(res: Response): Promise<void> {
  if (!res.ok) {
    const text = await res.text();
    throw parseApiError(text, res.status);
  }
}

export async function fetchRecipes(): Promise<Recipe[]> {
  const res = await fetch(`${base}/recipes`);
  await parse(res);
  return res.json();
}

export async function fetchRecipe(id: number): Promise<Recipe> {
  const res = await fetch(`${base}/recipes/${id}`);
  await parse(res);
  return res.json();
}

export async function extractRecipeFromVideo(
  url: string,
  options?: { useAi?: boolean },
): Promise<ExtractFromVideoResult> {
  const useAi = options?.useAi ?? true;
  const res = await fetch(`${base}/recipes/extract-from-video`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url, use_ai: useAi }),
  });
  await parse(res);
  return res.json();
}

export async function createRecipe(data: {
  title: string;
  ingredients: string[];
  steps: string[];
}): Promise<Recipe> {
  const res = await fetch(`${base}/recipes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  await parse(res);
  return res.json();
}

export async function updateRecipe(
  id: number,
  data: Partial<{ title: string; ingredients: string[]; steps: string[] }>,
): Promise<Recipe> {
  const res = await fetch(`${base}/recipes/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  await parse(res);
  return res.json();
}

export async function deleteRecipe(id: number): Promise<void> {
  const res = await fetch(`${base}/recipes/${id}`, { method: "DELETE" });
  await parse(res);
}
