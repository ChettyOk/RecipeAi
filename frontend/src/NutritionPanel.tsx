import type { Nutrition, NutritionReport } from "./api";
import {
  PORTION_UNITS,
  type PortionInput,
  formatPortionLabel,
  portionNutrition,
  unitLabel,
} from "./portion";

function fmt(n: number | null, suffix = ""): string {
  if (n == null) return "—";
  return `${Math.round(n * 10) / 10}${suffix}`;
}

function fmtCal(n: number | null): string {
  if (n == null) return "—";
  return `${Math.round(n)} kcal`;
}

export function MacroGrid({ nutrition }: { nutrition: Nutrition }) {
  const items: [string, string][] = [
    ["Calories", fmt(nutrition.calories)],
    ["Protein", fmt(nutrition.protein_g, " g")],
    ["Carbs", fmt(nutrition.carbs_g, " g")],
    ["Fat", fmt(nutrition.fat_g, " g")],
    ["Fiber", fmt(nutrition.fiber_g, " g")],
  ];
  return (
    <div className="macro-grid">
      {items.map(([label, value]) => (
        <div key={label} className="macro-grid__cell">
          <div style={{ fontSize: "1.05rem", fontWeight: 700, color: "var(--text)" }}>{value}</div>
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

  return (
    <div className="nutrition-panel">
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
            {formatPortionLabel(portion, nutrition)} → {fmtCal(scaled.calories)}
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
            <MacroGrid nutrition={scaled} />
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
      {nutrition.source?.includes("Creator caption") ? (
        <p style={{ margin: 0, fontSize: "0.72rem", color: "var(--success-text)" }}>
          ✓ Fixed values from the video caption — recalculate will not change these numbers.
        </p>
      ) : nutrition.source?.includes("Gemini") ? (
        <p style={{ margin: 0, fontSize: "0.72rem", color: "var(--danger-soft-text)" }}>
          AI estimate only — re-import the video for exact caption macros.
        </p>
      ) : nutrition.source ? (
        <p style={{ margin: 0, fontSize: "0.72rem", color: "var(--text-muted)" }}>
          Source: {nutrition.source}.
        </p>
      ) : null}
    </div>
  );
}
