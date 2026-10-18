import { describe, expect, it } from "vitest";
import { rulePlainExplanation } from "./rule-explanations";

describe("rulePlainExplanation", () => {
  it("has a plain-Spanish sentence for every series/policy rule R14-R18", () => {
    for (const rule of ["R14", "R15", "R16", "R17", "R18"]) {
      expect(rulePlainExplanation(rule)).toBeTruthy();
    }
  });

  it("returns null for a rule without a gloss", () => {
    expect(rulePlainExplanation("R01")).toBeNull();
  });
});
