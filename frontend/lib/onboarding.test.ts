import { describe, expect, it } from "vitest";

import type { Me } from "@/lib/me";
import {
  companyErrorMessage,
  onboardingRedirect,
  validateCompanyForm,
} from "@/lib/onboarding";

const withCompany: Me = {
  user_id: "u",
  email: "u@x.test",
  company: { id: "c", name: "Beta", base_currency: "EUR", is_demo: false, configured: false },
  member: { user_id: "u", email: "u@x.test", role: "admin", approver_groups: ["cfo"], is_approver: true },
};
const withoutCompany: Me = { user_id: "u", email: "u@x.test", company: null, member: null };

describe("onboarding (T9.8)", () => {
  it("normalizes the name and currency", () => {
    expect(validateCompanyForm({ name: "  Beta   SAS ", baseCurrency: "eur", isDemo: true })).toEqual({
      ok: true,
      body: { name: "Beta SAS", base_currency: "EUR", is_demo: true },
    });
  });

  it("rejects an empty name and an unknown currency", () => {
    expect(validateCompanyForm({ name: "  ", baseCurrency: "USD", isDemo: false }).ok).toBe(false);
    expect(validateCompanyForm({ name: "Beta", baseCurrency: "XYZ", isDemo: false }).ok).toBe(false);
  });

  it("sends users without company to onboarding and back home once they have one", () => {
    expect(onboardingRedirect("/decisiones", withoutCompany)).toBe("/onboarding");
    expect(onboardingRedirect("/onboarding", withoutCompany)).toBeNull();
    expect(onboardingRedirect("/onboarding", withCompany)).toBe("/");
    expect(onboardingRedirect("/decisiones", withCompany)).toBeNull();
    expect(onboardingRedirect("/decisiones", null)).toBeNull();
  });

  it("explains API errors in Spanish", () => {
    expect(companyErrorMessage("company_name_taken")).toContain("Ya existe");
    expect(companyErrorMessage("whatever")).toContain("No se pudo");
  });
});
