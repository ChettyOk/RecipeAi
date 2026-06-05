import type { Nutrition } from "../api";

type RingSlice = { label: string; value: number; color: string; max: number };

type Props = {
  consumed: Nutrition;
  targets: Nutrition;
  size?: number;
  stroke?: number;
};

export function MacroRing({ consumed, targets, size = 140, stroke = 10 }: Props) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const calPct = targets.calories ? Math.min((consumed.calories ?? 0) / targets.calories, 1) : 0;
  const offset = c * (1 - calPct);

  const slices: RingSlice[] = [
    { label: "P", value: consumed.protein_g ?? 0, max: targets.protein_g ?? 1, color: "var(--macro-protein)" },
    { label: "C", value: consumed.carbs_g ?? 0, max: targets.carbs_g ?? 1, color: "var(--macro-carbs)" },
    { label: "F", value: consumed.fat_g ?? 0, max: targets.fat_g ?? 1, color: "var(--macro-fat)" },
  ];

  return (
    <div className="macro-ring" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
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
      <div className="macro-ring__center">
        <span className="macro-ring__label">today</span>
        <span className="display-num macro-ring__cal">{consumed.calories ?? 0}</span>
        <span className="macro-ring__sub">/ {targets.calories ?? "—"} kcal</span>
      </div>
      <div className="macro-ring__legend">
        {slices.map((s) => (
          <span key={s.label} style={{ color: s.color }}>
            {s.label} {Math.round(s.value)}g
          </span>
        ))}
      </div>
    </div>
  );
}
