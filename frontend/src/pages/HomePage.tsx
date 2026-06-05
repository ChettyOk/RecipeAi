import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import type { DailyTargets, Recipe } from "../api";
import * as api from "../api";
import { MacroRing } from "../components/MacroRing";
import { RecipeThumb } from "../components/RecipeThumb";
import { getDailyLog, sumLoggedToday } from "../lib/storage";

const FILTERS = ["All", "High protein", "Low carb", "Under 500 cal", "Quick"] as const;

function matchesFilter(r: Recipe, filter: string): boolean {
  if (filter === "All") return true;
  const cal = r.nutrition?.per_serving?.calories;
  const prot = r.nutrition?.per_serving?.protein_g;
  const flags = r.dietary_flags ?? [];
  const mins = (r.prep_time_min ?? 0) + (r.cook_time_min ?? 0);
  if (filter === "High protein") return (prot != null && prot >= 25) || flags.includes("high-protein");
  if (filter === "Low carb") return flags.includes("low-carb") || flags.includes("keto");
  if (filter === "Under 500 cal") return cal != null && cal < 500;
  if (filter === "Quick") return mins > 0 && mins <= 30;
  return true;
}

export function HomePage() {
  const navigate = useNavigate();
  const [recipes, setRecipes] = useState<Recipe[]>([]);
  const [targets, setTargets] = useState<DailyTargets | null>(null);
  const [filter, setFilter] = useState<string>("All");
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, profile] = await Promise.all([api.fetchRecipes(), api.getProfile()]);
      setRecipes(list.slice(0, 12));
      setTargets(profile.targets);
    } catch {
      setRecipes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const consumed = sumLoggedToday();
  const targetCal = targets?.target_calories ?? 2000;
  const remaining = Math.max(0, targetCal - (consumed.calories ?? 0));
  const filtered = recipes.filter((r) => matchesFilter(r, filter));

  return (
    <div className="page">
      <header style={{ marginBottom: "1.25rem" }}>
        <h1 className="page-title">Today</h1>
        <p className="page-sub" style={{ margin: 0 }}>What should you eat?</p>
      </header>

      <section className="remaining-banner" style={{ marginBottom: "1rem" }}>
        <p className="remaining-banner__lbl">Calories remaining</p>
        <p className="display-num remaining-banner__num">{remaining}</p>
        <button type="button" className="btn btn--primary" style={{ marginTop: "0.75rem" }} onClick={() => navigate("/import")}>
          + Log a meal
        </button>
      </section>

      {targets ? (
        <section className="card" style={{ marginBottom: "1rem", textAlign: "center" }}>
          <MacroRing
            consumed={consumed}
            targets={{
              calories: targets.target_calories,
              protein_g: targets.protein_g,
              carbs_g: targets.carbs_g,
              fat_g: targets.fat_g,
              fiber_g: 0,
            }}
          />
          <p style={{ margin: "0.5rem 0 0", fontSize: "0.8rem", color: "var(--text-muted)" }}>
            {getDailyLog().entries.length} meal(s) logged today
          </p>
        </section>
      ) : (
        <p className="card" style={{ fontSize: "0.88rem", color: "var(--text-muted)" }}>
          <Link to="/profile">Set up your profile</Link> to see daily macro rings and remaining calories.
        </p>
      )}

      <h2 style={{ fontSize: "1rem", margin: "0 0 0.65rem", fontWeight: 700 }}>Recent recipes</h2>
      <div className="filter-row">
        {FILTERS.map((f) => (
          <button key={f} type="button" className={`chip ${filter === f ? "chip--on" : ""}`} onClick={() => setFilter(f)}>
            {f}
          </button>
        ))}
      </div>

      {loading ? (
        <p style={{ color: "var(--text-muted)" }}>Loading…</p>
      ) : filtered.length === 0 ? (
        <section className="card" style={{ textAlign: "center", padding: "2rem 1rem" }}>
          <p style={{ margin: "0 0 1rem", color: "var(--text-muted)" }}>Import a TikTok or YouTube cooking video to get started.</p>
          <div className="btn-row" style={{ justifyContent: "center" }}>
            <button type="button" className="btn btn--primary" onClick={() => navigate("/import")}>
              Import video
            </button>
            <button type="button" className="btn btn--secondary" onClick={() => navigate("/new")}>
              Add manually
            </button>
          </div>
        </section>
      ) : (
        <ul className="recipe-grid">
          {filtered.map((r) => (
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
                      : "— kcal"}
                  </p>
                  {r.nutrition?.per_serving?.protein_g != null && r.nutrition.per_serving.protein_g >= 20 ? (
                    <span className="recipe-card__badge">{Math.round(r.nutrition.per_serving.protein_g)}g protein</span>
                  ) : null}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
