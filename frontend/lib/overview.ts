import type { Decision } from "@/lib/decision-types";
import {
  DECISION_LIST_FILTERS,
  filterToApiDecision,
  type DecisionListFilter,
} from "@/lib/decisions-list";

export const OVERVIEW_EXPLANATION =
  "Tachyon lee cada factura y decide PAGAR, FRENAR o ESCALAR según las reglas vigentes de la empresa (límites, beneficiarios permitidos, presupuestos por área). Nunca paga fuera de esas reglas, y cada decisión queda registrada con su explicación para que una persona pueda revisarla.";

export type OverviewCardKey = DecisionListFilter;

export type OverviewCardConfig = {
  key: OverviewCardKey;
  label: string;
  decision: Decision;
  href: string;
};

// Overview-specific card copy; filter keys, decision mapping and estado query values come from
// decisions-list.ts (R2) so the two screens can never drift out of sync.
const OVERVIEW_CARD_LABELS: Record<DecisionListFilter, string> = {
  pendientes: "Pendientes de aprobación",
  frenadas: "Frenadas",
  pagadas: "Pagadas",
};

/**
 * Three count cards on the home panel, each linking to the matching /decisiones filter (T6.7).
 * Derived from decisions-list.ts (R2): order matches DECISION_LIST_FILTERS
 * (Pendientes, Frenadas, Pagadas) and the decision mapping / estado query value come from the
 * same single source as the decisions list page, instead of a second hardcoded copy.
 */
export const OVERVIEW_CARDS: OverviewCardConfig[] = DECISION_LIST_FILTERS.map((filter) => ({
  key: filter,
  label: OVERVIEW_CARD_LABELS[filter],
  decision: filterToApiDecision(filter),
  href: `/decisiones?estado=${filter}`,
}));

export type HowItWorksStep = {
  title: string;
  description: string;
};

export const HOW_IT_WORKS_STEPS: HowItWorksStep[] = [
  {
    title: "1. Llega la factura",
    description: "Se sube un archivo sintético o llega por un canal configurado (correo, chat).",
  },
  {
    title: "2. Se leen los datos",
    description: "El agente extrae beneficiario, monto, moneda y vencimiento del documento.",
  },
  {
    title: "3. Se aplican las reglas",
    description:
      "Cada chequeo compara esos datos contra las reglas vigentes; cualquier falla o duda escala o frena.",
  },
  {
    title: "4. Queda registrada la decisión",
    description: "PAGAR, FRENAR o ESCALAR se guarda con su explicación; nada se paga de verdad.",
  },
];

/** Validates the GET /api/decisions body and returns its row count. */
export function parseDecisionCount(payload: unknown): number {
  if (!Array.isArray(payload)) {
    throw new Error("INVALID_BODY");
  }
  return payload.length;
}
