export type NavLink = {
  href: string;
  label: string;
};

/** Order matches the global nav left to right (T6.7, D057). */
export const NAV_LINKS: NavLink[] = [
  { href: "/", label: "Inicio" },
  { href: "/reglas", label: "Reglas" },
  { href: "/decisiones", label: "Decisiones" },
  { href: "/bandeja", label: "Bandeja" },
  { href: "/aprobaciones", label: "Aprobaciones" },
  { href: "/subir", label: "Subir factura" },
];

/** True when `pathname` is on the section rooted at `href` (exact match, or a sub-route). */
export function isActiveNavLink(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

/** T9.8: «Aprobaciones» only for company approvers (hidden once we know the user is not one). */
export function visibleNavLinks(
  links: NavLink[],
  member: { is_approver: boolean } | null | undefined,
): NavLink[] {
  if (!member || member.is_approver) return links;
  return links.filter((link) => link.href !== "/aprobaciones");
}
