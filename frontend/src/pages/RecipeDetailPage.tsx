import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { Recipe, RecipeInsights } from "../api";
import * as api from "../api";
import { FitDayCard } from "../components/FitDayCard";
import { LogMealModal } from "../components/LogMealModal";
import { MacroHero } from "../components/MacroHero";
import { RecipeThumb } from "../components/RecipeThumb";
import { NutritionPanel } from "../NutritionPanel";
import type { PortionInput } from "../portion";
import { platformOpenLabel } from "../lib/videoUrl";
import { portionNutrition } from "../portion";

type Tab = "nutrition" | "cook" | "original";

export function RecipeDetailPage() {
  const { id } = useParams();
  const recipeId = id ? parseInt(id, 10) : null;
  const navigate = useNavigate();
  const [recipe, setRecipe] = useState<Recipe | null>(null);
  const [insights, setInsights] = useState<RecipeInsights | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>("nutrition");
  const [portion, setPortion] = useState<PortionInput>({ amount: 1, unit: "serving" });
  const [showLog, setShowLog] = useState(false);
  const [doneSteps, setDoneSteps] = useState<Set<number>>(new Set());
  const wakeRef = useRef<{ release: () => Promise<void> } | null>(null);

  useEffect(() => {
    if (recipeId == null) return;
    let cancelled = false;
    setLoading(true);
    setErr(null);
    void api
      .fetchRecipe(recipeId)
      .then((r) => {
        if (cancelled) return;
        setRecipe(r);
        return api
          .getInsights(r.ingredients, r.servings, r.nutrition)
          .then((i) => !cancelled && setInsights(i))
          .catch(() => undefined);
      })
      .catch((e) => !cancelled && setErr(e instanceof Error ? e.message : "Failed to load"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [recipeId]);

  useEffect(() => {
    if (tab !== "cook") {
      void wakeRef.current?.release();
      wakeRef.current = null;
      return;
    }
    if ("wakeLock" in navigator) {
      void navigator.wakeLock.request("screen").then((s) => {
        wakeRef.current = s;
      }).catch(() => undefined);
    }
    return () => {
      void wakeRef.current?.release();
    };
  }, [tab]);

  async function handleDelete() {
    if (!recipe || !window.confirm("Remove from cookbook?")) return;
    try {
      await api.deleteRecipe(recipe.id);
      navigate("/cookbook");
    } catch (e) {
      window.alert(e instanceof Error ? e.message : "Delete failed");
    }
  }

  if (loading) return <p style={{ color: "var(--text-muted)" }}>Loading…</p>;
  if (err) return <div className="card" role="alert" style={{ color: "var(--danger-soft-text)" }}>{err}</div>;
  if (!recipe) return null;

  const perServing = recipe.nutrition?.per_serving;
  const scaled = recipe.nutrition
    ? portionNutrition(recipe.nutrition, portion).portion
    : null;
  const displayNutrition = scaled ?? perServing;

  const tags: string[] = [];
  if (recipe.dietary_flags?.length) tags.push(...recipe.dietary_flags);
  if (perServing?.protein_g != null && perServing.protein_g >= 25) tags.push("high-protein");

  return (
    <article className="page reveal-up">
      <button type="button" className="btn btn--ghost" style={{ marginBottom: "0.75rem", padding: "0.35rem 0.7rem", fontSize: "0.82rem" }} onClick={() => navigate(-1)}>
        ← Back
      </button>

      <RecipeThumb
        variant="hero"
        title={recipe.title}
        thumbnailUrl={recipe.thumbnail_url}
        sourceUrl={recipe.source_url}
        sourcePlatform={recipe.source_platform}
        calories={perServing?.calories}
        proteinG={perServing?.protein_g}
      />

      <header style={{ marginBottom: "1rem", marginTop: "1rem" }}>
        <h1 className="page-title" style={{ fontSize: "1.4rem", wordBreak: "break-word" }}>{recipe.title}</h1>
        {recipe.servings != null ? (
          <p className="page-sub" style={{ margin: "0.25rem 0 0" }}>Makes {recipe.servings} servings</p>
        ) : null}
        {tags.length ? (
          <div style={{ display: "flex", flexWrap: "wrap", gap: "0.35rem", marginTop: "0.5rem" }}>
            {tags.map((t) => (
              <span key={t} className="chip chip--on" style={{ cursor: "default", fontSize: "0.7rem" }}>
                {t.replace(/-/g, " ")}
              </span>
            ))}
          </div>
        ) : null}
      </header>

      {displayNutrition?.calories != null ? (
        <section className="card" style={{ padding: 0, overflow: "hidden", marginBottom: "1rem" }}>
          <MacroHero
            calories={displayNutrition.calories}
            nutrition={displayNutrition}
            subtitle="per serving"
          />
        </section>
      ) : null}

      {insights ? <FitDayCard insights={insights} /> : null}

      <div className="btn-row" style={{ margin: "1rem 0" }}>
        <button type="button" className="btn btn--secondary" style={{ flex: 1 }} onClick={() => navigate(`/edit/${recipe.id}`)}>
          Edit recipe
        </button>
        {recipe.nutrition ? (
          <button type="button" className="btn btn--primary" style={{ flex: 1 }} onClick={() => setShowLog(true)}>
            Log to today
          </button>
        ) : null}
      </div>

      <div className="tabs">
        {(["nutrition", "cook", "original"] as Tab[]).map((t) => (
          <button
            key={t}
            type="button"
            className={`tabs__btn ${tab === t ? "tabs__btn--active" : ""}`}
            onClick={() => setTab(t)}
          >
            {t === "nutrition" ? "Nutrition" : t === "cook" ? "Cook" : "Original"}
          </button>
        ))}
      </div>

      {tab === "nutrition" && recipe.nutrition ? (
        <section className="card">
          <NutritionPanel nutrition={recipe.nutrition} portion={portion} onPortionChange={setPortion} />
        </section>
      ) : null}

      {tab === "nutrition" && !recipe.nutrition ? (
        <p className="card" style={{ color: "var(--text-muted)" }}>No nutrition data — edit recipe to calculate macros.</p>
      ) : null}

      {tab === "cook" ? (
        <section>
          <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "0.75rem" }}>
            Cook mode — screen stays awake. Tap steps as you go.
          </p>
          {recipe.steps.length === 0 ? (
            <p className="card">No steps listed.</p>
          ) : (
            recipe.steps.map((line, i) => (
              <label
                key={i}
                className={`cook-step ${doneSteps.has(i) ? "cook-step--done" : ""}`}
                style={{ cursor: "pointer" }}
              >
                <input
                  type="checkbox"
                  checked={doneSteps.has(i)}
                  onChange={() => {
                    setDoneSteps((prev) => {
                      const next = new Set(prev);
                      if (next.has(i)) next.delete(i);
                      else next.add(i);
                      return next;
                    });
                  }}
                  style={{ marginTop: "0.35rem" }}
                />
                <span className="cook-step__num">{i + 1}</span>
                <p className="cook-step__text">{line}</p>
              </label>
            ))
          )}
          <h3 style={{ fontSize: "0.95rem", color: "var(--text-muted)", marginTop: "1.25rem" }}>Ingredients</h3>
          <ul style={{ paddingLeft: "1.1rem", margin: 0 }}>
            {recipe.ingredients.map((line, i) => (
              <li key={i} style={{ marginBottom: "0.35rem" }}>{line}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {tab === "original" ? (
        <section className="card">
          {recipe.source_url ? (
            <>
              <p style={{ margin: "0 0 0.75rem", fontSize: "0.9rem", color: "var(--text-muted)" }}>
                Re-watch the source video if the AI missed an ingredient.
              </p>
              <a href={recipe.source_url} target="_blank" rel="noreferrer" className="btn btn--primary" style={{ display: "inline-block", textDecoration: "none" }}>
                {platformOpenLabel(recipe.source_platform)}
              </a>
            </>
          ) : (
            <p style={{ color: "var(--text-muted)" }}>No source link saved.</p>
          )}
        </section>
      ) : null}

      <div className="btn-row" style={{ marginTop: "1.5rem" }}>
        <button type="button" className="btn btn--danger" onClick={() => void handleDelete()}>
          Delete
        </button>
      </div>

      {showLog && recipe.nutrition && scaled ? (
        <LogMealModal
          recipe={recipe}
          perServing={scaled}
          onClose={() => setShowLog(false)}
          onLogged={() => navigate("/home")}
        />
      ) : null}
    </article>
  );
}
