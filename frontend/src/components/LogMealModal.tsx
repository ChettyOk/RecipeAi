import { useState } from "react";
import type { Nutrition, Recipe } from "../api";
import { logMealToday } from "../lib/storage";

type Props = {
  recipe: Recipe;
  perServing: Nutrition;
  onClose: () => void;
  onLogged: () => void;
};

export function LogMealModal({ recipe, perServing, onClose, onLogged }: Props) {
  const [servings, setServings] = useState(1);

  function confirm() {
    logMealToday({
      recipeId: recipe.id,
      title: recipe.title,
      servings,
      nutrition: perServing,
    });
    onLogged();
    onClose();
  }

  return (
    <div
      role="dialog"
      aria-modal
      style={{
        position: "fixed",
        inset: 0,
        background: "rgb(0 0 0 / 0.75)",
        display: "flex",
        alignItems: "flex-end",
        justifyContent: "center",
        zIndex: 200,
        padding: "1rem",
      }}
      onClick={onClose}
    >
      <div className="card reveal-up" style={{ width: "100%", maxWidth: 400 }} onClick={(e) => e.stopPropagation()}>
        <h3 style={{ margin: "0 0 0.5rem" }}>Log to today</h3>
        <p style={{ margin: "0 0 1rem", fontSize: "0.88rem", color: "var(--text-muted)" }}>
          How many servings did you eat?
        </p>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "1rem", marginBottom: "1rem" }}>
          <button type="button" className="btn btn--secondary" onClick={() => setServings((s) => Math.max(0.25, s - 0.25))}>−</button>
          <span className="display-num" style={{ fontSize: "2.5rem", minWidth: "3rem", textAlign: "center" }}>
            {servings}
          </span>
          <button type="button" className="btn btn--secondary" onClick={() => setServings((s) => s + 0.25)}>+</button>
        </div>
        <p style={{ textAlign: "center", fontSize: "0.85rem", color: "var(--accent)", marginBottom: "1rem" }}>
          ≈ {Math.round((perServing.calories ?? 0) * servings)} kcal
        </p>
        <div className="btn-row">
          <button type="button" className="btn btn--ghost" style={{ flex: 1 }} onClick={onClose}>Cancel</button>
          <button type="button" className="btn btn--primary" style={{ flex: 1 }} onClick={confirm}>Log meal</button>
        </div>
      </div>
    </div>
  );
}
