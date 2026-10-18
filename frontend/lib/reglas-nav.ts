export type ReglasNavLink = { href: string; label: string };

/** Left-hand workspace navigation for `/reglas` (T7.5 §2). Order matches the UI top-to-bottom. */
export const REGLAS_NAV_LINKS: ReglasNavLink[] = [
  { href: "/reglas", label: "Reglas generales" },
  { href: "/reglas/politica", label: "Política de aprobación" },
  { href: "/reglas/proveedores", label: "Proveedores" },
  { href: "/reglas/acuerdos", label: "Acuerdos" },
];

/**
 * True when `pathname` is on the section rooted at `href` (exact match, or a
 * sub-route). `/reglas` itself ("Reglas generales") has no sub-routes of its
 * own -- its sub-paths (`/reglas/politica`, `/reglas/proveedores`,
 * `/reglas/acuerdos`) are the *other* sections, so it only matches exactly,
 * the same way `isActiveNavLink` special-cases `/` in `./nav`.
 */
export function isActiveReglasLink(pathname: string, href: string): boolean {
  if (href === "/reglas") return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}
