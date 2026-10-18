import { describe, expect, it } from "vitest";
import type { CheckResult } from "@/lib/decision-types";
import {
  approvalCountLabel,
  approvalStateLabel,
  approversSummary,
  humanizeRouteId,
  pendingChecksSentence,
  routeDisplayLabel,
  type ApprovalStatusBody,
} from "./approval-status-present";

function status(overrides: Partial<ApprovalStatusBody>): ApprovalStatusBody {
  return {
    route_id: "alto-monto",
    required: 2,
    collected: 1,
    approvers: [],
    satisfied: false,
    rejected: false,
    payment_ready: false,
    pending_checks: [],
    ...overrides,
  };
}

describe("approvalCountLabel", () => {
  it('renders "x de N aprobaciones" from a simulated /approval response', () => {
    expect(approvalCountLabel(status({ collected: 1, required: 2 }))).toBe("1 de 2 aprobaciones");
  });

  it("uses the singular word when exactly one approval is required", () => {
    expect(approvalCountLabel(status({ collected: 0, required: 1 }))).toBe("0 de 1 aprobación");
  });

  it("has a plain sentence when no approval is required at all", () => {
    expect(approvalCountLabel(status({ collected: 0, required: 0 }))).toBe(
      "No se requieren aprobaciones adicionales.",
    );
  });
});

describe("routeDisplayLabel / humanizeRouteId", () => {
  it('turns "alto-monto" into "Ruta: Alto monto"', () => {
    expect(humanizeRouteId("alto-monto")).toBe("Alto monto");
    expect(routeDisplayLabel("alto-monto")).toBe("Ruta: Alto monto");
  });

  it("falls back to a plain-approval label when there is no route", () => {
    expect(routeDisplayLabel(null)).toBe("Ruta: aprobación simple");
  });
});

describe("pendingChecksSentence", () => {
  const checks: CheckResult[] = [
    { rule: "R06", name: "Cuadra con contrato", result: "FALLA", detail: "No hay contrato confirmado." },
  ];

  it("builds the completed-approvals-but-pending-check sentence", () => {
    const text = pendingChecksSentence(
      status({ satisfied: true, rejected: false, pending_checks: ["R06"] }),
      checks,
    );
    expect(text).toBe("Aprobaciones completas, pero falta resolver: Cuadra con contrato (R06).");
  });

  it("is null while approvals are still missing", () => {
    expect(pendingChecksSentence(status({ satisfied: false, pending_checks: ["R06"] }), checks)).toBeNull();
  });

  it("is null when the decision was rejected", () => {
    expect(
      pendingChecksSentence(status({ satisfied: true, rejected: true, pending_checks: ["R06"] }), checks),
    ).toBeNull();
  });

  it("is null when payment is already fully ready", () => {
    expect(pendingChecksSentence(status({ satisfied: true, pending_checks: [] }), checks)).toBeNull();
  });
});

describe("approversSummary / approvalStateLabel", () => {
  it("has an empty-state sentence with no approvers yet", () => {
    expect(approversSummary(status({ approvers: [] }))).toBe("Nadie ha aprobado todavía.");
  });

  it("joins approver emails", () => {
    expect(approversSummary(status({ approvers: ["finanzas@demo.test", "cfo@demo.test"] }))).toBe(
      "finanzas@demo.test, cfo@demo.test",
    );
  });

  it("labels a rejected decision", () => {
    expect(approvalStateLabel(status({ rejected: true }))).toBe("Rechazada");
  });

  it("labels a payment-ready decision", () => {
    expect(approvalStateLabel(status({ satisfied: true, payment_ready: true }))).toBe("Lista para pagar");
  });
});
