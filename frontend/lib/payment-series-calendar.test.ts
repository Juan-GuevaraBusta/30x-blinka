import { describe, expect, it } from "vitest";
import type { DecisionRecord } from "@/lib/decision-types";
import {
  buildVendorCalendar,
  expectedPeriods,
  periodKey,
  seriesForVendor,
  type PaymentSeries,
} from "./payment-series-calendar";

const globexRetainer: PaymentSeries = {
  id: "globex-retainer",
  beneficiary: "Globex LLC",
  department: "Ingenieria",
  periodicity: "monthly",
  currency: "USD",
  expected_amount: { min: 800, max: 800 },
  start: "2026-01-01",
  end: "2026-12-31",
  total_cap: 9600,
  items: [],
};

const norteclaroCuotas: PaymentSeries = {
  id: "norteclaro-cuotas",
  beneficiary: "Norteclaro SpA",
  periodicity: "installments",
  currency: "USD",
  total_cap: 3000,
  items: [
    { key: "1/3", due_from: "2026-02-01", due_to: "2026-02-28", amount: 1000 },
    { key: "2/3", due_from: "2026-03-01", due_to: "2026-03-31", amount: 1000 },
  ],
};

function record(overrides: Partial<DecisionRecord> & { dueDate?: string }): DecisionRecord {
  const { dueDate, ...rest } = overrides;
  return {
    id: "d1",
    invoice_id: "GX-0312",
    received_at: "2026-03-05T00:00:00Z",
    decision: "PAGAR",
    severity: 0,
    summary: "ok",
    extracted: {
      beneficiary: "Globex LLC",
      amount: 800,
      currency: "USD",
      amount_base: 800,
      due_date: dueDate ?? "2026-03-01",
      invoice_number: "GX-0312",
      department: "Ingenieria",
    },
    checks: [],
    jev_signals: [],
    verifier: { consistent: true, issues: [] },
    admin_notice: null,
    next_step: "",
    trace: {},
    versions: { rules_version: "1", model_extractor: "1", model_verifier: "1", jev: "1" },
    human_events: [],
    ...rest,
  };
}

describe("periodKey", () => {
  it("formats monthly periods as YYYY-MM", () => {
    expect(periodKey(globexRetainer, "2026-03-15")).toBe("2026-03");
  });

  it("formats quarterly periods as YYYY-Qn", () => {
    const quarterly: PaymentSeries = { ...globexRetainer, periodicity: "quarterly" };
    expect(periodKey(quarterly, "2026-04-01")).toBe("2026-Q2");
  });

  it("formats biweekly periods as the 14-day block index from start", () => {
    const biweekly: PaymentSeries = { ...globexRetainer, periodicity: "biweekly", start: "2026-01-01" };
    expect(periodKey(biweekly, "2026-01-01")).toBe("B0");
    expect(periodKey(biweekly, "2026-01-15")).toBe("B1");
  });

  it("formats annual periods as YYYY", () => {
    const annual: PaymentSeries = { ...globexRetainer, periodicity: "annual" };
    expect(periodKey(annual, "2026-06-15")).toBe("2026");
    expect(periodKey(annual, "2027-01-01")).toBe("2027");
  });

  it("resolves the single matching item for installments", () => {
    expect(periodKey(norteclaroCuotas, "2026-02-14")).toBe("1/3");
  });

  it("returns null when no item contains the date (out of series)", () => {
    expect(periodKey(norteclaroCuotas, "2026-05-01")).toBeNull();
  });
});

describe("expectedPeriods", () => {
  it("lists every monthly period from start through the given date", () => {
    expect(expectedPeriods(globexRetainer, "2026-03-01")).toEqual(["2026-01", "2026-02", "2026-03"]);
  });

  it("lists explicit item keys for installments, ignoring the through date", () => {
    expect(expectedPeriods(norteclaroCuotas, "2026-01-01")).toEqual(["1/3", "2/3"]);
  });

  it("lists every annual period from start through the given date", () => {
    const annual: PaymentSeries = { ...globexRetainer, periodicity: "annual", start: "2024-01-01", end: null };
    expect(expectedPeriods(annual, "2026-06-01")).toEqual(["2024", "2025", "2026"]);
  });
});

describe("buildVendorCalendar", () => {
  it("marks a period paid when the matching decision is PAGAR", () => {
    const calendar = buildVendorCalendar(globexRetainer, [record({ dueDate: "2026-01-10" })], "2026-01-31");
    expect(calendar.periods).toEqual([
      { period: "2026-01", state: "pagado", decisionId: "d1", invoiceNumber: "GX-0312", amountBase: 800 },
    ]);
    expect(calendar.totalPaid).toBe(800);
  });

  it("marks an escalated-and-approved period as paid too", () => {
    const escalated = record({
      dueDate: "2026-01-10",
      decision: "ESCALAR",
      severity: 1,
      human_events: [{ author: "cfo@demo.test", at: "2026-01-11T00:00:00Z", action: "aprobada_humano", reason: "ok" }],
    });
    const calendar = buildVendorCalendar(globexRetainer, [escalated], "2026-01-31");
    expect(calendar.periods[0].state).toBe("pagado");
  });

  it("marks a held period as frenado", () => {
    const held = record({ dueDate: "2026-01-10", decision: "FRENAR", severity: 2 });
    const calendar = buildVendorCalendar(globexRetainer, [held], "2026-01-31");
    expect(calendar.periods[0].state).toBe("frenado");
  });

  it("marks a pending escalation without approval as pendiente", () => {
    const pending = record({ dueDate: "2026-01-10", decision: "ESCALAR", severity: 1 });
    const calendar = buildVendorCalendar(globexRetainer, [pending], "2026-01-31");
    expect(calendar.periods[0].state).toBe("pendiente");
  });

  it("marks a period with no matching decision as sin_factura", () => {
    const calendar = buildVendorCalendar(globexRetainer, [], "2026-01-31");
    expect(calendar.periods).toEqual([{ period: "2026-01", state: "sin_factura" }]);
  });
});

describe("seriesForVendor", () => {
  it("finds the series declared for an exact vendor name", () => {
    expect(seriesForVendor([globexRetainer, norteclaroCuotas], "Norteclaro SpA")?.id).toBe("norteclaro-cuotas");
  });

  it("returns null when the vendor has no declared series", () => {
    expect(seriesForVendor([globexRetainer], "Initech SAS")).toBeNull();
  });
});
