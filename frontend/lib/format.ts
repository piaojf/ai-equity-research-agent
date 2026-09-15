export function money(value: number | null | undefined, currency = "USD") {
  if (value == null) return "—";
  return new Intl.NumberFormat("zh-CN", { style: "currency", currency, maximumFractionDigits: 2 }).format(value);
}

export function number(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : new Intl.NumberFormat("zh-CN", { maximumFractionDigits: digits }).format(value);
}

export function percent(value: number | null | undefined, digits = 1) {
  return value == null ? "—" : `${value >= 0 ? "+" : ""}${value.toFixed(digits)}%`;
}

export function date(value?: string) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("zh-CN", { month: "long", day: "numeric", year: "numeric" }).format(new Date(value));
}

export function titleCase(value: string) { return value.replace(/_/g, " ").replace(/\b\w/g, (letter) => letter.toUpperCase()); }
