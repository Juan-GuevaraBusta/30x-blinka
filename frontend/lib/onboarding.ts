import type { Me } from "@/lib/me";

/** Currencies in data/fx.json (the API rejects any other with 422). */
export const SUPPORTED_CURRENCIES = ["USD", "EUR", "MXN", "COP", "BRL"] as const;

export const ONBOARDING_PATH = "/onboarding";

export type CompanyForm = { name: string; baseCurrency: string; isDemo: boolean };

export type CompanyFormResult =
  | { ok: true; body: { name: string; base_currency: string; is_demo: boolean } }
  | { ok: false; message: string };

export function validateCompanyForm(form: CompanyForm): CompanyFormResult {
  const name = form.name.split(/\s+/).filter(Boolean).join(" ");
  if (!name) return { ok: false, message: "Escribe el nombre de la empresa." };
  if (name.length > 120) return { ok: false, message: "El nombre admite hasta 120 caracteres." };
  const currency = form.baseCurrency.trim().toUpperCase();
  if (!(SUPPORTED_CURRENCIES as readonly string[]).includes(currency)) {
    return { ok: false, message: "Elige una moneda base de la lista." };
  }
  return { ok: true, body: { name, base_currency: currency, is_demo: form.isDemo } };
}

/** Where AuthGate should send the user, or `null` to stay. */
export function onboardingRedirect(pathname: string, me: Me | null): string | null {
  if (!me) return null;
  if (!me.company && pathname !== ONBOARDING_PATH) return ONBOARDING_PATH;
  if (me.company && pathname === ONBOARDING_PATH) return "/";
  return null;
}

export function companyErrorMessage(detail: unknown): string {
  switch (detail) {
    case "company_name_taken":
      return "Ya existe una empresa con ese nombre. Elígela de la lista para unirte.";
    case "already_in_company":
      return "Tu usuario ya pertenece a una empresa.";
    case "unsupported_currency":
      return "Esa moneda no está en la tabla de cambio.";
    case "missing_user_email":
      return "Vuelve a iniciar sesión: falta tu correo.";
    default:
      return "No se pudo completar. Inténtalo de nuevo.";
  }
}
