import { describe, expect, it } from "vitest";
import { isActiveSettingsLink, SETTINGS_NAV_LINKS } from "./ajustes-nav";

describe("SETTINGS_NAV_LINKS", () => {
  it("has the four sections in order", () => {
    expect(SETTINGS_NAV_LINKS.map((link) => link.href)).toEqual([
      "/reglas",
      "/ajustes/politica",
      "/ajustes/proveedores",
      "/ajustes/acuerdos",
    ]);
  });
});

describe("isActiveSettingsLink", () => {
  it("matches the exact path", () => {
    expect(isActiveSettingsLink("/ajustes/politica", "/ajustes/politica")).toBe(true);
  });

  it("matches a sub-route", () => {
    expect(isActiveSettingsLink("/ajustes/proveedores/Globex%20LLC", "/ajustes/proveedores")).toBe(true);
  });

  it("does not match an unrelated path", () => {
    expect(isActiveSettingsLink("/ajustes/politica", "/ajustes/proveedores")).toBe(false);
  });
});
