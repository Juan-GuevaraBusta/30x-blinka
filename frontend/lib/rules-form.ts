import type { FailAction, RulesConfig, RuleId } from "./rules-types";
import { JEV_KEYS, RULE_IDS } from "./rules-types";

const TOP_LEVEL_KEYS = new Set([
  "company",
  "limits",
  "human_approval_threshold",
  "allowed_beneficiaries",
  "department_budgets",
  "approvers",
  "manual_blocks",
  "on_fail",
  "jev_thresholds",
]);

const COMPANY_KEYS = new Set(["name", "base_currency"]);
const LIMITS_KEYS = new Set(["per_payment", "per_period"]);
const PERIOD_KEYS = new Set(["type", "amount"]);
const ON_FAIL_KEYS = new Set<string>(RULE_IDS);
const JEV_THRESHOLD_KEYS = new Set<string>(JEV_KEYS);

export type ValidationResult =
  | { ok: true; document: RulesConfig }
  | { ok: false; errors: string[] };

function isPlainObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function forbidExtraKeys(
  obj: Record<string, unknown>,
  allowed: Set<string>,
  path: string,
  errors: string[],
): void {
  for (const key of Object.keys(obj)) {
    if (!allowed.has(key)) {
      errors.push(`Campo desconocido en ${path}: «${key}».`);
    }
  }
}

function nonEmptyString(value: unknown, path: string, errors: string[]): string | null {
  if (typeof value !== "string") {
    errors.push(`${path} debe ser texto.`);
    return null;
  }
  if (!value.trim()) {
    errors.push(`${path} no puede quedar vacío.`);
    return null;
  }
  return value;
}

function positiveNumber(value: unknown, path: string, errors: string[]): number | null {
  if (typeof value !== "number" || Number.isNaN(value)) {
    errors.push(`${path} debe ser un número mayor que cero.`);
    return null;
  }
  if (value <= 0) {
    errors.push(`${path} debe ser mayor que cero.`);
    return null;
  }
  return value;
}

function jevProbability(value: unknown, path: string, errors: string[]): number | null {
  if (typeof value !== "number" || Number.isNaN(value)) {
    errors.push(`${path} debe ser un número entre 0 y 1.`);
    return null;
  }
  if (value <= 0 || value > 1) {
    errors.push(`${path} debe estar entre 0 y 1 (límite superior incluido).`);
    return null;
  }
  return value;
}

/** Client-side gate before PUT; mirrors server `RulesConfig` validation. */
export function validateDraft(raw: unknown): ValidationResult {
  const errors: string[] = [];

  if (!isPlainObject(raw)) {
    return { ok: false, errors: ["El documento de reglas debe ser un objeto JSON."] };
  }

  forbidExtraKeys(raw, TOP_LEVEL_KEYS, "raíz", errors);

  const companyRaw = raw.company;
  if (!isPlainObject(companyRaw)) {
    errors.push("Falta el bloque «company».");
  } else {
    forbidExtraKeys(companyRaw, COMPANY_KEYS, "company", errors);
    nonEmptyString(companyRaw.name, "company.name", errors);
    nonEmptyString(companyRaw.base_currency, "company.base_currency", errors);
  }

  const limitsRaw = raw.limits;
  let perPayment: number | null = null;
  if (!isPlainObject(limitsRaw)) {
    errors.push("Falta el bloque «limits».");
  } else {
    forbidExtraKeys(limitsRaw, LIMITS_KEYS, "limits", errors);
    perPayment = positiveNumber(limitsRaw.per_payment, "limits.per_payment", errors);
    const periodRaw = limitsRaw.per_period;
    if (!isPlainObject(periodRaw)) {
      errors.push("Falta limits.per_period.");
    } else {
      forbidExtraKeys(periodRaw, PERIOD_KEYS, "limits.per_period", errors);
      if (periodRaw.type !== "calendar_month") {
        errors.push("limits.per_period.type solo admite «calendar_month».");
      }
      positiveNumber(periodRaw.amount, "limits.per_period.amount", errors);
    }
  }

  positiveNumber(raw.human_approval_threshold, "human_approval_threshold", errors);

  const beneficiaries = raw.allowed_beneficiaries;
  if (!Array.isArray(beneficiaries)) {
    errors.push("allowed_beneficiaries debe ser una lista.");
  } else if (beneficiaries.length === 0) {
    errors.push("Debe haber al menos un beneficiario permitido.");
  } else {
    for (let i = 0; i < beneficiaries.length; i += 1) {
      const entry = beneficiaries[i];
      if (typeof entry !== "string" || !entry.trim()) {
        errors.push(`El beneficiario en la posición ${i + 1} no puede quedar en blanco.`);
      }
    }
  }

  const budgets = raw.department_budgets;
  if (!isPlainObject(budgets)) {
    errors.push("department_budgets debe ser un objeto.");
  } else {
    const entries = Object.entries(budgets);
    if (entries.length === 0) {
      errors.push("Añade al menos un presupuesto por área.");
    }
    for (const [name, amount] of entries) {
      if (!name.trim()) {
        errors.push("Las claves de department_budgets no pueden quedar en blanco.");
      }
      positiveNumber(amount, `department_budgets.${name || "?"}`, errors);
    }
  }

  const approvers = raw.approvers;
  if (!isPlainObject(approvers)) {
    errors.push("approvers debe ser un objeto.");
  } else {
    if (!("default" in approvers)) {
      errors.push('approvers debe incluir la clave «default».');
    }
    for (const [name, email] of Object.entries(approvers)) {
      if (!name.trim()) {
        errors.push("Los nombres en approvers no pueden quedar en blanco.");
      }
      if (typeof email !== "string" || !email.trim()) {
        errors.push(`El correo de «${name || "?"}» no puede quedar en blanco.`);
      }
    }
  }

  const blocks = raw.manual_blocks;
  if (!Array.isArray(blocks)) {
    errors.push("manual_blocks debe ser una lista.");
  } else {
    for (let i = 0; i < blocks.length; i += 1) {
      const entry = blocks[i];
      if (typeof entry !== "string" || !entry.trim()) {
        errors.push(`El bloqueo manual en la posición ${i + 1} no puede quedar en blanco.`);
      }
    }
  }

  const onFail = raw.on_fail;
  if (!isPlainObject(onFail)) {
    errors.push("Falta el bloque «on_fail».");
  } else {
    forbidExtraKeys(onFail, ON_FAIL_KEYS, "on_fail", errors);
    for (const ruleId of RULE_IDS) {
      const action = onFail[ruleId];
      if (action !== "FRENAR" && action !== "ESCALAR") {
        errors.push(`on_fail.${ruleId} debe ser FRENAR o ESCALAR.`);
      }
    }
  }

  const jev = raw.jev_thresholds;
  if (!isPlainObject(jev)) {
    errors.push("Falta el bloque «jev_thresholds».");
  } else {
    forbidExtraKeys(jev, JEV_THRESHOLD_KEYS, "jev_thresholds", errors);
    if ("J5" in jev) {
      errors.push("jev_thresholds no admite J5; use solo J1, J2, J3, J4, J6 y J7.");
    }
    for (const key of JEV_KEYS) {
      jevProbability(jev[key], `jev_thresholds.${key}`, errors);
    }
  }

  if (errors.length > 0) {
    return { ok: false, errors };
  }

  if (perPayment !== null && perPayment <= 0) {
    return { ok: false, errors: ["limits.per_payment debe ser mayor que cero."] };
  }

  return { ok: true, document: raw as unknown as RulesConfig };
}

export function failActionLabel(action: FailAction): string {
  return action === "FRENAR" ? "Frenar pago" : "Escalar";
}

export function cloneRulesConfig(doc: RulesConfig): RulesConfig {
  return JSON.parse(JSON.stringify(doc)) as RulesConfig;
}

export function emptyOnFail(): Record<RuleId, FailAction> {
  const base = {} as Record<RuleId, FailAction>;
  for (const id of RULE_IDS) {
    base[id] = "ESCALAR";
  }
  return base;
}
