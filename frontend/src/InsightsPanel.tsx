import { Link } from "react-router-dom";
import type { RecipeInsights } from "./api";

function Bar({ label, pct }: { label: string; pct: number | null }) {
  if (pct == null) return null;
  const clamped = Math.max(0, Math.min(pct, 100));
  const over = pct > 100;
  return (
    <div style={{ display: "grid", gap: "0.2rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.8rem", color: "var(--text-muted)" }}>
        <span>{label}</span>
        <span>{pct}% of daily target</span>
      </div>
      <div style={{ height: 8, borderRadius: 999, background: "var(--bg-page)", border: "1px solid var(--border)", overflow: "hidden" }}>
        <div
          style={{
            width: `${clamped}%`,
            height: "100%",
            background: over ? "var(--danger-text)" : "var(--accent)",
          }}
        />
      </div>
    </div>
  );
}

export function InsightsPanel({ insights }: { insights: RecipeInsights }) {
  return (
    <div style={{ display: "grid", gap: "0.8rem" }}>
      <strong style={{ color: "var(--text)" }}>Personalized insights</strong>

      {!insights.has_profile ? (
        <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)" }}>
          <Link to="/profile" style={{ color: "var(--link)" }}>Set up your profile</Link> (height, weight, goal,
          allergies) to see how this fits your day and get tailored swaps.
        </p>
      ) : null}

      {insights.calories_pct_of_target != null || insights.protein_pct_of_target != null ? (
        <div style={{ display: "grid", gap: "0.5rem" }}>
          <Bar label="Calories / serving" pct={insights.calories_pct_of_target} />
          <Bar label="Protein / serving" pct={insights.protein_pct_of_target} />
        </div>
      ) : null}

      {insights.allergy_warnings.length > 0 ? (
        <div style={{ background: "var(--danger-soft-bg)", color: "var(--danger-soft-text)", border: "1px solid var(--border)", borderRadius: 8, padding: "0.6rem 0.8rem" }}>
          <strong style={{ display: "block", marginBottom: "0.25rem" }}>⚠ Allergy warnings</strong>
          <ul style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.85rem" }}>
            {insights.allergy_warnings.map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        </div>
      ) : null}

      {insights.dietary_conflicts.length > 0 ? (
        <ul style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
          {insights.dietary_conflicts.map((w, i) => <li key={i}>{w}</li>)}
        </ul>
      ) : null}

      {insights.fit_notes.length > 0 ? (
        <ul style={{ margin: 0, paddingLeft: "1.1rem", fontSize: "0.85rem", color: "var(--text)" }}>
          {insights.fit_notes.map((n, i) => <li key={i}>{n}</li>)}
        </ul>
      ) : null}

      {insights.substitutions.length > 0 ? (
        <div style={{ display: "grid", gap: "0.4rem" }}>
          <strong style={{ color: "var(--text)", fontSize: "0.9rem" }}>Healthier swaps</strong>
          <ul style={{ margin: 0, paddingLeft: "1.1rem", display: "grid", gap: "0.3rem", fontSize: "0.85rem" }}>
            {insights.substitutions.map((s, i) => (
              <li key={i}>
                Swap <strong>{s.ingredient}</strong> → <span style={{ color: "var(--link)" }}>{s.suggestion}</span>
                <span style={{ color: "var(--text-muted)" }}> — {s.reason}</span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {insights.has_profile &&
      insights.substitutions.length === 0 &&
      insights.allergy_warnings.length === 0 &&
      insights.fit_notes.length === 0 ? (
        <p style={{ margin: 0, fontSize: "0.85rem", color: "var(--text-muted)" }}>
          Looks good — no flags or swaps for your goals.
        </p>
      ) : null}
    </div>
  );
}
