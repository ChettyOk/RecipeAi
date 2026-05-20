import { useCallback, useEffect, useState } from "react";
import type { Recipe } from "./api";
import * as api from "./api";
import { RecipeDetailModal } from "./RecipeDetailModal";

function linesToList(text: string): string[] {
  return text
    .split("\n")
    .map((s) => s.trim())
    .filter(Boolean);
}

export default function App() {
  const [theme, setTheme] = useState<"dark" | "light">(() =>
    document.documentElement.dataset.theme === "light" ? "light" : "dark",
  );

  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [editingId, setEditingId] = useState<number | null>(null);
  const [title, setTitle] = useState("");
  const [ingredientsText, setIngredientsText] = useState("");
  const [stepsText, setStepsText] = useState("");

  const [viewId, setViewId] = useState<number | null>(null);

  const [videoUrl, setVideoUrl] = useState("");
  const [useExtractAi, setUseExtractAi] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [extractBanner, setExtractBanner] = useState<string | null>(null);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem("recipeai-theme", theme);
  }, [theme]);

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      setRecipes(await api.fetchRecipes());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load recipes");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  function resetForm() {
    setEditingId(null);
    setTitle("");
    setIngredientsText("");
    setStepsText("");
    setExtractBanner(null);
  }

  function startCreate() {
    resetForm();
  }

  function startEdit(r: Recipe) {
    setExtractBanner(null);
    setEditingId(r.id);
    setTitle(r.title);
    setIngredientsText(r.ingredients.join("\n"));
    setStepsText(r.steps.join("\n"));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const ingredients = linesToList(ingredientsText);
    const steps = linesToList(stepsText);
    try {
      if (editingId == null) {
        await api.createRecipe({ title, ingredients, steps });
      } else {
        await api.updateRecipe(editingId, { title, ingredients, steps });
      }
      resetForm();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    }
  }

  async function handleExtractFromVideo(e: React.FormEvent) {
    e.preventDefault();
    const u = videoUrl.trim();
    if (!u) return;
    setError(null);
    setExtractBanner(null);
    setExtracting(true);
    try {
      const r = await api.extractRecipeFromVideo(u, { useAi: useExtractAi });
      setEditingId(null);
      setTitle(r.title);
      setIngredientsText(r.ingredients.join("\n"));
      setStepsText(r.steps.join("\n"));
      const bits: string[] = [];
      if (r.had_transcript) bits.push("subtitles/captions");
      if (r.had_description) bits.push("description");
      const src = bits.length ? ` Used ${bits.join(" and ")} from the page.` : "";
      const mode = r.used_ai
        ? "Google Gemini structured the draft."
        : "No AI — text was split with simple rules from the transcript/description.";
      const note = r.extraction_note ? ` ${r.extraction_note}` : "";
      setExtractBanner(
        `Draft loaded from video${r.source_video_title ? ` (“${r.source_video_title}”)` : ""}.${src} ${mode}${note} Edit below, then click Create to save.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Extract failed");
    } finally {
      setExtracting(false);
    }
  }

  async function handleDelete(id: number) {
    if (!window.confirm("Delete this recipe?")) return;
    setError(null);
    try {
      await api.deleteRecipe(id);
      if (editingId === id) resetForm();
      if (viewId === id) setViewId(null);
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  const card: React.CSSProperties = {
    background: "var(--bg-card)",
    borderRadius: 12,
    padding: "1rem 1.25rem",
    marginBottom: "1.5rem",
    boxShadow: "var(--shadow)",
    border: "1px solid var(--border)",
  };

  return (
    <div style={{ maxWidth: 720, margin: "0 auto", padding: "1.25rem" }}>
      <header
        style={{
          marginBottom: "1.5rem",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          gap: "1rem",
          flexWrap: "wrap",
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: "1.75rem", color: "var(--text)" }}>Recipes</h1>
          <p style={{ margin: "0.35rem 0 0", color: "var(--text-muted)", maxWidth: "36rem" }}>
            Dark-first UI. Import from video with or without Gemini AI, edit, save, view, and download.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
          style={{
            background: "var(--btn-secondary-bg)",
            color: "var(--btn-secondary-text)",
            border: "1px solid var(--border)",
            borderRadius: 8,
            padding: "0.45rem 0.85rem",
            fontSize: "0.85rem",
            whiteSpace: "nowrap",
          }}
        >
          {theme === "dark" ? "Light mode" : "Dark mode"}
        </button>
      </header>

      {error ? (
        <div
          role="alert"
          style={{
            background: "var(--danger-soft-bg)",
            color: "var(--danger-soft-text)",
            padding: "0.75rem 1rem",
            borderRadius: 8,
            marginBottom: "1rem",
            border: "1px solid var(--border)",
          }}
        >
          {error}
        </div>
      ) : null}

      {extractBanner ? (
        <div
          role="status"
          style={{
            background: "var(--success-bg)",
            color: "var(--success-text)",
            padding: "0.75rem 1rem",
            borderRadius: 8,
            marginBottom: "1rem",
            fontSize: "0.95rem",
            border: "1px solid var(--border)",
          }}
        >
          {extractBanner}
        </div>
      ) : null}

      <section style={card}>
        <h2 style={{ margin: "0 0 0.75rem", fontSize: "1.1rem", color: "var(--text)" }}>Import from video</h2>
        <p style={{ margin: "0 0 0.75rem", fontSize: "0.9rem", color: "var(--text-muted)" }}>
          Paste a public URL. The server uses yt-dlp for title, description, and captions. Turn off “Use Gemini” to
          structure the draft with heuristics only (no Google API usage); quality is lower but fine for a starting point.
        </p>
        <form onSubmit={(e) => void handleExtractFromVideo(e)} style={{ display: "grid", gap: "0.65rem" }}>
          <label style={{ display: "grid", gap: "0.25rem" }}>
            <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text)" }}>Video URL</span>
            <input
              type="url"
              inputMode="url"
              placeholder="https://www.youtube.com/watch?v=… or https://www.tiktok.com/…"
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              style={{ padding: "0.5rem 0.65rem", borderRadius: 8 }}
            />
          </label>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.5rem",
              fontSize: "0.9rem",
              color: "var(--text-muted)",
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              checked={useExtractAi}
              onChange={(e) => setUseExtractAi(e.target.checked)}
              style={{ width: "1rem", height: "1rem", accentColor: "var(--accent)" }}
            />
            <span>Use Gemini (Google AI) to structure ingredients &amp; steps (uses your API quota)</span>
          </label>
          <div>
            <button
              type="submit"
              disabled={extracting || !videoUrl.trim()}
              style={{
                background:
                  extracting || !videoUrl.trim() ? "var(--text-muted)" : "var(--accent)",
                color: "#fff",
                border: "none",
                borderRadius: 8,
                padding: "0.5rem 1rem",
                cursor: extracting || !videoUrl.trim() ? "not-allowed" : "pointer",
              }}
            >
              {extracting ? "Extracting…" : "Extract into form"}
            </button>
          </div>
        </form>
      </section>

      <section style={card}>
        <h2 style={{ margin: "0 0 0.75rem", fontSize: "1.1rem", color: "var(--text)" }}>
          {editingId == null ? "New recipe" : `Edit recipe #${editingId}`}
        </h2>
        <form onSubmit={handleSubmit} style={{ display: "grid", gap: "0.75rem" }}>
          <label style={{ display: "grid", gap: "0.25rem" }}>
            <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text)" }}>Title</span>
            <input required value={title} onChange={(e) => setTitle(e.target.value)} style={{ padding: "0.5rem 0.65rem", borderRadius: 8 }} />
          </label>
          <label style={{ display: "grid", gap: "0.25rem" }}>
            <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text)" }}>Ingredients (one per line)</span>
            <textarea
              value={ingredientsText}
              onChange={(e) => setIngredientsText(e.target.value)}
              rows={5}
              style={{ padding: "0.5rem 0.65rem", borderRadius: 8, resize: "vertical" }}
            />
          </label>
          <label style={{ display: "grid", gap: "0.25rem" }}>
            <span style={{ fontWeight: 600, fontSize: "0.9rem", color: "var(--text)" }}>Steps (one per line)</span>
            <textarea
              value={stepsText}
              onChange={(e) => setStepsText(e.target.value)}
              rows={6}
              style={{ padding: "0.5rem 0.65rem", borderRadius: 8, resize: "vertical" }}
            />
          </label>
          <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
            <button
              type="submit"
              style={{
                background: "var(--accent)",
                color: "#fff",
                border: "none",
                borderRadius: 8,
                padding: "0.5rem 1rem",
              }}
            >
              {editingId == null ? "Create" : "Save changes"}
            </button>
            <button
              type="button"
              onClick={startCreate}
              style={{
                background: "var(--btn-secondary-bg)",
                color: "var(--btn-secondary-text)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: "0.5rem 1rem",
              }}
            >
              Clear / new
            </button>
          </div>
        </form>
      </section>

      <section>
        <h2 style={{ fontSize: "1.1rem", margin: "0 0 0.75rem", color: "var(--text)" }}>Your recipes</h2>
        {loading ? <p style={{ color: "var(--text-muted)" }}>Loading…</p> : null}
        {!loading && recipes.length === 0 ? (
          <p style={{ color: "var(--text-muted)" }}>No recipes yet. Add one above.</p>
        ) : null}
        <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "grid", gap: "0.75rem" }}>
          {recipes.map((r) => (
            <li
              key={r.id}
              style={{
                ...card,
                marginBottom: 0,
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", gap: "0.75rem", flexWrap: "wrap" }}>
                <button
                  type="button"
                  onClick={() => setViewId(r.id)}
                  style={{
                    background: "none",
                    border: "none",
                    padding: 0,
                    textAlign: "left",
                    cursor: "pointer",
                    color: "var(--link)",
                  }}
                >
                  <strong style={{ fontSize: "1.05rem", textDecoration: "underline" }}>{r.title}</strong>
                </button>
                <div style={{ display: "flex", gap: "0.35rem", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    onClick={() => setViewId(r.id)}
                    style={{
                      background: "var(--view-bg)",
                      color: "var(--view-text)",
                      border: "none",
                      borderRadius: 8,
                      padding: "0.35rem 0.65rem",
                      fontSize: "0.85rem",
                    }}
                  >
                    View
                  </button>
                  <button
                    type="button"
                    onClick={() => startEdit(r)}
                    style={{
                      background: "var(--edit-bg)",
                      color: "var(--edit-text)",
                      border: "none",
                      borderRadius: 8,
                      padding: "0.35rem 0.65rem",
                      fontSize: "0.85rem",
                    }}
                  >
                    Edit
                  </button>
                  <button
                    type="button"
                    onClick={() => void handleDelete(r.id)}
                    style={{
                      background: "var(--danger-bg)",
                      color: "var(--danger-text)",
                      border: "none",
                      borderRadius: 8,
                      padding: "0.35rem 0.65rem",
                      fontSize: "0.85rem",
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
              <p style={{ margin: "0.5rem 0 0", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                {r.ingredients.length} ingredients · {r.steps.length} steps — click title or View for full recipe
              </p>
            </li>
          ))}
        </ul>
      </section>

      {viewId != null ? (
        <RecipeDetailModal recipeId={viewId} onClose={() => setViewId(null)} onDeleted={() => void load()} />
      ) : null}
    </div>
  );
}
