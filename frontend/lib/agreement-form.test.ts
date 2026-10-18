import { describe, expect, it } from "vitest";

import {
  applyDraftToFormState,
  buildAgreementTerms,
  emptyFormState,
  missingRequiredFields,
  normalizeVendorKey,
} from "./agreement-form";

describe("missingRequiredFields", () => {
  it("flags every required retainer field when blank", () => {
    const state = emptyFormState();
    expect(missingRequiredFields(state)).toEqual(
      expect.arrayContaining(["vendor_name", "valid_from", "amount_min", "amount_max"]),
    );
  });

  it("is empty once a retainer form is complete", () => {
    const state = {
      ...emptyFormState(),
      vendor_name: "Globex LLC",
      valid_from: "2026-01-01",
      amount_min: "800",
      amount_max: "800",
    };
    expect(missingRequiredFields(state)).toEqual([]);
  });

  it("accepts tiered unit_pricing without a flat rate", () => {
    const state = {
      ...emptyFormState(),
      kind: "unit_pricing" as const,
      vendor_name: "Pampaluz Ltda",
      valid_from: "2026-01-01",
      unit: "unidad",
      formulaKind: "tiered" as const,
      tiersText: "100|10\n|8",
    };
    expect(missingRequiredFields(state)).toEqual([]);
  });
});

describe("buildAgreementTerms", () => {
  it("returns null while required fields are missing", () => {
    expect(buildAgreementTerms(emptyFormState())).toBeNull();
  });

  it("builds a retainer with min==max and a cap", () => {
    const state = {
      ...emptyFormState(),
      vendor_name: "Globex LLC",
      valid_from: "2026-01-01",
      valid_to: "2026-12-31",
      amount_min: "800",
      amount_max: "800",
      total_cap: "9600",
    };
    expect(buildAgreementTerms(state)).toEqual({
      vendor_name: "Globex LLC",
      vendor_key: "globex",
      department: null,
      currency: "USD",
      valid_from: "2026-01-01",
      valid_to: "2026-12-31",
      kind: "retainer",
      periodicity: "monthly",
      amount: { min: 800, max: 800 },
      total_cap: 9600,
    });
  });

  it("builds hourly terms with overtime", () => {
    const state = {
      ...emptyFormState(),
      kind: "hourly" as const,
      vendor_name: "Andesbyte SAS",
      valid_from: "2026-01-01",
      rate: "25",
      included_hours: "120",
      overtime_multiplier: "1.5",
      overtime_max_hours: "40",
    };
    const terms = buildAgreementTerms(state);
    expect(terms).toMatchObject({
      kind: "hourly",
      rate: 25,
      included_hours: 120,
      overtime: { multiplier: 1.5, max_hours: 40 },
    });
  });

  it("parses installments lines into items", () => {
    const state = {
      ...emptyFormState(),
      kind: "installments" as const,
      vendor_name: "Luma Austral SA",
      valid_from: "2026-02-01",
      itemsText: "1/2|2026-02-01|2026-02-28|1000\n2/2|2026-03-01|2026-03-31|1000",
    };
    const terms = buildAgreementTerms(state);
    expect(terms).toMatchObject({
      kind: "installments",
      items: [
        { key: "1/2", due_from: "2026-02-01", due_to: "2026-02-28", amount: 1000 },
        { key: "2/2", due_from: "2026-03-01", due_to: "2026-03-31", amount: 1000 },
      ],
    });
  });
});

describe("applyDraftToFormState", () => {
  it("overlays only the fields present in the draft", () => {
    const base = emptyFormState();
    const next = applyDraftToFormState(base, { kind: "retainer", vendor_name: "Globex LLC" });
    expect(next.kind).toBe("retainer");
    expect(next.vendor_name).toBe("Globex LLC");
    expect(next.currency).toBe(base.currency);
  });
});

describe("normalizeVendorKey", () => {
  it("strips accents, case, and common legal suffixes", () => {
    expect(normalizeVendorKey("Globex LLC")).toBe("globex");
    expect(normalizeVendorKey("Andesbyte SAS")).toBe("andesbyte");
    expect(normalizeVendorKey("Luma Austral SA")).toBe("luma austral");
  });
});
