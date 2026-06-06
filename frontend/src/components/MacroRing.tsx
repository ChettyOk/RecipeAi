import { useEffect, useState } from "react";
import type { Nutrition } from "../api";
import { AnimatedNumber } from "./AnimatedNumber";

type Props = {
  consumed: Nutrition;
  targets: Nutrition;
  size?: number;
  stroke?: number;
  /** Play fill animation on mount / when bumped after logging */
  animate?: boolean;
  bump?: boolean;
};

export function MacroRing({ consumed, targets, size = 140, stroke = 10, animate = true, bump }: Props) {
  const [ready, setReady] = useState(!animate);
  const [pulse, setPulse] = useState(false);

  useEffect(() => {
    if (!animate) return;
    const id = requestAnimationFrame(() => setReady(true));
    return () => cancelAnimationFrame(id);
  }, [animate]);

  useEffect(() => {
    if (!bump) return;
    setPulse(true);
    const t = window.setTimeout(() => setPulse(false), 700);
    return () => clearTimeout(t);
  }, [bump]);

  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const calPct = targets.calories ? Math.min((consumed.calories ?? 0) / targets.calories, 1) : 0;
  const displayPct = ready ? calPct : 0;
  const offset = c * (1 - displayPct);

  const slices = [
    { label: "P", value: consumed.protein_g ?? 0, max: targets.protein_g ?? 1, color: "var(--macro-protein)" },
    { label: "C", value: consumed.carbs_g ?? 0, max: targets.carbs_g ?? 1, color: "var(--macro-carbs)" },
    { label: "F", value: consumed.fat_g ?? 0, max: targets.fat_g ?? 1, color: "var(--macro-fat)" },
  ];

  return (
    <div className={`macro-ring ${pulse ? "macro-ring--pulse" : ""}`}>
      <div className="macro-ring__viz" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
          <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--border)" strokeWidth={stroke} />
          <circle
            cx={size / 2}
            cy={size / 2}
            r={r}
            fill="none"
            stroke="var(--accent)"
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={c}
            strokeDashoffset={offset}
            transform={`rotate(-90 ${size / 2} ${size / 2})`}
            className="macro-ring__progress"
          />
        </svg>
        {pulse ? (
          <span className="macro-ring__logged" aria-hidden>
            ✓
          </span>
        ) : null}
        <div className="macro-ring__center">
          <span className="macro-ring__label">today</span>
          <span className="display-num macro-ring__cal">
            <AnimatedNumber value={ready ? consumed.calories : 0} duration={800} />
          </span>
          <span className="macro-ring__sub">/ {targets.calories ?? "—"} kcal</span>
        </div>
      </div>
      <div className="macro-ring__legend" aria-label="Macros consumed today">
        {slices.map((s) => (
          <span key={s.label} className="macro-ring__legend-item" style={{ color: s.color }}>
            <span className="macro-ring__legend-key">{s.label}</span>
            <span className="macro-ring__legend-val">
              <AnimatedNumber value={ready ? s.value : 0} duration={800} suffix="g" />
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
