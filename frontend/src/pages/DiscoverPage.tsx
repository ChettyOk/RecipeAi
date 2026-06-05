import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { Recipe } from "../api";
import * as api from "../api";
import { RecipeThumb } from "../components/RecipeThumb";

const FILTERS = [
  { id: "all", label: "All" },
  { id: "high-protein", label: "High protein" },
  { id: "low-carb", label: "Low carb" },
  { id: "under500", label: "Under 500 cal" },
  { id: "quick", label: "Quick (<30 min)" },
] as const;

function match(r: Recipe, id: string): boolean {
  if (id === "all") return true;
  const cal = r.nutrition?.per_serving?.calories;
  const prot = r.nutrition?.per_serving?.protein_g;
  const flags = r.dietary_flags ?? [];
  const mins = (r.prep_time_min ?? 0) + (r.cook_time_min ?? 0);
  if (id === "high-protein") return (prot != null && prot >= 25) || flags.includes("high-protein");
  if (id === "low-carb") return flags.includes("low-carb") || flags.includes("keto");
  if (id === "under500") return cal != null && cal < 500;
  if (id === "quick") return mins > 0 && mins <= 30;
  return true;
}

export function DiscoverPage() {
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [filter, setFilter] = useState("all");
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setRecipes(await api.fetchRecipes());
    } catch {
      setRecipes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const shown = recipes.filter((r) => {
    if (!match(r, filter)) return false;
    if (!q.trim()) return true;
    return r.title.toLowerCase().includes(q.toLowerCase());
  });

  return (
    <div className="page">
      <h1 className="page-title">Discover</h1>
      <p className="page-sub">Your saved recipes — filter by what fits today.</p>

      <input
        type="search"
        placeholder="Search recipes…"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        style={{ width: "100%", padding: "0.65rem 0.85rem", marginBottom: "0.85rem" }}
      />

      <div className="filter-row">
        {FILTERS.map((f) => (
          <button
            key={f.id}
            type="button"
            className={`chip ${filter === f.id ? "chip--on" : ""}`}
            onClick={() => setFilter(f.id)}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p style={{ color: "var(--text-muted)" }}>Loading…</p>
      ) : shown.length === 0 ? (
        <p className="card" style={{ color: "var(--text-muted)", textAlign: "center" }}>
          No recipes match. Import a TikTok or YouTube video to build your library.
        </p>
      ) : (
        <ul className="recipe-grid">
          {shown.map((r) => (
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
                      ? `${Math.round(r.nutrition.per_serving.calories)} kcal/serv`
                      : "—"}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
