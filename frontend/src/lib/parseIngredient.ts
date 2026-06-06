/** Parse free-text ingredient lines (mirrors backend nutrition.parse_ingredient). */

const UNICODE_FRACTIONS: Record<string, number> = {
  "¼": 0.25,
  "½": 0.5,
  "¾": 0.75,
  "⅓": 1 / 3,
  "⅔": 2 / 3,
  "⅛": 0.125,
  "⅜": 0.375,
  "⅝": 0.625,
  "⅞": 0.875,
};

const WEIGHT_UNITS = new Set([
  "g", "gram", "grams", "kg", "kilogram", "oz", "ounce", "ounces", "lb", "lbs", "pound", "pounds",
]);

const VOLUME_UNITS = new Set([
  "ml", "milliliter", "millilitre", "l", "liter", "litre",
  "tsp", "teaspoon", "teaspoons", "tbsp", "tbs", "tablespoon", "tablespoons",
  "cup", "cups", "pint", "quart", "fl", "floz",
]);

const QTY_RE = /^\s*([\d¼½¾⅓⅔⅛⅜⅝⅞./\s-]+)?\s*([a-zA-Z]+)?\.?\s+(.*)$/;
const SIMPLE_QTY_RE = /^\s*([\d¼½¾⅓⅔⅛⅜⅝⅞./\s-]+)\s+(.+)$/;

export type ParsedIngredient = {
  raw: string;
  qty: number | null;
  unit: string | null;
  name: string;
  mergeKey: string;
};

function parseNumber(token: string): number | null {
  const t = token.trim();
  if (!t) return null;
  let total = 0;
  let matched = false;
  let lead = "";
  for (const ch of t) {
    if (ch in UNICODE_FRACTIONS) {
      total += UNICODE_FRACTIONS[ch];
      matched = true;
    } else {
      lead += ch;
    }
  }
  const parts = lead.trim().split(/\s+/).filter(Boolean);
  for (const part of parts) {
    if (part.includes("/")) {
      const [num, den] = part.split("/", 2);
      const n = Number(num);
      const d = Number(den);
      if (!Number.isFinite(n) || !Number.isFinite(d) || d === 0) {
        return matched ? total : null;
      }
      total += n / d;
      matched = true;
      continue;
    }
    const v = Number(part);
    if (!Number.isFinite(v)) return matched ? total : null;
    total += v;
    matched = true;
  }
  return matched ? total : null;
}

export function normalizeIngredientName(name: string): string {
  let s = name.toLowerCase().trim().replace(/^(a|an|the)\s+/, "");
  if (s.endsWith("ies") && s.length > 4) s = `${s.slice(0, -3)}y`;
  else if (s.endsWith("es") && s.length > 4) s = s.slice(0, -2);
  else if (s.endsWith("s") && !s.endsWith("ss") && s.length > 3) s = s.slice(0, -1);
  return s;
}

export function parseIngredientLine(line: string): ParsedIngredient {
  const raw = line.trim();
  let s = raw.replace(/\(.*?\)/g, "").trim();
  s = s.replace(/^[-•*·▪►]\s*/, "");

  const m = QTY_RE.exec(s);
  if (!m) {
    const simple = SIMPLE_QTY_RE.exec(s);
    if (simple) {
      const qty = parseNumber(simple[1]);
      const name = simple[2].trim();
      const norm = normalizeIngredientName(name);
      return { raw, qty, unit: null, name, mergeKey: `${norm}|` };
    }
    const name = s || raw;
    const norm = normalizeIngredientName(name);
    return { raw, qty: null, unit: null, name, mergeKey: `${norm}|` };
  }

  const qtyRaw = m[1] ?? "";
  const unitRaw = m[2] ?? "";
  let rest = (m[3] ?? "").trim();

  const qty = qtyRaw ? parseNumber(qtyRaw) : null;
  let unit: string | null = null;

  if (unitRaw) {
    const u = unitRaw.toLowerCase().replace(/\.$/, "");
    if (WEIGHT_UNITS.has(u) || VOLUME_UNITS.has(u)) {
      unit = u;
    } else {
      rest = `${unitRaw} ${rest}`.trim();
    }
  }

  const name = rest.replace(/^[,.\s-]+|[,.\s-]+$/g, "") || s;
  const norm = normalizeIngredientName(name);
  return { raw, qty, unit, name, mergeKey: `${norm}|${unit ?? ""}` };
}

export function formatQty(qty: number): string {
  if (Math.abs(qty - Math.round(qty)) < 0.05) return String(Math.round(qty));
  const rounded = Math.round(qty * 100) / 100;
  return String(rounded);
}
