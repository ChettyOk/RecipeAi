import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import type { Recipe, RecipeInsights } from "../api";
import * as api from "../api";
import { CookStepViewer } from "../components/CookStepViewer";
import { DietaryTags } from "../components/DietaryTags";
import { FavoriteButton } from "../components/FavoriteButton";
import { FitDayCard } from "../components/FitDayCard";
import { LogMealModal } from "../components/LogMealModal";
import { MacroHero } from "../components/MacroHero";
import { RecipeThumb } from "../components/RecipeThumb";
import { NutritionPanel } from "../NutritionPanel";
import type { PortionInput } from "../portion";
import { useFavorites } from "../context/FavoritesContext";
import { useShoppingCart } from "../context/ShoppingCartContext";
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
  const [refreshing, setRefreshing] = useState(false);
  const [cartMsg, setCartMsg] = useState<string | null>(null);
  const wakeRef = useRef<{ release: () => Promise<void> } | null>(null);
  const { addRecipe, recipeEntryCount } = useShoppingCart();
  const { removeFavorite } = useFavorites();

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

  async function handleRefreshNutrition() {
    if (!recipe) return;
    setRefreshing(true);
    setErr(null);
    try {
      const updated = await api.refreshRecipeNutrition(recipe.id);
      setRecipe(updated);
      const i = await api.getInsights(updated.ingredients, updated.servings, updated.nutrition);
      setInsights(i);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Refresh failed");
    } finally {
      setRefreshing(false);
    }
  }

  async function handleDelete() {
    if (!recipe || !window.confirm("Remove from cookbook?")) return;
    try {
      await api.deleteRecipe(recipe.id);
      removeFavorite(recipe.id);
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
        recipeId={recipe.id}
        title={recipe.title}
        thumbnailUrl={recipe.thumbnail_url}
        sourceUrl={recipe.source_url}
        sourcePlatform={recipe.source_platform}
        calories={perServing?.calories}
        proteinG={perServing?.protein_g}
      />

      <header style={{ marginBottom: "1rem", marginTop: "1rem" }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "0.75rem" }}>
          <h1 className="page-title" style={{ fontSize: "1.4rem", wordBreak: "break-word", margin: 0, flex: 1 }}>
            {recipe.title}
          </h1>
          <FavoriteButton recipeId={recipe.id} showLabel />
        </div>
        {recipe.servings != null ? (
          <p className="page-sub" style={{ margin: "0.25rem 0 0" }}>Makes {recipe.servings} servings</p>
        ) : null}
        {tags.length ? <DietaryTags tags={tags} /> : null}
      </header>

      {displayNutrition?.calories != null ? (
        <section className="card" style={{ padding: 0, overflow: "hidden", marginBottom: "1rem" }}>
          <MacroHero
            animate
            calories={displayNutrition.calories}
            nutrition={displayNutrition}
            subtitle="per serving"
          />
        </section>
      ) : null}

      {insights ? <FitDayCard insights={insights} /> : null}

      {cartMsg ? (
        <div className="alert alert--success" role="status" style={{ marginBottom: "0.75rem" }}>
          {cartMsg}
        </div>
      ) : null}

      <div className="btn-row" style={{ margin: "1rem 0" }}>
        <button type="button" className="btn btn--secondary" style={{ flex: 1 }} onClick={() => navigate(`/edit/${recipe.id}`)}>
          Edit recipe
        </button>
        <button
          type="button"
          className="btn btn--secondary"
          style={{ flex: 1 }}
          disabled={!recipe.ingredients.length}
          onClick={() => {
            const n = recipeEntryCount(recipe.id);
            addRecipe({ id: recipe.id, title: recipe.title, ingredients: recipe.ingredients });
            setCartMsg(
              n > 0
                ? `Added again (${n + 1}× in cart) — ingredients merged in shopping list.`
                : "Added to shopping list — ingredients merged automatically.",
            );
            window.setTimeout(() => setCartMsg(null), 2800);
          }}
        >
          Add to cart
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
          {recipe.source_url ? (
            <div style={{ marginBottom: "0.75rem" }}>
              <button
                type="button"
                className="btn btn--secondary"
                style={{ width: "100%", fontSize: "0.82rem" }}
                disabled={refreshing}
                onClick={() => void handleRefreshNutrition()}
              >
                {refreshing ? "Refreshing…" : "Refresh macros from video"}
              </button>
            </div>
          ) : null}
          <NutritionPanel nutrition={recipe.nutrition} portion={portion} onPortionChange={setPortion} />
        </section>
      ) : null}

      {tab === "nutrition" && !recipe.nutrition ? (
        <p className="card" style={{ color: "var(--text-muted)" }}>No nutrition data — edit recipe to calculate macros.</p>
      ) : null}

      {tab === "cook" ? (
        <section className="cook-mode">
          <p className="cook-mode__hint">
            Cook mode — screen stays awake. Tap steps as you go.
          </p>
          <CookStepViewer
            steps={recipe.steps}
            doneSteps={doneSteps}
            onToggleStep={(i) => {
              setDoneSteps((prev) => {
                const next = new Set(prev);
                if (next.has(i)) next.delete(i);
                else next.add(i);
                return next;
              });
            }}
          />
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
          onLogged={() => navigate("/home", { state: { mealLogged: true } })}
        />
      ) : null}
    </article>
  );
}
