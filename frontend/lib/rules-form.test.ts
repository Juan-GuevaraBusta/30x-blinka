import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

import type { RulesConfig } from "./rules-types";
import { canonicalJson } from "./canonical-json";
import { cloneRulesConfig, validateDraft } from "./rules-form";
import { versionLabel } from "./version-label";

const repoRoot = join(dirname(fileURLToPath(import.meta.url)), "..", "..");
const samplePath = join(repoRoot, "data", "rules.json");

function loadSample(): RulesConfig {
  return JSON.parse(readFileSync(samplePath, "utf8")) as RulesConfig;
}

describe("versionLabel", () => {
  it("same document yields same label", async () => {
    const doc = loadSample();
    expect(await versionLabel(doc)).toBe(await versionLabel(cloneRulesConfig(doc)));
  });

  it("different documents yield different labels", async () => {
    const a = loadSample();
    const b = cloneRulesConfig(a);
    b.human_approval_threshold = 2500;
    expect(await versionLabel(a)).not.toBe(await versionLabel(b));
  });

  it("canonical JSON sorts keys", () => {
    const doc = loadSample();
    const parsed = JSON.parse(canonicalJson(doc)) as Record<string, unknown>;
    const keys = Object.keys(parsed);
    expect(keys).toEqual([...keys].sort());
  });
});

describe("validateDraft", () => {
  it("accepts the seed rules document", () => {
    const result = validateDraft(loadSample());
    expect(result.ok).toBe(true);
  });

  it("rejects per_payment <= 0", () => {
    const doc = cloneRulesConfig(loadSample());
    doc.limits.per_payment = -1;
    const result = validateDraft(doc);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.some((e) => e.includes("per_payment"))).toBe(true);
    }
  });

  it("rejects approvers without default", () => {
    const doc = cloneRulesConfig(loadSample());
    const rest = { ...doc.approvers };
    delete rest.default;
    doc.approvers = rest;
    const result = validateDraft(doc);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.some((e) => e.includes("default"))).toBe(true);
    }
  });

  it("rejects J5 in jev_thresholds", () => {
    const doc = cloneRulesConfig(loadSample()) as RulesConfig & {
      jev_thresholds: Record<string, number>;
    };
    doc.jev_thresholds.J5 = 0.5;
    const result = validateDraft(doc);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.some((e) => e.includes("J5"))).toBe(true);
    }
  });
});
