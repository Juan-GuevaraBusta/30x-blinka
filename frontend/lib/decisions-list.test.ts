import { describe, expect, it } from "vitest";

import {
  DECISION_LIST_FILTERS,
  decisionMotivo,
  emptyStateMessage,
  filterToApiDecision,
  rowStatusLabel,
} from "./decisions-list";

describe("filterToApiDecision", () => {
  it("maps Pagadas, Frenadas and Pendientes to API enums", () => {
    expect(filterToApiDecision("pagadas")).toBe("PAGAR");
    expect(filterToApiDecision("frenadas")).toBe("FRENAR");
    expect(filterToApiDecision("pendientes")).toBe("ESCALAR");
  });
});

describe("rowStatusLabel", () => {
  it("maps API decision to row labels", () => {
    expect(rowStatusLabel("PAGAR")).toBe("Pagada");
    expect(rowStatusLabel("FRENAR")).toBe("Frenada");
    expect(rowStatusLabel("ESCALAR")).toBe("Pendiente");
  });
});

describe("decisionMotivo", () => {
  it("returns summary unchanged", () => {
    const summary =
      "Escalada: USD 4.200 llega al umbral de aprobación humana.";
    expect(decisionMotivo(summary)).toBe(summary);
  });
});

describe("emptyStateMessage", () => {
  it("uses the three empty copy strings from the spec", () => {
    for (const filter of DECISION_LIST_FILTERS) {
      const msg = emptyStateMessage(filter);
      expect(msg.length).toBeGreaterThan(0);
    }
    expect(emptyStateMessage("pagadas")).toBe("No hay facturas pagadas.");
    expect(emptyStateMessage("frenadas")).toBe("No hay facturas frenadas.");
    expect(emptyStateMessage("pendientes")).toBe(
      "No hay facturas pendientes de revisión.",
    );
  });
});
