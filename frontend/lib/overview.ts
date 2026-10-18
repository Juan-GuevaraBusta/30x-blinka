import type { Decision } from "@/lib/decision-types";

export const OVERVIEW_EXPLANATION =
  "El agente de pagos lee cada factura y decide PAGAR, FRENAR o ESCALAR según las reglas vigentes de la empresa (límites, beneficiarios permitidos, presupuestos por área). Nunca paga fuera de esas reglas, y cada decisión queda registrada con su explicación para que una persona pueda revisarla.";

export type OverviewCardKey = "pagadas" | "frenadas" | "pendientes";

export type OverviewCardConfig = {
  key: OverviewCardKey;
  label: string;
  decision: Decision;
  href: string;
};

/** Three count cards on the home panel, each linking to the matching /decisiones filter (T6.7). */
export const OVERVIEW_CARDS: OverviewCardConfig[] = [
  { key: "pagadas", label: "Pagadas", decision: "PAGAR", href: "/decisiones?estado=pagadas" },
  { key: "frenadas", label: "Frenadas", decision: "FRENAR", href: "/decisiones?estado=frenadas" },
  {
    key: "pendientes",
    label: "Pendientes de aprobación",
    decision: "ESCALAR",
    href: "/decisiones?estado=pendientes",
  },
];

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
