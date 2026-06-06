import type { Nutrition } from "../api";
import { AnimatedNumber } from "./AnimatedNumber";

export function MacroPills({ nutrition, animate }: { nutrition: Nutrition; animate?: boolean }) {
  const pills = [
    { label: "Protein", value: nutrition.protein_g, unit: "g", cls: "pill--protein" },
    { label: "Carbs", value: nutrition.carbs_g, unit: "g", cls: "pill--carbs" },
    { label: "Fat", value: nutrition.fat_g, unit: "g", cls: "pill--fat" },
  ];
  return (
    <div className="macro-pills">
      {pills.map((p, i) => (
        <span
          key={p.label}
          className={`macro-pill ${p.cls} ${animate ? "macro-pill--stagger" : ""}`}
          style={animate ? { animationDelay: `${200 + i * 80}ms` } : undefined}
        >
          <span className="display-num macro-pill__val">
            {animate && p.value != null ? (
              <AnimatedNumber value={p.value} duration={800} suffix={p.unit} />
            ) : p.value != null ? (
              `${Math.round(p.value)}${p.unit}`
            ) : (
              "—"
            )}
          </span>
          <span className="macro-pill__lbl">{p.label}</span>
        </span>
      ))}
    </div>
  );
}
