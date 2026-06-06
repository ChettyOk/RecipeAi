import { useEffect, useState } from "react";
import type { DailyLogWeekDay, DailyTargets, Profile } from "../api";
import * as api from "../api";
import { ACTIVITY_LEVELS, ALLERGENS, DIETARY_FLAGS, GOALS, SEXES } from "../api";
import { BodyStatsFields } from "../components/BodyStatsFields";
import { loadTodayLog } from "../lib/dailyLog";
import { resolveBodyStats } from "../lib/bodyMetrics";

const ACTIVITY_LABEL: Record<string, string> = {
  sedentary: "Sedentary",
  light: "Light (1–3 d/wk)",
  moderate: "Moderate (3–5 d/wk)",
  active: "Active (6–7 d/wk)",
  very_active: "Very active",
};

const GOAL_LABEL: Record<string, string> = {
  lose: "Lose weight",
  maintain: "Maintain",
  gain: "Gain / build",
};

export function ProfilePage() {
  const [heightCm, setHeightCm] = useState<number | null>(null);
  const [weightKg, setWeightKg] = useState<number | null>(null);
  const [age, setAge] = useState<number | null>(null);
  const [sex, setSex] = useState<string>("");
  const [activity, setActivity] = useState<string>("");
  const [goal, setGoal] = useState<string>("");
  const [allergies, setAllergies] = useState<string[]>([]);
  const [prefs, setPrefs] = useState<string[]>([]);
  const [targets, setTargets] = useState<DailyTargets | null>(null);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [mealsLogged, setMealsLogged] = useState(0);
  const [week, setWeek] = useState<DailyLogWeekDay[]>([]);

  useEffect(() => {
    let cancelled = false;
    void Promise.all([api.getProfile(), loadTodayLog(), api.fetchDailyLogWeek(7)])
      .then(([p, log, w]) => {
        if (cancelled) return;
        setHeightCm(p.height_cm);
        setWeightKg(p.weight_kg);
        setAge(p.age);
        setSex(p.sex ?? "");
        setActivity(p.activity_level ?? "");
        setGoal(p.goal ?? "");
        setAllergies(p.allergies ?? []);
        setPrefs(p.dietary_prefs ?? []);
        setTargets(p.targets);
        setMealsLogged(log.entries.length);
        setWeek(w);
      })
      .catch((e) => !cancelled && setError(e instanceof Error ? e.message : "Failed to load profile"))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, []);

  function toggle(list: string[], setter: (v: string[]) => void, value: string) {
    setter(list.includes(value) ? list.filter((x) => x !== value) : [...list, value]);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    setSaved(false);
    const stats = resolveBodyStats({ heightCm, weightKg, age });
    const payload: Profile = {
      height_cm: stats.heightCm,
      weight_kg: stats.weightKg,
      age: stats.age,
      sex: sex || null,
      activity_level: activity || null,
      goal: goal || null,
      allergies,
      dietary_prefs: prefs,
    };
    try {
      const res = await api.saveProfile(payload);
      setHeightCm(res.height_cm);
      setWeightKg(res.weight_kg);
      setAge(res.age);
      setSex(res.sex ?? "");
      setActivity(res.activity_level ?? "");
      setGoal(res.goal ?? "");
      setAllergies(res.allergies ?? []);
      setPrefs(res.dietary_prefs ?? []);
      setTargets(res.targets);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="page-sub">Loading profile…</p>;

  const maxWeekCal = Math.max(...week.map((d) => d.calories ?? 0), targets?.target_calories ?? 2000, 1);

  return (
    <div className="page">
      <h1 className="page-title">Profile</h1>
      <p className="page-sub">Your progress & targets — settings below.</p>

      <section className="card">
        <p style={{ margin: 0, fontSize: "0.72rem", textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--accent)" }}>
          Today
        </p>
        <p className="display-num" style={{ fontSize: "2.5rem", margin: "0.15rem 0", color: "var(--text)" }}>
          {mealsLogged}
        </p>
        <p style={{ margin: 0, color: "var(--text-muted)", fontSize: "0.88rem" }}>
          meal{mealsLogged === 1 ? "" : "s"} logged today
        </p>
      </section>

      {week.length > 0 ? (
        <section className="card">
          <strong>Last 7 days</strong>
          <div className="week-chart" aria-label="Calories logged per day">
            {week.map((d) => {
              const cal = d.calories ?? 0;
              const h = Math.max(8, Math.round((cal / maxWeekCal) * 100));
              const dayLabel = d.date.slice(5);
              return (
                <div key={d.date} className="week-chart__col" title={`${d.date}: ${cal} kcal`}>
                  <div className="week-chart__bar" style={{ height: `${h}%` }} />
                  <span className="week-chart__lbl">{dayLabel}</span>
                  <span className="week-chart__val">{cal > 0 ? cal : ""}</span>
                </div>
              );
            })}
          </div>
        </section>
      ) : null}

      {targets ? (
        <section className="card">
          <strong>Estimated daily targets</strong>
          {targets.bmi != null ? (
            <p className="page-sub" style={{ marginTop: "0.35rem", marginBottom: "0.65rem" }}>
              BMI {targets.bmi}
              {targets.bmi_category ? ` · ${targets.bmi_category.replace("_", " ")}` : ""}
            </p>
          ) : null}
          <div className="targets-grid">
            <div className="target-card">
              <div className="target-card__value">{targets.target_calories ?? "—"}</div>
              <div className="target-card__label">Calories</div>
            </div>
            <div className="target-card">
              <div className="target-card__value">{targets.protein_g != null ? `${targets.protein_g}g` : "—"}</div>
              <div className="target-card__label">Protein</div>
            </div>
            <div className="target-card">
              <div className="target-card__value">{targets.carbs_g != null ? `${targets.carbs_g}g` : "—"}</div>
              <div className="target-card__label">Carbs</div>
            </div>
            <div className="target-card">
              <div className="target-card__value">{targets.fat_g != null ? `${targets.fat_g}g` : "—"}</div>
              <div className="target-card__label">Fat</div>
            </div>
            <div className="target-card">
              <div className="target-card__value">{targets.tdee ?? "—"}</div>
              <div className="target-card__label">TDEE</div>
            </div>
          </div>
          {targets.basis ? <p className="page-sub" style={{ marginTop: "0.65rem", marginBottom: 0 }}>{targets.basis}</p> : null}
        </section>
      ) : null}

      <form onSubmit={handleSubmit} className="card form-stack">
        {error ? <div className="alert alert--error" role="alert">{error}</div> : null}
        {saved ? <div className="alert alert--success" role="status">Profile saved.</div> : null}

        <BodyStatsFields
          heightCm={heightCm}
          weightKg={weightKg}
          age={age}
          onHeightCm={setHeightCm}
          onWeightKg={setWeightKg}
          onAge={setAge}
        />

        <label className="field">
          <span className="field__label">Sex</span>
          <select className="select" value={sex} onChange={(e) => setSex(e.target.value)}>
            <option value="">—</option>
            {SEXES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>

        <div className="form-grid-2">
          <label className="field">
            <span className="field__label">Activity level</span>
            <select className="select" value={activity} onChange={(e) => setActivity(e.target.value)}>
              <option value="">—</option>
              {ACTIVITY_LEVELS.map((a) => (
                <option key={a} value={a}>{ACTIVITY_LABEL[a]}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span className="field__label">Goal</span>
            <select className="select" value={goal} onChange={(e) => setGoal(e.target.value)}>
              <option value="">—</option>
              {GOALS.map((g) => (
                <option key={g} value={g}>{GOAL_LABEL[g]}</option>
              ))}
            </select>
          </label>
        </div>

        <div className="form-section">
          <span className="field__label">Allergies</span>
          <div className="chip-row">
            {ALLERGENS.map((a) => (
              <button
                key={a}
                type="button"
                className={`chip ${allergies.includes(a) ? "chip--on" : ""}`}
                onClick={() => toggle(allergies, setAllergies, a)}
              >
                {a}
              </button>
            ))}
          </div>
        </div>

        <div className="form-section">
          <span className="field__label">Dietary preferences</span>
          <div className="chip-row">
            {DIETARY_FLAGS.map((d) => (
              <button
                key={d}
                type="button"
                className={`chip ${prefs.includes(d) ? "chip--on" : ""}`}
                onClick={() => toggle(prefs, setPrefs, d)}
              >
                {d}
              </button>
            ))}
          </div>
        </div>

        <button type="submit" disabled={saving} className="btn btn--primary btn--block">
          {saving ? "Saving…" : "Save profile"}
        </button>
      </form>
    </div>
  );
}
