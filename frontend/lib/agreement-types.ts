/** Mirrors `backend/app/models/agreement.py` (T9.1, D061; read-only contract). */

export type AgreementKind = "retainer" | "hourly" | "installments" | "milestones" | "unit_pricing";
export type AgreementStatus = "active" | "superseded" | "inactive";
export type AgreementPeriodicity = "monthly" | "biweekly" | "quarterly" | "annual";

export interface AmountRange {
  min: number;
  max: number;
}

export interface OvertimeTerms {
  multiplier: number;
  max_hours?: number | null;
}

export interface AgreementInstallmentItem {
  key: string;
  due_from: string;
  due_to: string;
  amount: number;
}

export interface TieredTier {
  up_to: number | null;
  rate: number;
}

export interface UnitPricingUnitRate {
  kind: "unit_rate";
  unit: string;
  rate: number;
}

export interface UnitPricingTiered {
  kind: "tiered";
  unit: string;
  tiers: TieredTier[];
}

interface AgreementCommon {
  vendor_name: string;
  vendor_key: string;
  department?: string | null;
  currency: string;
  valid_from: string;
  valid_to?: string | null;
  sender_emails?: string[];
  source_clauses?: Record<string, string>;
}

export interface RetainerAgreement extends AgreementCommon {
  kind: "retainer";
  periodicity: AgreementPeriodicity;
  amount: AmountRange;
  total_cap?: number | null;
}

export interface HourlyAgreement extends AgreementCommon {
  kind: "hourly";
  unit: "hora";
  rate: number;
  included_hours?: number | null;
  overtime?: OvertimeTerms | null;
  period_cap?: number | null;
}

export interface InstallmentsAgreement extends AgreementCommon {
  kind: "installments" | "milestones";
  items: AgreementInstallmentItem[];
  total_cap?: number | null;
}

export interface UnitPricingAgreement extends AgreementCommon {
  kind: "unit_pricing";
  formula: UnitPricingUnitRate | UnitPricingTiered;
  period_cap?: number | null;
}

export type VendorAgreement =
  | RetainerAgreement
  | HourlyAgreement
  | InstallmentsAgreement
  | UnitPricingAgreement;

export interface VendorAgreementVersion {
  vendor_key: string;
  version: number;
  terms: VendorAgreement;
  source_sha256?: string | null;
  spans: Record<string, string>;
  confirmed_by: string;
  confirmed_at: string;
  status: AgreementStatus;
}

export interface AgreementListEntry {
  vendor_key: string;
  vendor_name: string;
  kind: AgreementKind;
  version: number;
  status: AgreementStatus;
  confirmed_by: string;
  confirmed_at: string;
  valid_from: string;
  valid_to: string | null;
}

export interface AgreementHistory {
  vendor_key: string;
  active: VendorAgreementVersion | null;
  versions: VendorAgreementVersion[];
}

export interface AgreementDraftResponse {
  draft: Record<string, unknown>;
  spans: Record<string, string>;
  missing: string[];
  source_sha256: string;
}

export const AGREEMENT_KIND_LABELS: Record<AgreementKind, string> = {
  retainer: "Retainer",
  hourly: "Horas con extras",
  installments: "Cuotas",
  milestones: "Hitos",
  unit_pricing: "Precio unitario",
};
