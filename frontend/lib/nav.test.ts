import { describe, expect, it } from "vitest";

import { isActiveNavLink, NAV_LINKS } from "./nav";

describe("NAV_LINKS", () => {
  it("has the seven expected sections in order", () => {
    expect(NAV_LINKS.map((l) => l.href)).toEqual([
      "/",
      "/reglas",
      "/decisiones",
      "/bandeja",
      "/aprobaciones",
      "/metricas",
      "/subir",
    ]);
  });
});

describe("isActiveNavLink", () => {
  it("matches the home link only on exact /", () => {
    expect(isActiveNavLink("/", "/")).toBe(true);
    expect(isActiveNavLink("/reglas", "/")).toBe(false);
  });

  it("matches a section root and its sub-routes", () => {
    expect(isActiveNavLink("/decisiones", "/decisiones")).toBe(true);
    expect(isActiveNavLink("/decisiones/dec_0042", "/decisiones")).toBe(true);
  });

  it("does not match a different section with a shared prefix", () => {
    expect(isActiveNavLink("/decisionesextra", "/decisiones")).toBe(false);
  });
});
