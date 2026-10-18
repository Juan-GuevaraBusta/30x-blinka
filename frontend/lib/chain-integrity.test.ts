import { describe, expect, it } from "vitest";

import {
  chainBadgeLabel,
  chainBadgeToneClass,
  isChainVerification,
} from "./chain-integrity";

describe("isChainVerification", () => {
  it("accepts a well-formed ok body", () => {
    expect(isChainVerification({ ok: true, length: 3, first_broken_id: null })).toBe(true);
  });

  it("accepts a well-formed broken body", () => {
    expect(isChainVerification({ ok: false, length: 3, first_broken_id: "dec_0002" })).toBe(
      true,
    );
  });

  it("rejects a missing or wrongly typed field", () => {
    expect(isChainVerification({ length: 3, first_broken_id: null })).toBe(false);
    expect(isChainVerification({ ok: "true", length: 3, first_broken_id: null })).toBe(false);
    expect(isChainVerification({ ok: true, length: "3", first_broken_id: null })).toBe(false);
    expect(isChainVerification({ ok: true, length: 3, first_broken_id: 2 })).toBe(false);
  });

  it("rejects non-objects", () => {
    expect(isChainVerification(null)).toBe(false);
    expect(isChainVerification(undefined)).toBe(false);
    expect(isChainVerification("ok")).toBe(false);
  });
});

describe("chainBadgeLabel", () => {
  it("reads 'Registro íntegro ✓' when ok", () => {
    expect(chainBadgeLabel({ ok: true, length: 3, first_broken_id: null })).toBe(
      "Registro íntegro ✓",
    );
  });

  it("names the exact broken id when not ok", () => {
    expect(chainBadgeLabel({ ok: false, length: 3, first_broken_id: "dec_0002" })).toBe(
      "Registro alterado en dec_0002",
    );
  });

  it("falls back to a placeholder if first_broken_id is somehow null while not ok", () => {
    expect(chainBadgeLabel({ ok: false, length: 0, first_broken_id: null })).toBe(
      "Registro alterado en posición desconocida",
    );
  });
});

describe("chainBadgeToneClass", () => {
  it("is the success tone when ok, danger tone when not", () => {
    expect(chainBadgeToneClass({ ok: true, length: 1, first_broken_id: null })).toBe(
      "text-success",
    );
    expect(chainBadgeToneClass({ ok: false, length: 1, first_broken_id: "dec_1" })).toBe(
      "text-danger",
    );
  });
});
