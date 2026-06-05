import type { Nutrition } from "../api";

export function MacroPills({ nutrition }: { nutrition: Nutrition }) {
  const pills = [
    { label: "Protein", value: nutrition.protein_g, unit: "g", cls: "pill--protein" },
    { label: "Carbs", value: nutrition.carbs_g, unit: "g", cls: "pill--carbs" },
    { label: "Fat", value: nutrition.fat_g, unit: "g", cls: "pill--fat" },
  ];
  return (
    <div className="macro-pills">
      {pills.map((p) => (
        <span key={p.label} className={`macro-pill ${p.cls}`}>
          <span className="display-num macro-pill__val">
            {p.value != null ? Math.round(p.value) : "—"}
            {p.unit}
          </span>
          <span className="macro-pill__lbl">{p.label}</span>
        </span>
      ))}
    </div>
  );
}
