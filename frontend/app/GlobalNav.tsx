"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { roleLabel, setMe, useMe } from "@/lib/me";
import { isActiveNavLink, NAV_LINKS, visibleNavLinks } from "@/lib/nav";
import { clearStoredUserId, getStoredUserId } from "@/lib/session";

const RAIL_DISCLAIMER = "Esta mesa registra la decisión. No mueve dinero.";

function NavLinks({ orientation }: { orientation: "vertical" | "horizontal" }) {
  const pathname = usePathname();
  const me = useMe();
  const links = visibleNavLinks(NAV_LINKS, me?.member);
  const listClass =
    orientation === "vertical"
      ? "flex flex-col gap-0.5"
      : "flex flex-wrap gap-x-1 gap-y-1";

  return (
    <ul className={listClass}>
      {links.map((link) => {
        const active = isActiveNavLink(pathname ?? "/", link.href);
        return (
          <li key={link.href}>
            <Link
              href={link.href}
              aria-current={active ? "page" : undefined}
              className={`block rounded-lg px-3 py-2 text-sm font-medium transition-colors focus-ring ${
                active
                  ? "bg-accent/10 text-ink"
                  : "text-ink-muted hover:bg-paper hover:text-ink"
              }`}
            >
              {link.label}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function SignOutButton() {
  const pathname = usePathname();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const path = pathname ?? "/";
    setVisible(path !== "/entrar" && Boolean(getStoredUserId()));
  }, [pathname]);

  if (!visible) {
    return null;
  }
  return (
    <button
      type="button"
      className="mt-2 w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-ink-muted hover:bg-paper hover:text-ink focus-ring"
      onClick={() => {
        clearStoredUserId();
        setMe(null);
        window.location.href = "/entrar";
      }}
    >
      Salir
    </button>
  );
}

function CompanyBadge() {
  const me = useMe();
  if (!me?.company) return null;
  const role = roleLabel(me.member?.role);
  return (
    <p className="mt-1 text-xs text-ink-muted" aria-label="Empresa y rol">
      <span className="font-medium text-ink">{me.company.name}</span>
      {role ? ` · ${role}` : ""}
      {me.member?.is_approver ? " · aprobador" : ""}
    </p>
  );
}

export default function GlobalNav() {
  return (
    <>
      <header className="border-b border-line bg-surface md:hidden">
        <div className="px-4 py-3">
          <Link href="/" className="text-base font-semibold tracking-tight text-ink focus-ring">
            Blinka
          </Link>
          <p className="mt-0.5 text-xs text-ink-muted">Agente de pagos</p>
          <CompanyBadge />
        </div>
        <nav aria-label="Principal" className="overflow-x-auto border-t border-line px-2 py-2">
          <NavLinks orientation="horizontal" />
        </nav>
      </header>

      <aside
        className="hidden w-[var(--rail-width)] shrink-0 flex-col border-r border-line bg-surface md:flex"
        aria-label="Navegación principal"
      >
        <div className="px-5 py-6">
          <Link href="/" className="text-lg font-semibold tracking-tight text-ink focus-ring">
            Blinka
          </Link>
          <p className="mt-1 text-xs text-ink-muted">Agente de pagos</p>
          <CompanyBadge />
        </div>
        <nav className="flex-1 px-3">
          <NavLinks orientation="vertical" />
          <SignOutButton />
        </nav>
        <p className="border-t border-line px-5 py-4 text-xs leading-relaxed text-ink-muted">
          {RAIL_DISCLAIMER}
        </p>
      </aside>
    </>
  );
}
