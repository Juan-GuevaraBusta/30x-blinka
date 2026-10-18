import type { CheckResult } from "@/lib/decision-types";

/** Mirrors `backend/app/api/schemas.py` `ApprovalStatusBody` (T7.1, D059 §4). */
export interface ApprovalStatusBody {
  route_id: string | null;
  required: number;
  collected: number;
  approvers: string[];
  satisfied: boolean;
  rejected: boolean;
  payment_ready: boolean;
  pending_checks: string[];
}

/** "1 de 2 aprobaciones" (T7.5 §2); collected is clamped to required, extras noted. */
export function approvalCountLabel(status: ApprovalStatusBody): string {
  if (status.required <= 0) {
    return "No se requieren aprobaciones adicionales.";
  }
  const word = status.required === 1 ? "aprobación" : "aprobaciones";
  // Extra approvals beyond the requirement never read as "2 de 1".
  const shown = Math.min(status.collected, status.required);
  const extra = status.collected - shown;
  const base = `${shown} de ${status.required} ${word}`;
  if (extra <= 0) return base;
  return `${base} (+${extra} ${extra === 1 ? "adicional" : "adicionales"})`;
}

/** "alto-monto" -> "Alto monto". Purely cosmetic: routes have no separate display name. */
export function humanizeRouteId(routeId: string): string {
  const words = routeId.replace(/[-_]+/g, " ").trim();
  if (!words) return routeId;
  return words.charAt(0).toUpperCase() + words.slice(1);
}

/** "Ruta: Alto monto" (T7.5 §2), or a plain-approval fallback when there is no route. */
export function routeDisplayLabel(routeId: string | null): string {
  if (!routeId) return "Ruta: aprobación simple";
  return `Ruta: ${humanizeRouteId(routeId)}`;
}

/**
 * "Aprobaciones completas, pero falta resolver: Cuadra con contrato (R06)."
 * Only shown once every required approval is in and nothing is rejected, but
 * `payment_ready` is still false because another check besides R04/R14 is not OK.
 */
export function pendingChecksSentence(status: ApprovalStatusBody, checks: CheckResult[]): string | null {
  if (!status.satisfied || status.rejected || status.pending_checks.length === 0) {
    return null;
  }
  const parts = status.pending_checks.map((rule) => {
    const check = checks.find((candidate) => candidate.rule === rule);
    return check ? `${check.name} (${rule})` : rule;
  });
  return `Aprobaciones completas, pero falta resolver: ${parts.join(", ")}.`;
}

/** "Finanzas, CFO" from the collected approver emails, or a plain empty-state sentence. */
export function approversSummary(status: ApprovalStatusBody): string {
  if (status.approvers.length === 0) {
    return "Nadie ha aprobado todavía.";
  }
  return status.approvers.join(", ");
}

export function approvalStateLabel(status: ApprovalStatusBody): string {
  if (status.rejected) return "Rechazada";
  if (status.payment_ready) return "Lista para pagar";
  if (status.satisfied) return "Aprobaciones completas";
  return "Pendiente de aprobación";
}
