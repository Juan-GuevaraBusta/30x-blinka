import { describe, expect, it } from "vitest";

import { describeAgreement } from "./agreement-present";
import type { HourlyAgreement, InstallmentsAgreement, RetainerAgreement } from "./agreement-types";

const RETAINER: RetainerAgreement = {
  kind: "retainer",
  vendor_name: "Globex LLC",
  vendor_key: "globex",
  currency: "USD",
  periodicity: "monthly",
  amount: { min: 800, max: 800 },
  valid_from: "2026-01-01",
  valid_to: "2026-12-31",
  total_cap: 9600,
};

describe("describeAgreement", () => {
  it("summarizes a fixed-amount monthly retainer in Spanish", () => {
    expect(describeAgreement(RETAINER)).toBe(
      "Mensual, USD 800, de 2026-01-01 a 2026-12-31, tope USD 9.600",
    );
  });

  it("summarizes an hourly agreement with overtime", () => {
    const hourly: HourlyAgreement = {
      kind: "hourly",
      vendor_name: "Andesbyte SAS",
      vendor_key: "andesbyte",
      currency: "USD",
      unit: "hora",
      rate: 25,
      included_hours: 120,
      overtime: { multiplier: 1.5, max_hours: 40 },
      valid_from: "2026-01-01",
      valid_to: null,
    };
    expect(describeAgreement(hourly)).toContain("Por hora, USD 25");
    expect(describeAgreement(hourly)).toContain("120 h incluidas");
    expect(describeAgreement(hourly)).toContain("extras ×1.5 hasta 40 h");
    expect(describeAgreement(hourly)).toContain("sin fin");
  });

  it("summarizes equal installments", () => {
    const installments: InstallmentsAgreement = {
      kind: "installments",
      vendor_name: "Luma Austral SA",
      vendor_key: "luma austral",
      currency: "USD",
      valid_from: "2026-02-01",
      valid_to: null,
      items: [
        { key: "1/2", due_from: "2026-02-01", due_to: "2026-02-28", amount: 1000 },
        { key: "2/2", due_from: "2026-03-01", due_to: "2026-03-31", amount: 1000 },
      ],
    };
    expect(describeAgreement(installments)).toBe(
      "Cuotas: 2 de USD 1.000, de 2026-02-01 a sin fin",
    );
  });
});
