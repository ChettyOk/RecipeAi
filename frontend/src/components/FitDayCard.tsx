import { Link } from "react-router-dom";
import type { RecipeInsights } from "../api";

export function FitDayCard({ insights }: { insights: RecipeInsights }) {
  if (!insights.has_profile) {
    return (
      <div className="card fit-day">
        <p className="fit-day__headline">How does this fit your day?</p>
        <p style={{ margin: "0.35rem 0 0", fontSize: "0.88rem", color: "var(--text-muted)" }}>
          <Link to="/profile">Set up your profile</Link> to see calories & protein vs your targets and get swap ideas.
        </p>
      </div>
    );
  }

  const headline =
    insights.fit_notes[0] ??
    (insights.protein_pct_of_target != null
      ? `This covers ${Math.round(insights.protein_pct_of_target)}% of your protein goal per serving.`
      : insights.calories_pct_of_target != null
        ? `This is ${Math.round(insights.calories_pct_of_target)}% of your daily calories per serving.`
        : "Review macros below to see how this fits your plan.");

  return (
    <div className="card fit-day reveal-up">
      <p style={{ margin: 0, fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--accent)" }}>
        Fits your day
      </p>
      <p className="fit-day__headline">{headline}</p>
      {insights.fit_notes.slice(1, 3).map((n, i) => (
        <p key={i} style={{ margin: "0.35rem 0 0", fontSize: "0.85rem", color: "var(--text-muted)" }}>{n}</p>
      ))}
      {insights.substitutions.length > 0 ? (
        <div style={{ marginTop: "0.75rem", paddingTop: "0.75rem", borderTop: "1px solid var(--border)" }}>
          <p style={{ margin: "0 0 0.35rem", fontSize: "0.78rem", fontWeight: 600, color: "var(--text-muted)" }}>
            Smart swaps
          </p>
          {insights.substitutions.slice(0, 2).map((s, i) => (
            <p key={i} style={{ margin: "0.25rem 0", fontSize: "0.85rem" }}>
              <strong>{s.ingredient}</strong> → {s.suggestion}
            </p>
          ))}
        </div>
      ) : null}
    </div>
  );
}
