export type SettingsNavLink = { href: string; label: string };

/** Left-hand workspace navigation for `/ajustes` (T7.5 §2). Order matches the UI top-to-bottom. */
export const SETTINGS_NAV_LINKS: SettingsNavLink[] = [
  { href: "/reglas", label: "Reglas generales" },
  { href: "/ajustes/politica", label: "Política de aprobación" },
  { href: "/ajustes/proveedores", label: "Proveedores" },
  { href: "/ajustes/acuerdos", label: "Acuerdos" },
];

/** True when `pathname` is on the section rooted at `href` (exact match, or a sub-route). */
export function isActiveSettingsLink(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}
