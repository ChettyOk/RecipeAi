import type { Nutrition } from "../api";
import { MacroPills } from "./MacroPills";

type Props = {
  calories: number | null;
  nutrition: Nutrition;
  subtitle?: string;
  animate?: boolean;
};

export function MacroHero({ calories, nutrition, subtitle, animate }: Props) {
  return (
    <div className={`macro-hero ${animate ? "macro-hero--animate" : ""}`}>
      <p className="macro-hero__eyebrow">{subtitle ?? "per serving"}</p>
      <p className="display-num macro-hero__cal">{calories != null ? Math.round(calories) : "—"}</p>
      <p className="macro-hero__unit">calories</p>
      <MacroPills nutrition={nutrition} />
    </div>
  );
}
