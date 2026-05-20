import { useEffect, useState } from "react";
import type { Recipe } from "./api";
import * as api from "./api";
import { downloadRecipe } from "./recipeDownload";

type Props = {
  recipeId: number;
  onClose: () => void;
  onDeleted: () => void;
};

export function RecipeDetailModal({ recipeId, onClose, onDeleted }: Props) {
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setErr(null);
    void api
      .fetchRecipe(recipeId)
      .then((r) => {
        if (!cancelled) setRecipe(r);
      })
      .catch((e) => {
        if (!cancelled) setErr(e instanceof Error ? e.message : "Failed to load");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [recipeId]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="recipe-detail-title"
      style={{
        position: "fixed",
        inset: 0,
        background: "var(--modal-scrim)",
        display: "flex",
        alignItems: "stretch",
        justifyContent: "center",
        padding: "1rem",
        zIndex: 50,
        overflow: "auto",
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        style={{
          background: "var(--bg-card)",
          color: "var(--text)",
          borderRadius: 12,
          maxWidth: 640,
          width: "100%",
          margin: "auto",
          maxHeight: "min(92vh, 900px)",
          display: "flex",
          flexDirection: "column",
          boxShadow: "var(--modal-shadow)",
          border: "1px solid var(--border)",
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div
          style={{
            padding: "1rem 1.25rem",
            borderBottom: "1px solid var(--border)",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            gap: "0.75rem",
            flexWrap: "wrap",
          }}
        >
          <div style={{ minWidth: 0 }}>
            <h2 id="recipe-detail-title" style={{ margin: 0, fontSize: "1.35rem", wordBreak: "break-word" }}>
              {loading ? "Loading…" : recipe?.title ?? "Recipe"}
            </h2>
            {!loading && recipe ? (
              <p style={{ margin: "0.35rem 0 0", fontSize: "0.8rem", color: "var(--text-muted)" }}>
                Updated {new Date(recipe.updated_at).toLocaleString()}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            style={{
              border: "1px solid var(--border)",
              background: "var(--btn-secondary-bg)",
              color: "var(--btn-secondary-text)",
              borderRadius: 8,
              padding: "0.4rem 0.75rem",
              fontSize: "0.9rem",
            }}
          >
            Close
          </button>
        </div>

        <div style={{ padding: "1rem 1.25rem", overflow: "auto", flex: 1 }}>
          {err ? (
            <p style={{ color: "var(--danger-soft-text)" }} role="alert">
              {err}
            </p>
          ) : null}
          {loading ? <p style={{ color: "var(--text-muted)" }}>Loading recipe…</p> : null}
          {!loading && recipe ? (
            <>
              <section style={{ marginBottom: "1.25rem" }}>
                <h3 style={{ margin: "0 0 0.5rem", fontSize: "1rem", color: "var(--text-muted)" }}>Ingredients</h3>
                <ul style={{ margin: 0, paddingLeft: "1.25rem" }}>
                  {recipe.ingredients.length === 0 ? (
                    <li style={{ color: "var(--text-muted)" }}>None listed</li>
                  ) : (
                    recipe.ingredients.map((line, i) => <li key={i}>{line}</li>)
                  )}
                </ul>
              </section>
              <section>
                <h3 style={{ margin: "0 0 0.5rem", fontSize: "1rem", color: "var(--text-muted)" }}>Steps</h3>
                <ol style={{ margin: 0, paddingLeft: "1.25rem" }}>
                  {recipe.steps.length === 0 ? (
                    <li style={{ color: "var(--text-muted)" }}>None listed</li>
                  ) : (
                    recipe.steps.map((line, i) => <li key={i}>{line}</li>)
                  )}
                </ol>
              </section>
            </>
          ) : null}
        </div>

        {!loading && recipe ? (
          <div
            style={{
              padding: "1rem 1.25rem",
              borderTop: "1px solid var(--border)",
              display: "flex",
              flexWrap: "wrap",
              gap: "0.5rem",
              alignItems: "center",
            }}
          >
            <span style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginRight: "0.25rem" }}>Download</span>
            <button
              type="button"
              onClick={() => downloadRecipe(recipe, "md")}
              style={{
                background: "var(--btn-secondary-bg)",
                color: "var(--btn-secondary-text)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: "0.4rem 0.65rem",
                fontSize: "0.85rem",
              }}
            >
              Markdown (.md)
            </button>
            <button
              type="button"
              onClick={() => downloadRecipe(recipe, "txt")}
              style={{
                background: "var(--btn-secondary-bg)",
                color: "var(--btn-secondary-text)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: "0.4rem 0.65rem",
                fontSize: "0.85rem",
              }}
            >
              Plain text (.txt)
            </button>
            <button
              type="button"
              onClick={() => downloadRecipe(recipe, "json")}
              style={{
                background: "var(--btn-secondary-bg)",
                color: "var(--btn-secondary-text)",
                border: "1px solid var(--border)",
                borderRadius: 8,
                padding: "0.4rem 0.65rem",
                fontSize: "0.85rem",
              }}
            >
              JSON (.json)
            </button>
            <span style={{ flex: 1 }} />
            <button
              type="button"
              onClick={async () => {
                if (!window.confirm("Delete this recipe permanently?")) return;
                try {
                  await api.deleteRecipe(recipe.id);
                  onDeleted();
                  onClose();
                } catch (e) {
                  window.alert(e instanceof Error ? e.message : "Delete failed");
                }
              }}
              style={{
                background: "var(--danger-bg)",
                color: "var(--danger-text)",
                border: "none",
                borderRadius: 8,
                padding: "0.4rem 0.65rem",
                fontSize: "0.85rem",
              }}
            >
              Delete
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
