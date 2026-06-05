import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { Recipe } from "../api";
import * as api from "../api";
import { RecipeThumb } from "../components/RecipeThumb";

export function CookbookPage() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const load = useCallback(async () => {
    setError(null);
    setLoading(true);
    try {
      setRecipes(await api.fetchRecipes());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading cookbook…</p>;

  if (error) {
    return (
      <div className="card" role="alert" style={{ color: "var(--danger-soft-text)" }}>
        {error} — is the backend running?
      </div>
    );
  }

  if (recipes.length === 0) {
    return (
      <section className="card" style={{ textAlign: "center", padding: "2.5rem 1.25rem" }}>
        <p style={{ fontSize: "2.5rem", margin: "0 0 0.5rem" }}>📓</p>
        <h2 className="page-title" style={{ fontSize: "1.35rem" }}>Cookbook is empty</h2>
        <p className="page-sub">Save recipes from TikTok or YouTube to cook them later.</p>
        <div className="btn-row" style={{ justifyContent: "center" }}>
          <button type="button" className="btn btn--primary" onClick={() => navigate("/import")}>
            Import a video
          </button>
          <button type="button" className="btn btn--secondary" onClick={() => navigate("/new")}>
            Add manually
          </button>
        </div>
      </section>
    );
  }

  return (
    <div className="page">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem", gap: "0.5rem" }}>
        <h1 className="page-title" style={{ margin: 0 }}>Cookbook</h1>
        <div className="btn-row" style={{ margin: 0, flexShrink: 0 }}>
          <button type="button" className="btn btn--ghost" style={{ padding: "0.4rem 0.65rem", fontSize: "0.78rem" }} onClick={() => navigate("/new")}>
            + Manual
          </button>
          <button type="button" className="btn btn--secondary" style={{ padding: "0.4rem 0.65rem", fontSize: "0.78rem" }} onClick={() => navigate("/import")}>
            Import
          </button>
        </div>
      </div>
      <p style={{ margin: "0 0 0.5rem", color: "var(--text-muted)", fontSize: "0.85rem" }}>{recipes.length} saved</p>
      <p className="page-sub">Saved for later — no impact on today's log until you log a meal.</p>

      <ul className="recipe-grid">
        {recipes.map((r) => (
          <li key={r.id}>
            <Link to={`/recipe/${r.id}`} className="recipe-card">
              <RecipeThumb
                title={r.title}
                thumbnailUrl={r.thumbnail_url}
                sourceUrl={r.source_url}
                sourcePlatform={r.source_platform}
                calories={r.nutrition?.per_serving?.calories}
                proteinG={r.nutrition?.per_serving?.protein_g}
              />
              <div className="recipe-card__body">
                <p className="recipe-card__title">{r.title}</p>
                <p className="recipe-card__meta">
                  {r.nutrition?.per_serving?.calories != null
                    ? `${Math.round(r.nutrition.per_serving.calories)} kcal`
                    : "—"}
                </p>
                {r.nutrition?.per_serving?.protein_g != null && r.nutrition.per_serving.protein_g >= 15 ? (
                  <span className="recipe-card__badge">{Math.round(r.nutrition.per_serving.protein_g)}g protein</span>
                ) : null}
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
