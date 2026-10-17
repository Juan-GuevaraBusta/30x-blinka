import { describe, expect, it } from "vitest";

import type { DecisionRecord } from "@/lib/decision-types";

import {
  buildHumanDecisionBody,
  humanActionHttpErrorMessage,
  isPendingEscalar,
  mergeHumanActionSuccess,
  MSG_REASON_REQUIRED,
  MSG_SERVER_422,
  validateHumanDecisionInput,
} from "./approvals";

function minimalRecord(overrides: Partial<DecisionRecord> = {}): DecisionRecord {
  return {
    id: "dec_test",
    invoice_id: "INV-TEST",
    received_at: "2026-01-01T12:00:00Z",
    decision: "ESCALAR",
    severity: 1,
    summary: "Resumen de prueba",
    extracted: { beneficiary: "Globex LLC", amount: 1000, currency: "USD" },
    checks: [],
    jev_signals: [],
    verifier: { consistent: true, issues: [] },
    admin_notice: null,
    next_step: "Pendiente de aprobación.",
    trace: {},
    versions: {
      rules_version: "v1",
      model_extractor: "ext",
      model_verifier: "ver",
      jev: "jev",
    },
    human_events: [],
    ...overrides,
  };
}

describe("validateHumanDecisionInput", () => {
  it("rejects empty or whitespace-only reason", () => {
    expect(validateHumanDecisionInput("cfo@demo.test", "").ok).toBe(false);
    expect(validateHumanDecisionInput("cfo@demo.test", "   ").ok).toBe(false);
    const fail = validateHumanDecisionInput("cfo@demo.test", "  ");
    if (!fail.ok) {
      expect(fail.message).toBe(MSG_REASON_REQUIRED);
    }
  });

  it("rejects empty author after trim", () => {
    expect(validateHumanDecisionInput("  ", "motivo").ok).toBe(false);
  });

  it("rejects fields longer than 500 characters", () => {
    const long = "a".repeat(501);
    expect(validateHumanDecisionInput(long, "ok").ok).toBe(false);
    expect(validateHumanDecisionInput("a@b.co", long).ok).toBe(false);
  });

  it("accepts trimmed author and reason", () => {
    const result = validateHumanDecisionInput("  cfo@demo.test  ", "  Coincide  ");
    expect(result).toEqual({
      ok: true,
      body: { author: "cfo@demo.test", reason: "Coincide" },
    });
  });
});

describe("buildHumanDecisionBody", () => {
  it("returns only author and reason keys", () => {
    const body = buildHumanDecisionBody("cfo@demo.test", "Coincide con el presupuesto");
    expect(Object.keys(body).sort()).toEqual(["author", "reason"]);
    expect(body).toEqual({
      author: "cfo@demo.test",
      reason: "Coincide con el presupuesto",
    });
  });
});

describe("isPendingEscalar", () => {
  it("is true only for ESCALAR without human events", () => {
    expect(isPendingEscalar(minimalRecord())).toBe(true);
    expect(
      isPendingEscalar(
        minimalRecord({
          human_events: [
            {
              author: "cfo@demo.test",
              at: "2026-01-02T12:00:00Z",
              action: "aprobada_humano",
              reason: "ok",
            },
          ],
        }),
      ),
    ).toBe(false);
    expect(isPendingEscalar(minimalRecord({ decision: "PAGAR", severity: 0 }))).toBe(false);
  });
});

describe("mergeHumanActionSuccess", () => {
  it("accepts 200 when decision and severity unchanged and one new event", () => {
    const previous = minimalRecord();
    const response = minimalRecord({
      human_events: [
        {
          author: "cfo@demo.test",
          at: "2026-01-02T12:00:00Z",
          action: "aprobada_humano",
          reason: "Coincide con el presupuesto",
        },
      ],
    });
    const merged = mergeHumanActionSuccess(previous, response);
    expect(merged.ok).toBe(true);
    if (merged.ok) {
      expect(merged.record.human_events).toHaveLength(1);
      expect(merged.record.decision).toBe("ESCALAR");
      expect(merged.record.severity).toBe(1);
    }
  });

  it("rejects when decision changes on 200", () => {
    const previous = minimalRecord();
    const response = minimalRecord({ decision: "PAGAR", severity: 0 });
    expect(mergeHumanActionSuccess(previous, response).ok).toBe(false);
  });

  it("rejects when human_events count does not grow by one", () => {
    const previous = minimalRecord();
    expect(mergeHumanActionSuccess(previous, previous).ok).toBe(false);
  });
});

describe("humanActionHttpErrorMessage", () => {
  it("maps 422 to server message", () => {
    expect(humanActionHttpErrorMessage(422)).toBe(MSG_SERVER_422);
  });

  it("maps 404 and 409 details", () => {
    expect(humanActionHttpErrorMessage(404, "not_found")).toMatch(/identificador/);
    expect(humanActionHttpErrorMessage(409, "not_escalated")).toMatch(/cola/);
  });
});
