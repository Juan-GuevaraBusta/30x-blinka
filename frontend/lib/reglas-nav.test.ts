import { describe, expect, it } from "vitest";
import { isActiveReglasLink, REGLAS_NAV_LINKS } from "./reglas-nav";

describe("REGLAS_NAV_LINKS", () => {
  it("has the four sections in order", () => {
    expect(REGLAS_NAV_LINKS.map((link) => link.href)).toEqual([
      "/reglas",
      "/reglas/politica",
      "/reglas/proveedores",
      "/reglas/acuerdos",
    ]);
  });
});

describe("isActiveReglasLink", () => {
  it("matches the exact path", () => {
    expect(isActiveReglasLink("/reglas/politica", "/reglas/politica")).toBe(true);
  });

  it("matches a sub-route", () => {
    expect(isActiveReglasLink("/reglas/proveedores/Globex%20LLC", "/reglas/proveedores")).toBe(true);
  });

  it("does not match an unrelated path", () => {
    expect(isActiveReglasLink("/reglas/politica", "/reglas/proveedores")).toBe(false);
  });

  it("matches the general-rules root only exactly, not its sibling sections", () => {
    expect(isActiveReglasLink("/reglas", "/reglas")).toBe(true);
    expect(isActiveReglasLink("/reglas/politica", "/reglas")).toBe(false);
    expect(isActiveReglasLink("/reglas/acuerdos/nuevo", "/reglas")).toBe(false);
  });
});
