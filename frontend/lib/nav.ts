export type NavLink = {
  href: string;
  label: string;
};

/** Order matches the global nav left to right (T6.7, D057). */
export const NAV_LINKS: NavLink[] = [
  { href: "/", label: "Inicio" },
  { href: "/reglas", label: "Reglas" },
  { href: "/decisiones", label: "Decisiones" },
  { href: "/aprobaciones", label: "Aprobaciones" },
  { href: "/metricas", label: "Métricas" },
  { href: "/subir", label: "Subir factura" },
];

/** True when `pathname` is on the section rooted at `href` (exact match, or a sub-route). */
export function isActiveNavLink(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}
