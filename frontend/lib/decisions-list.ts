import type { Decision } from "@/lib/decision-types";

// T6.7 (D057): pending review comes first — that is the queue that needs attention.
export const DECISION_LIST_FILTERS = ["pendientes", "frenadas", "pagadas"] as const;

export type DecisionListFilter = (typeof DECISION_LIST_FILTERS)[number];

export const FILTER_CONTROL_LABELS: Record<DecisionListFilter, string> = {
  pendientes: "Pendientes",
  frenadas: "Frenadas",
  pagadas: "Pagadas",
};

export const DEFAULT_DECISION_LIST_FILTER: DecisionListFilter = "pendientes";

/** Reads the `?estado=` query param (T6.7); falls back to the default filter when absent or invalid. */
export function parseInitialFilter(value: string | string[] | undefined): DecisionListFilter {
  const raw = Array.isArray(value) ? value[0] : value;
  if (raw && (DECISION_LIST_FILTERS as readonly string[]).includes(raw)) {
    return raw as DecisionListFilter;
  }
  return DEFAULT_DECISION_LIST_FILTER;
}

/** Maps UI filter control to `GET /decisions?decision=` query value. */
export function filterToApiDecision(filter: DecisionListFilter): Decision {
  switch (filter) {
    case "pagadas":
      return "PAGAR";
    case "frenadas":
      return "FRENAR";
    case "pendientes":
      return "ESCALAR";
  }
}

/** Row status label for a stored `decision` value (not the filter name). */
export function rowStatusLabel(decision: Decision): string {
  switch (decision) {
    case "PAGAR":
      return "Pagada";
    case "FRENAR":
      return "Frenada";
    case "ESCALAR":
      return "Pendiente";
  }
}

/** Motivo column: `summary` unchanged, character for character. */
export function decisionMotivo(summary: string): string {
  return summary;
}

export function emptyStateMessage(filter: DecisionListFilter): string {
  switch (filter) {
    case "pagadas":
      return "No hay facturas pagadas.";
    case "frenadas":
      return "No hay facturas frenadas.";
    case "pendientes":
      return "No hay facturas pendientes de revisión.";
  }
}

export function statusToneClass(decision: Decision): string {
  switch (decision) {
    case "PAGAR":
      return "text-success";
    case "FRENAR":
      return "text-danger";
    case "ESCALAR":
      return "text-accent";
  }
}
