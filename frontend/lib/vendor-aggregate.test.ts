import { describe, expect, it } from "vitest";

import type { AgreementListEntry } from "./agreement-types";
import type { RulesConfig } from "./rules-types";
import { mergeVendorData, vendorProvenanceLabel, type EffectiveRulesResponse } from "./vendor-aggregate";

function baseRulesConfig(overrides: Partial<RulesConfig> = {}): RulesConfig {
  return {
    company: { name: "Acme", base_currency: "USD" },
    limits: { per_payment: 100000, per_period: { type: "calendar_month", amount: 500000 } },
    human_approval_threshold: 50000,
    allowed_beneficiaries: [],
    department_budgets: {},
    approvers: {},
    manual_blocks: [],
    on_fail: {
      R01: "FRENAR",
      R02: "FRENAR",
      R03: "FRENAR",
      R04: "FRENAR",
      R05: "FRENAR",
      R06: "FRENAR",
      R07: "FRENAR",
      R08: "FRENAR",
      R09: "FRENAR",
      R10: "FRENAR",
      R11: "FRENAR",
      R12: "FRENAR",
      R13: "FRENAR",
    },
    jev_thresholds: { J1: 0, J2: 0, J3: 0, J4: 0, J6: 0, J7: 0 },
    ...overrides,
  };
}

function agreementEntry(overrides: Partial<AgreementListEntry> = {}): AgreementListEntry {
  return {
    vendor_key: "globex",
    vendor_name: "Globex LLC",
    kind: "retainer",
    version: 1,
    status: "active",
    confirmed_by: "cfo@acme.test",
    confirmed_at: "2026-01-01T00:00:00Z",
    valid_from: "2026-01-01",
    valid_to: null,
    ...overrides,
  };
}

describe("mergeVendorData", () => {
  it("returns an empty list for empty input", () => {
    const effective: EffectiveRulesResponse = { rules: baseRulesConfig(), provenance: {} };
    expect(mergeVendorData(effective, [])).toEqual([]);
  });

  it("marks a vendor with no provenance entry as base", () => {
    const effective: EffectiveRulesResponse = {
      rules: baseRulesConfig({ allowed_beneficiaries: ["Acme Supplies SA"] }),
      provenance: {},
    };
    const result = mergeVendorData(effective, []);
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      name: "Acme Supplies SA",
      source: "base",
      agreementVersion: null,
    });
  });

  it("marks a vendor added purely via agreement provenance", () => {
    const effective: EffectiveRulesResponse = {
      rules: baseRulesConfig({ allowed_beneficiaries: ["Globex LLC"] }),
      provenance: {
        "allowed_beneficiaries:globex": "agr-globex-v2",
        "payment_series:globex": "agr-globex-v2",
      },
    };
    const result = mergeVendorData(effective, [agreementEntry({ version: 2 })]);
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      name: "Globex LLC",
      vendorKey: "globex",
      source: "agreement",
      agreementVersion: "agr-globex-v2",
      agreementKind: "retainer",
      hasPaymentSeries: true,
      hasVariablePricing: false,
    });
  });

  it("lets the agreement annotation win when a vendor is present in both base and an agreement", () => {
    const effective: EffectiveRulesResponse = {
      rules: baseRulesConfig({ allowed_beneficiaries: ["Andesbyte SAS"] }),
      provenance: {
        "allowed_beneficiaries:andesbyte": "agr-andesbyte-v3",
        "variable_pricing:andesbyte": "agr-andesbyte-v3",
      },
    };
    const result = mergeVendorData(effective, [
      agreementEntry({ vendor_key: "andesbyte", vendor_name: "Andesbyte SAS", kind: "hourly", version: 3 }),
    ]);
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      source: "agreement",
      agreementVersion: "agr-andesbyte-v3",
      agreementKind: "hourly",
      hasVariablePricing: true,
      hasPaymentSeries: false,
    });
  });

  it("de-duplicates repeated vendor names", () => {
    const effective: EffectiveRulesResponse = {
      rules: baseRulesConfig({ allowed_beneficiaries: ["Globex LLC", "Globex LLC"] }),
      provenance: {},
    };
    expect(mergeVendorData(effective, [])).toHaveLength(1);
  });
});

describe("vendorProvenanceLabel", () => {
  it("labels a base vendor", () => {
    const [vendor] = mergeVendorData(
      { rules: baseRulesConfig({ allowed_beneficiaries: ["Base Co"] }), provenance: {} },
      [],
    );
    expect(vendorProvenanceLabel(vendor)).toBe("Reglas base");
  });

  it("labels an agreement vendor with its version number", () => {
    const [vendor] = mergeVendorData(
      {
        rules: baseRulesConfig({ allowed_beneficiaries: ["Globex LLC"] }),
        provenance: { "allowed_beneficiaries:globex": "agr-globex-v2" },
      },
      [agreementEntry({ version: 2 })],
    );
    expect(vendorProvenanceLabel(vendor)).toBe("Acuerdo v2");
  });
});
