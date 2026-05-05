const usd = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" });
const dateShort = new Intl.DateTimeFormat("en-US", { dateStyle: "medium" });
const dateTime = new Intl.DateTimeFormat("en-US", { dateStyle: "medium", timeStyle: "short" });

export function money(n: number): string {
  return usd.format(n);
}

export function fmtDate(s: string | Date): string {
  return dateShort.format(typeof s === "string" ? new Date(s) : s);
}

export function fmtDateTime(s: string | Date): string {
  return dateTime.format(typeof s === "string" ? new Date(s) : s);
}

export function daysUntil(s: string | Date): number {
  const target = typeof s === "string" ? new Date(s) : s;
  return Math.ceil((target.getTime() - Date.now()) / 86_400_000);
}
