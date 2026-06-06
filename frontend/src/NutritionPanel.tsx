import type { Nutrition, NutritionReport } from "./api";
import { nutritionSourceLabel, nutritionTrustLevel } from "./lib/nutritionDisplay";
import {
  PORTION_UNITS,
  type PortionInput,
  formatPortionLabel,
  portionNutrition,
  unitLabel,
} from "./portion";

import { AnimatedNumber } from "./components/AnimatedNumber";

function fmt(n: number | null, suffix = ""): string {
  if (n == null) return "—";
  return `${Math.round(n * 10) / 10}${suffix}`;
}

function fmtCal(n: number | null): string {
  if (n == null) return "—";
  return `${Math.round(n)} kcal`;
}

export function MacroGrid({ nutrition, animate }: { nutrition: Nutrition; animate?: boolean }) {
  const items: [string, keyof Nutrition][] = [
    ["Calories", "calories"],
    ["Protein", "protein_g"],
    ["Carbs", "carbs_g"],
    ["Fat", "fat_g"],
    ["Fiber", "fiber_g"],
  ];
  const suffix: Partial<Record<keyof Nutrition, string>> = {
    protein_g: " g",
    carbs_g: " g",
    fat_g: " g",
    fiber_g: " g",
  };
  return (
    <div className="macro-grid">
      {items.map(([label, key]) => (
        <div key={label} className="macro-grid__cell">
          <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text)" }}>
            {animate ? (
              key === "calories" ? (
                <AnimatedNumber value={nutrition.calories} duration={150} />
              ) : (
                <AnimatedNumber
                  value={nutrition[key] as number | null}
                  duration={150}
                  suffix={suffix[key] ?? ""}
                />
              )
            ) : key === "calories" ? (
              fmt(nutrition.calories)
            ) : (
              fmt(nutrition[key] as number | null, suffix[key] ?? "")
            )}
          </div>
          <div style={{ fontSize: "0.7rem", color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 0.4 }}>
            {label}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Macro breakdown with total recipe calories, reference per-serving (from video/calc),
 * and a portion adjuster in g/kg/ml/oz/servings.
 */
export function NutritionPanel({
  nutrition,
  portion,
  onPortionChange,
}: {
  nutrition: NutritionReport;
  portion: PortionInput;
  onPortionChange?: (p: PortionInput) => void;
}) {
  const perServing = nutrition.per_serving;
  const total = nutrition.total;
  const { portion: scaled, warning } = portionNutrition(nutrition, portion);

  const hasTotal = total.calories != null;
  const hasPerServing = perServing.calories != null;
  const hasMacros = hasTotal || hasPerServing || nutrition.matched > 0;
  const srv = nutrition.servings;
  const perWeight = nutrition.per_serving_weight_g;
  const unitWord = unitLabel(nutrition, 1);
  const unitWordPlural = unitLabel(nutrition, 2);
  const sourceLabel = nutritionSourceLabel(nutrition);
  const trust = nutritionTrustLevel(nutrition);
  const unmatched = nutrition.unmatched ?? [];

  return (
    <div className="nutrition-panel">
      {sourceLabel ? (
        <div className={`nutrition-source nutrition-source--${trust}`}>
          <span className="nutrition-source__dot" aria-hidden />
          {sourceLabel}
          {nutrition.matched > 0 && trust !== "high" ? (
            <span className="nutrition-source__meta"> · {nutrition.matched} ingredient(s) matched</span>
          ) : null}
        </div>
      ) : null}

      {unmatched.length > 0 ? (
        <div className="alert alert--warn" role="status">
          <strong>{unmatched.length} ingredient{unmatched.length === 1 ? "" : "s"} not matched</strong>
          <p style={{ margin: "0.35rem 0 0", fontSize: "0.82rem" }}>
            Fix spelling or add weights (e.g. <code>200g chicken</code>) for better macros:{" "}
            {unmatched.slice(0, 4).join(", ")}
            {unmatched.length > 4 ? "…" : ""}
          </p>
        </div>
      ) : null}
      {hasTotal ? (
        <div className="nutrition-total">
          <div>
            <div style={{ fontSize: "0.75rem", opacity: 0.9, textTransform: "uppercase", letterSpacing: 0.5 }}>
              Total recipe
            </div>
            <div style={{ fontSize: "1.75rem", fontWeight: 800, lineHeight: 1.2 }}>{fmtCal(total.calories)}</div>
          </div>
          <div style={{ fontSize: "0.85rem", opacity: 0.95, textAlign: "right" }}>
            {srv != null ? (
              <>
                {srv} {srv === 1 ? unitWord : unitWordPlural}
                {hasPerServing ? ` · ${fmtCal(perServing.calories)}/each` : ""}
              </>
            ) : hasPerServing ? (
              `${fmtCal(perServing.calories)} per ${unitWord}`
            ) : null}
            {perWeight != null ? (
              <div style={{ opacity: 0.85, marginTop: "0.2rem" }}>
                ≈ {Math.round(perWeight)} g per {unitWord}
              </div>
            ) : null}
          </div>
        </div>
      ) : hasPerServing ? (
        <div style={{ background: "var(--accent)", color: "#fff", borderRadius: 12, padding: "1rem 1.1rem" }}>
          <div style={{ fontSize: "0.75rem", opacity: 0.9, textTransform: "uppercase", letterSpacing: 0.5 }}>
            Per {unitWord} (reference)
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: 800 }}>{fmtCal(perServing.calories)}</div>
          {perWeight != null ? (
            <div style={{ fontSize: "0.85rem", opacity: 0.9, marginTop: "0.25rem" }}>
              ≈ {Math.round(perWeight)} g per {unitWord}
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Reference per-serving macros (creator / calculated) */}
      {hasPerServing ? (
        <div style={{ fontSize: "0.82rem", color: "var(--text-muted)" }}>
          Reference per {unitWord}: {fmtCal(perServing.calories)}
          {perServing.protein_g != null ? ` · ${fmt(perServing.protein_g, "g protein")}` : ""}
          {perServing.carbs_g != null ? ` · ${fmt(perServing.carbs_g, "g carbs")}` : ""}
          {perServing.fat_g != null ? ` · ${fmt(perServing.fat_g, "g fat")}` : ""}
        </div>
      ) : null}

      {/* User portion adjuster */}
      <div className="nutrition-portion-box">
        <strong style={{ color: "var(--text)", fontSize: "0.9rem" }}>Your portion</strong>
        {onPortionChange ? (
          <div className="portion-row">
            <input
              className="input portion-input"
              type="number"
              min={0.01}
              step="any"
              value={portion.amount}
              onChange={(e) => {
                const v = parseFloat(e.target.value);
                onPortionChange({
                  ...portion,
                  amount: Number.isFinite(v) && v > 0 ? v : 1,
                });
              }}
              aria-label="Portion amount"
            />
            <select
              className="select portion-select"
              value={portion.unit}
              onChange={(e) =>
                onPortionChange({
                  ...portion,
                  unit: e.target.value as PortionInput["unit"],
                  amount: e.target.value === "serving" ? 1 : portion.amount,
                })
              }
              aria-label="Portion unit"
            >
              {PORTION_UNITS.map((u) => (
                <option key={u.value} value={u.value}>
                  {u.value === "serving"
                    ? nutrition.serving_label
                      ? `1 ${unitWord} (serving)`
                      : u.label
                    : u.label}
                </option>
              ))}
            </select>
          </div>
        ) : null}

        {scaled.calories != null ? (
          <div style={{ fontSize: "1.1rem", fontWeight: 700, color: "var(--text)" }}>
            {formatPortionLabel(portion, nutrition)} →{" "}
            <AnimatedNumber value={scaled.calories} duration={150} suffix=" kcal" />
          </div>
        ) : null}

        {warning ? (
          <p style={{ margin: 0, fontSize: "0.8rem", color: "var(--danger-soft-text)" }}>{warning}</p>
        ) : portion.unit !== "serving" && perWeight != null ? (
          <p style={{ margin: 0, fontSize: "0.75rem", color: "var(--text-muted)" }}>
            Scaled from reference per-{unitWord} ({Math.round(perWeight)} g) using video-stated macros.
          </p>
        ) : null}

        {hasMacros ? (
          <div style={{ display: "grid", gap: "0.35rem" }}>
            <span style={{ fontSize: "0.8rem", color: "var(--text-muted)" }}>Your portion — macros</span>
            <MacroGrid nutrition={scaled} animate />
          </div>
        ) : null}
      </div>

      {!hasMacros ? (
        <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)" }}>
          No calories could be calculated yet — import a video with stated macros or calculate from ingredients.
        </p>
      ) : null}

      {nutrition.notes.length > 0 ? (
        <ul style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.8rem", color: "var(--text-muted)" }}>
          {nutrition.notes.map((n, i) => (
            <li key={i}>{n}</li>
          ))}
        </ul>
      ) : null}
      {trust === "high" ? (
        <p style={{ margin: 0, fontSize: "0.72rem", color: "var(--success-text)" }}>
          Caption macros are stable — recalculate will not change these numbers.
        </p>
      ) : null}
    </div>
  );
}
