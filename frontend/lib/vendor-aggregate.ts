import { normalizeVendorKey } from "./agreement-form";
import type { AgreementKind, AgreementListEntry } from "./agreement-types";
import type { RulesConfig } from "./rules-types";

/**
 * `GET /api/rules/effective` response shape (T9.1, D061 §3): compiled
 * `RulesConfig` plus a `<field>:<vendor_key>` -> `agr-<vendor_key>-v<version>`
 * provenance map for every field an agreement contributed to.
 */
export interface EffectiveRulesResponse {
  rules: RulesConfig;
  provenance: Record<string, string>;
}

export type VendorSource = "base" | "agreement";

export interface VendorSummary {
  name: string;
  vendorKey: string;
  source: VendorSource;
  /** e.g. `"agr-globex-v2"`, present only when `source === "agreement"`. */
  agreementVersion: string | null;
  agreementKind: AgreementKind | null;
  hasPaymentSeries: boolean;
  hasVariablePricing: boolean;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

/** Pulls the trailing `-v<N>` out of a provenance value like `agr-globex-v2`. */
function parseAgreementVersionNumber(provenanceValue: string): number | null {
  const match = /-v(\d+)$/.exec(provenanceValue);
  return match ? Number(match[1]) : null;
}

/**
 * Merges `GET /rules/effective` (rules + provenance) with `GET /agreements`
 * into one per-vendor view, so the UI can show every vendor the backend
 * actually allows — whether it came from static `rules.json` or was added
 * solely through a confirmed agreement — with visible provenance (T1).
 *
 * Pure function: no fetching here, so it is trivially unit-testable with
 * plain fixtures (per ODD task instructions).
 */
export function mergeVendorData(
  effective: EffectiveRulesResponse,
  agreements: AgreementListEntry[],
): VendorSummary[] {
  const names = isStringArray(effective.rules?.allowed_beneficiaries)
    ? effective.rules.allowed_beneficiaries
    : [];
  const provenance = effective.provenance ?? {};
  const agreementByName = new Map(agreements.map((entry) => [entry.vendor_name, entry]));

  const seen = new Set<string>();
  const summaries: VendorSummary[] = [];

  for (const name of names) {
    if (seen.has(name)) continue;
    seen.add(name);

    const agreementEntry = agreementByName.get(name) ?? null;
    const vendorKey = agreementEntry?.vendor_key ?? normalizeVendorKey(name);
    const agreementVersion = provenance[`allowed_beneficiaries:${vendorKey}`] ?? null;

    summaries.push({
      name,
      vendorKey,
      source: agreementVersion ? "agreement" : "base",
      agreementVersion,
      agreementKind: agreementEntry?.kind ?? null,
      hasPaymentSeries: Boolean(provenance[`payment_series:${vendorKey}`]),
      hasVariablePricing: Boolean(provenance[`variable_pricing:${vendorKey}`]),
    });
  }

  return summaries;
}

/** "Reglas base" vs "Acuerdo v<N>" badge text for a merged vendor (T2). */
export function vendorProvenanceLabel(vendor: VendorSummary): string {
  if (vendor.source === "base" || !vendor.agreementVersion) {
    return "Reglas base";
  }
  const versionNumber = parseAgreementVersionNumber(vendor.agreementVersion);
  return versionNumber !== null ? `Acuerdo v${versionNumber}` : "Acuerdo";
}
