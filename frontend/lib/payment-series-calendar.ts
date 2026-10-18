import type { DecisionRecord } from "@/lib/decision-types";

/**
 * Mirrors `backend/app/rules/payment_series.py` (T7.2, D059) — pure period-key
 * and expected-period formulas only, ported read-only for display. This file
 * never decides PAGAR/ESCALAR/FRENAR; it only groups decisions the API has
 * already returned onto the calendar periods their own `due_date` falls in
 * (T7.5 §2: "la UI solo muestra lo que devuelve el API").
 */

export type SeriesPeriodicity =
  | "monthly"
  | "biweekly"
  | "quarterly"
  | "annual"
  | "installments"
  | "milestones";

export interface AmountRange {
  min: number;
  max: number;
}

export interface SeriesItem {
  key: string;
  due_from: string;
  due_to: string;
  amount: number;
}

export interface PaymentSeries {
  id: string;
  beneficiary: string;
  department?: string | null;
  periodicity: SeriesPeriodicity;
  currency: string;
  expected_amount?: AmountRange | null;
  start?: string | null;
  end?: string | null;
  total_cap?: number | null;
  items: SeriesItem[];
}

const CALENDAR_PERIODICITIES = new Set<SeriesPeriodicity>([
  "monthly",
  "biweekly",
  "quarterly",
  "annual",
]);
const MAX_PERIODS = 240;

function parseIsoDate(value: string): Date {
  return new Date(`${value}T00:00:00Z`);
}

function daysBetween(start: Date, end: Date): number {
  return Math.floor((end.getTime() - start.getTime()) / 86_400_000);
}

/** `null` means "cannot be determined" (fail-closed), same as the backend. */
export function periodKey(series: PaymentSeries, dueDateIso: string): string | null {
  const due = parseIsoDate(dueDateIso);
  if (series.periodicity === "monthly") {
    return `${due.getUTCFullYear()}-${String(due.getUTCMonth() + 1).padStart(2, "0")}`;
  }
  if (series.periodicity === "quarterly") {
    const quarter = Math.floor(due.getUTCMonth() / 3) + 1;
    return `${due.getUTCFullYear()}-Q${quarter}`;
  }
  if (series.periodicity === "annual") {
    return `${due.getUTCFullYear()}`;
  }
  if (series.periodicity === "biweekly") {
    if (!series.start) return null;
    const start = parseIsoDate(series.start);
    if (due.getTime() < start.getTime()) return null;
    return `B${Math.floor(daysBetween(start, due) / 14)}`;
  }
  const matches = series.items.filter((item) => {
    const from = parseIsoDate(item.due_from);
    const to = parseIsoDate(item.due_to);
    return from.getTime() <= due.getTime() && due.getTime() <= to.getTime();
  });
  return matches.length === 1 ? matches[0].key : null;
}

/** Ordered calendar period keys from `series.start` through `throughIso` (inclusive). */
export function expectedPeriods(series: PaymentSeries, throughIso: string): string[] {
  if (series.periodicity === "installments" || series.periodicity === "milestones") {
    return series.items.map((item) => item.key);
  }
  if (!series.start) return [];
  const start = parseIsoDate(series.start);
  const through = parseIsoDate(throughIso);
  const end = series.end ? parseIsoDate(series.end) : null;
  const last = end && end.getTime() < through.getTime() ? end : through;
  if (last.getTime() < start.getTime()) return [];

  const keys: string[] = [];
  if (series.periodicity === "monthly") {
    let year = start.getUTCFullYear();
    let month = start.getUTCMonth();
    const lastYear = last.getUTCFullYear();
    const lastMonth = last.getUTCMonth();
    while ((year < lastYear || (year === lastYear && month <= lastMonth)) && keys.length < MAX_PERIODS) {
      keys.push(`${year}-${String(month + 1).padStart(2, "0")}`);
      month += 1;
      if (month > 11) {
        month = 0;
        year += 1;
      }
    }
    return keys;
  }
  if (series.periodicity === "quarterly") {
    let year = start.getUTCFullYear();
    let quarter = Math.floor(start.getUTCMonth() / 3) + 1;
    const lastYear = last.getUTCFullYear();
    const lastQuarter = Math.floor(last.getUTCMonth() / 3) + 1;
    while ((year < lastYear || (year === lastYear && quarter <= lastQuarter)) && keys.length < MAX_PERIODS) {
      keys.push(`${year}-Q${quarter}`);
      quarter += 1;
      if (quarter > 4) {
        quarter = 1;
        year += 1;
      }
    }
    return keys;
  }
  if (series.periodicity === "annual") {
    let year = start.getUTCFullYear();
    const lastYear = last.getUTCFullYear();
    while (year <= lastYear && keys.length < MAX_PERIODS) {
      keys.push(`${year}`);
      year += 1;
    }
    return keys;
  }
  // biweekly
  const lastIndex = Math.floor(daysBetween(start, last) / 14);
  for (let i = 0; i <= lastIndex && keys.length < MAX_PERIODS; i += 1) {
    keys.push(`B${i}`);
  }
  return keys;
}

export type PeriodState = "pagado" | "pendiente" | "frenado" | "sin_factura";

export const PERIOD_STATE_LABELS: Record<PeriodState, string> = {
  pagado: "Pagado",
  pendiente: "Pendiente de aprobación",
  frenado: "Frenado",
  sin_factura: "Sin factura",
};

export interface CalendarPeriod {
  period: string;
  state: PeriodState;
  decisionId?: string;
  invoiceNumber?: string | null;
  amountBase?: number | null;
}

export interface VendorSeriesCalendar {
  seriesId: string;
  currency: string;
  periods: CalendarPeriod[];
  totalPaid: number;
  totalCap: number | null;
}

/** A decision counts as "paid" once it reached PAGAR, or an escalation was approved by a human. */
function isCountedPaid(record: DecisionRecord): boolean {
  return (
    record.decision === "PAGAR" || record.human_events.some((event) => event.action === "aprobada_humano")
  );
}

/**
 * Groups already-decided records (from `GET /decisions`) onto this series'
 * calendar periods. Presentational only: every state comes from fields the
 * API already returned (`decision`, `human_events`), never computed anew.
 */
export function buildVendorCalendar(
  series: PaymentSeries,
  decisions: DecisionRecord[],
  todayIso: string,
): VendorSeriesCalendar {
  const byPeriod = new Map<string, DecisionRecord[]>();
  for (const record of decisions) {
    const due = record.extracted.due_date;
    if (!due) continue;
    const key = periodKey(series, due);
    if (!key) continue;
    const list = byPeriod.get(key) ?? [];
    list.push(record);
    byPeriod.set(key, list);
  }

  const through =
    series.end && parseIsoDate(series.end).getTime() < parseIsoDate(todayIso).getTime() ? series.end : todayIso;
  const expected = expectedPeriods(series, through);

  let totalPaid = 0;
  const periods: CalendarPeriod[] = expected.map((key) => {
    const records = byPeriod.get(key) ?? [];
    if (records.length === 0) {
      return { period: key, state: "sin_factura" };
    }
    const paid = records.find(isCountedPaid);
    if (paid) {
      totalPaid += paid.extracted.amount_base ?? 0;
      return {
        period: key,
        state: "pagado",
        decisionId: paid.id,
        invoiceNumber: paid.extracted.invoice_number ?? null,
        amountBase: paid.extracted.amount_base ?? null,
      };
    }
    const held = records.find((record) => record.decision === "FRENAR");
    if (held) {
      return {
        period: key,
        state: "frenado",
        decisionId: held.id,
        invoiceNumber: held.extracted.invoice_number ?? null,
        amountBase: held.extracted.amount_base ?? null,
      };
    }
    const pending = records[0];
    return {
      period: key,
      state: "pendiente",
      decisionId: pending.id,
      invoiceNumber: pending.extracted.invoice_number ?? null,
      amountBase: pending.extracted.amount_base ?? null,
    };
  });

  return { seriesId: series.id, currency: series.currency, periods, totalPaid, totalCap: series.total_cap ?? null };
}

/** Finds the (at most one, by product rule) series declared for this exact vendor name. */
export function seriesForVendor(allSeries: PaymentSeries[], vendorName: string): PaymentSeries | null {
  return allSeries.find((series) => series.beneficiary === vendorName) ?? null;
}

export function isCalendarPeriodicity(periodicity: SeriesPeriodicity): boolean {
  return CALENDAR_PERIODICITIES.has(periodicity);
}
