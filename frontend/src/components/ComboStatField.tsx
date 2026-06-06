export type ComboStatItem = {
  value: number;
  label: string;
};

type Props = {
  label: string;
  value: number;
  onChange: (value: number) => void;
  items: ComboStatItem[];
  unit: string;
  "aria-label": string;
};

function nearestInList(n: number, items: ComboStatItem[]): number {
  if (items.length === 0) return n;
  return items.reduce(
    (best, item) => (Math.abs(item.value - n) < Math.abs(best - n) ? item.value : best),
    items[0].value,
  );
}

export function ComboStatField({
  label,
  value,
  onChange,
  items,
  unit,
  "aria-label": ariaLabel,
}: Props) {
  return (
    <label className="field combo-stat">
      <span className="field__label">{label}</span>
      <select
        className="select"
        value={nearestInList(value, items)}
        aria-label={ariaLabel}
        onChange={(e) => {
          const n = parseFloat(e.target.value);
          if (Number.isFinite(n)) onChange(n);
        }}
      >
        {items.map((item) => (
          <option key={item.value} value={item.value}>
            {item.label} {unit}
          </option>
        ))}
      </select>
    </label>
  );
}
