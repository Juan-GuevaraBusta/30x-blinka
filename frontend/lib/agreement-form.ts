import type { AgreementKind, AgreementPeriodicity, VendorAgreement } from "@/lib/agreement-types";

// Mirrors `app.rules.normalize.normalize_party_name` (backend) closely enough to build the
// PUT /agreements/{vendor_key} URL client-side; the server always recomputes and owns the
// canonical value (§2) -- this is only ever used for routing, never trusted as the real key.
const _LEGAL_SUFFIXES = new Set([
  "llc",
  "ltd",
  "ltda",
  "inc",
  "corp",
  "co",
  "sa",
  "sas",
  "spa",
  "limited",
  "corporation",
]);

export function normalizeVendorKey(rawName: string): string {
  const collapsed = rawName
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^\w\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  if (!collapsed) return "";
  const parts = collapsed.split(" ");
  while (parts.length > 1 && _LEGAL_SUFFIXES.has(parts[parts.length - 1])) {
    parts.pop();
  }
  if (parts.length >= 2 && parts[parts.length - 2] === "s" && parts[parts.length - 1] === "a") {
    parts.pop();
    parts.pop();
  }
  return parts.join(" ");
}

/** Flat, string-valued form state for `/ajustes/acuerdos/nuevo` (T9.1, D061 §5). */
export interface AgreementFormState {
  kind: AgreementKind;
  vendor_name: string;
  department: string;
  currency: string;
  valid_from: string;
  valid_to: string;
  // retainer
  periodicity: AgreementPeriodicity;
  amount_min: string;
  amount_max: string;
  total_cap: string;
  // hourly
  rate: string;
  included_hours: string;
  overtime_multiplier: string;
  overtime_max_hours: string;
  period_cap: string;
  // installments/milestones: one "key|due_from|due_to|amount" per line
  itemsText: string;
  // unit_pricing
  unit: string;
  formulaKind: "unit_rate" | "tiered";
  // tiered: one "up_to|rate" per line, blank up_to = open-ended tier
  tiersText: string;
}

export function emptyFormState(): AgreementFormState {
  return {
    kind: "retainer",
    vendor_name: "",
    department: "",
    currency: "USD",
    valid_from: "",
    valid_to: "",
    periodicity: "monthly",
    amount_min: "",
    amount_max: "",
    total_cap: "",
    rate: "",
    included_hours: "",
    overtime_multiplier: "",
    overtime_max_hours: "",
    period_cap: "",
    itemsText: "",
    unit: "",
    formulaKind: "unit_rate",
    tiersText: "",
  };
}

/** Required field names per `kind`, used to drive the "Confirmar acuerdo" disabled state. */
export function requiredFields(kind: AgreementKind): string[] {
  const common = ["vendor_name", "currency", "valid_from"];
  if (kind === "retainer") return [...common, "periodicity", "amount_min", "amount_max"];
  if (kind === "hourly") return [...common, "rate"];
  if (kind === "installments" || kind === "milestones") return [...common, "itemsText"];
  return [...common, "unit", "rate_or_tiers"];
}

function isBlank(value: string): boolean {
  return value.trim() === "";
}

/** Field names still missing a value (`""`), driving the disabled-confirm-button state (§5). */
export function missingRequiredFields(state: AgreementFormState): string[] {
  const missing: string[] = [];
  for (const field of requiredFields(state.kind)) {
    if (field === "rate_or_tiers") {
      if (state.formulaKind === "unit_rate" && isBlank(state.rate)) missing.push("rate");
      if (state.formulaKind === "tiered" && isBlank(state.tiersText)) missing.push("tiersText");
      continue;
    }
    const value = (state as unknown as Record<string, string>)[field];
    if (isBlank(value)) missing.push(field);
  }
  return missing;
}

function parseItemsText(text: string): { key: string; due_from: string; due_to: string; amount: number }[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => {
      const [key, due_from, due_to, amount] = line.split("|").map((part) => part.trim());
      return { key, due_from, due_to, amount: Number(amount) };
    });
}

function parseTiersText(text: string): { up_to: number | null; rate: number }[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => line.length > 0)
    .map((line) => {
      const [upTo, rate] = line.split("|").map((part) => part.trim());
      return { up_to: upTo === "" ? null : Number(upTo), rate: Number(rate) };
    });
}

/** Builds the `VendorAgreement` body for `PUT /agreements/{vendor_key}`, or `null` while incomplete. */
export function buildAgreementTerms(state: AgreementFormState): VendorAgreement | null {
  if (missingRequiredFields(state).length > 0) return null;

  const common = {
    vendor_name: state.vendor_name.trim(),
    vendor_key: normalizeVendorKey(state.vendor_name),
    department: isBlank(state.department) ? null : state.department.trim(),
    currency: state.currency.trim(),
    valid_from: state.valid_from,
    valid_to: isBlank(state.valid_to) ? null : state.valid_to,
  };

  if (state.kind === "retainer") {
    return {
      ...common,
      kind: "retainer",
      periodicity: state.periodicity,
      amount: { min: Number(state.amount_min), max: Number(state.amount_max) },
      total_cap: isBlank(state.total_cap) ? null : Number(state.total_cap),
    };
  }

  if (state.kind === "hourly") {
    const hasOvertime = !isBlank(state.overtime_multiplier);
    return {
      ...common,
      kind: "hourly",
      unit: "hora",
      rate: Number(state.rate),
      included_hours: isBlank(state.included_hours) ? null : Number(state.included_hours),
      overtime: hasOvertime
        ? {
            multiplier: Number(state.overtime_multiplier),
            max_hours: isBlank(state.overtime_max_hours) ? null : Number(state.overtime_max_hours),
          }
        : null,
      period_cap: isBlank(state.period_cap) ? null : Number(state.period_cap),
    };
  }

  if (state.kind === "installments" || state.kind === "milestones") {
    return {
      ...common,
      kind: state.kind,
      items: parseItemsText(state.itemsText),
      total_cap: isBlank(state.total_cap) ? null : Number(state.total_cap),
    };
  }

  // unit_pricing
  return {
    ...common,
    kind: "unit_pricing",
    formula:
      state.formulaKind === "unit_rate"
        ? { kind: "unit_rate", unit: state.unit.trim(), rate: Number(state.rate) }
        : { kind: "tiered", unit: state.unit.trim(), tiers: parseTiersText(state.tiersText) },
    period_cap: isBlank(state.period_cap) ? null : Number(state.period_cap),
  };
}

/** Applies a draft's field map (already quote-validated by the backend) onto a blank form state. */
export function applyDraftToFormState(
  state: AgreementFormState,
  draft: Record<string, unknown>,
): AgreementFormState {
  const next = { ...state };
  const str = (value: unknown): string => (value == null ? "" : String(value));
  if (typeof draft.kind === "string") {
    next.kind = draft.kind as AgreementKind;
  }
  if ("vendor_name" in draft) next.vendor_name = str(draft.vendor_name);
  if ("department" in draft) next.department = str(draft.department);
  if ("currency" in draft) next.currency = str(draft.currency);
  if ("valid_from" in draft) next.valid_from = str(draft.valid_from);
  if ("valid_to" in draft) next.valid_to = str(draft.valid_to);
  if ("periodicity" in draft) next.periodicity = str(draft.periodicity) as AgreementPeriodicity;
  if ("amount_min" in draft) next.amount_min = str(draft.amount_min);
  if ("amount_max" in draft) next.amount_max = str(draft.amount_max);
  if ("total_cap" in draft) next.total_cap = str(draft.total_cap);
  if ("unit" in draft) next.unit = str(draft.unit);
  if ("rate" in draft) next.rate = str(draft.rate);
  if ("included_hours" in draft) next.included_hours = str(draft.included_hours);
  if ("overtime_multiplier" in draft) next.overtime_multiplier = str(draft.overtime_multiplier);
  if ("overtime_max_hours" in draft) next.overtime_max_hours = str(draft.overtime_max_hours);
  if ("period_cap" in draft) next.period_cap = str(draft.period_cap);
  return next;
}
