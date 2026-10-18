import { describe, expect, it } from "vitest";

import {
  HOW_IT_WORKS_STEPS,
  OVERVIEW_CARDS,
  OVERVIEW_EXPLANATION,
  parseDecisionCount,
} from "./overview";

describe("OVERVIEW_EXPLANATION", () => {
  it("is a non-empty plain-language paragraph", () => {
    expect(OVERVIEW_EXPLANATION.length).toBeGreaterThan(0);
    expect(OVERVIEW_EXPLANATION).toMatch(/PAGAR/);
  });
});

describe("OVERVIEW_CARDS", () => {
  it("has exactly three cards mapped to the right decision and filtered link", () => {
    expect(OVERVIEW_CARDS).toHaveLength(3);
    expect(OVERVIEW_CARDS.map((c) => c.key)).toEqual(["pagadas", "frenadas", "pendientes"]);
    expect(OVERVIEW_CARDS.map((c) => c.decision)).toEqual(["PAGAR", "FRENAR", "ESCALAR"]);
    for (const card of OVERVIEW_CARDS) {
      expect(card.href.startsWith("/decisiones?estado=")).toBe(true);
    }
  });
});

describe("HOW_IT_WORKS_STEPS", () => {
  it("has exactly four steps with title and description", () => {
    expect(HOW_IT_WORKS_STEPS).toHaveLength(4);
    for (const step of HOW_IT_WORKS_STEPS) {
      expect(step.title.length).toBeGreaterThan(0);
      expect(step.description.length).toBeGreaterThan(0);
    }
  });
});

describe("parseDecisionCount", () => {
  it("returns the array length for a valid list", () => {
    expect(parseDecisionCount([])).toBe(0);
    expect(parseDecisionCount([{}, {}, {}])).toBe(3);
  });

  it("throws INVALID_BODY for a non-array payload", () => {
    expect(() => parseDecisionCount({})).toThrow("INVALID_BODY");
    expect(() => parseDecisionCount(null)).toThrow("INVALID_BODY");
  });
});
