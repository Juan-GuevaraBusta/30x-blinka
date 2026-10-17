/** Mirrors `backend/app/models/rules_config.py` (read-only contract). */

export type FailAction = "FRENAR" | "ESCALAR";
export type PeriodType = "calendar_month";

export interface CompanyRef {
  name: string;
  base_currency: string;
}

export interface PeriodLimit {
  type: PeriodType;
  amount: number;
}

export interface Limits {
  per_payment: number;
  per_period: PeriodLimit;
}

export type RuleId =
  | "R01"
  | "R02"
  | "R03"
  | "R04"
  | "R05"
  | "R06"
  | "R07"
  | "R08"
  | "R09"
  | "R10"
  | "R11"
  | "R12"
  | "R13";

export type OnFail = Record<RuleId, FailAction>;

export type JevKey = "J1" | "J2" | "J3" | "J4" | "J6" | "J7";

export type JevThresholds = Record<JevKey, number>;

export interface RulesConfig {
  company: CompanyRef;
  limits: Limits;
  human_approval_threshold: number;
  allowed_beneficiaries: string[];
  department_budgets: Record<string, number>;
  approvers: Record<string, string>;
  manual_blocks: string[];
  on_fail: OnFail;
  jev_thresholds: JevThresholds;
}

export const RULE_IDS: RuleId[] = [
  "R01",
  "R02",
  "R03",
  "R04",
  "R05",
  "R06",
  "R07",
  "R08",
  "R09",
  "R10",
  "R11",
  "R12",
  "R13",
];

export const JEV_KEYS: JevKey[] = ["J1", "J2", "J3", "J4", "J6", "J7"];
