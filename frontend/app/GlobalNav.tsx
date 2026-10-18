"use client";

import {
  CheckSquare,
  FileUp,
  Gavel,
  Home,
  Inbox,
  LogOut,
  ScrollText,
  type LucideIcon,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import { PulseDot } from "@/components/ui/Badge";
import { BrandMark } from "@/components/ui/BrandMark";
import { cn } from "@/lib/cn";
import { roleLabel, setMe, useMe } from "@/lib/me";
import { isActiveNavLink, NAV_LINKS, visibleNavLinks } from "@/lib/nav";
import { clearStoredUserId, getStoredUserId } from "@/lib/session";

const RAIL_DISCLAIMER = "Esta mesa registra la decisión. No mueve dinero.";

const NAV_ICONS: Record<string, LucideIcon> = {
  "/": Home,
  "/reglas": Gavel,
  "/decisiones": ScrollText,
  "/bandeja": Inbox,
  "/aprobaciones": CheckSquare,
  "/subir": FileUp,
};

function NavLinks({ orientation }: { orientation: "vertical" | "horizontal" }) {
  const pathname = usePathname();
  const me = useMe();
  const links = visibleNavLinks(NAV_LINKS, me?.member);
  const listClass = orientation === "vertical" ? "flex flex-col gap-1" : "flex gap-1";

  return (
    <ul className={listClass}>
      {links.map((link) => {
        const active = isActiveNavLink(pathname ?? "/", link.href);
        const Icon = NAV_ICONS[link.href] ?? Home;
        return (
          <li key={link.href}>
            <Link
              href={link.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "group relative flex items-center gap-3 whitespace-nowrap rounded-lg px-3 py-2 text-sm font-medium transition-all duration-150 focus-ring",
                active
                  ? "bg-white/10 text-white"
                  : "text-brand-100/80 hover:bg-white/5 hover:text-white",
              )}
            >
              {active && orientation === "vertical" ? (
                <span className="absolute -left-3 top-1/2 h-5 w-1 -translate-y-1/2 rounded-r-full bg-signal" aria-hidden="true" />
              ) : null}
              <Icon
                className={cn(
                  "h-4 w-4 shrink-0 transition-colors",
                  active ? "text-signal" : "text-brand-300 group-hover:text-white",
                )}
                aria-hidden="true"
              />
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
      className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm font-medium text-brand-100/80 transition-colors hover:bg-white/5 hover:text-white focus-ring"
      onClick={() => {
        clearStoredUserId();
        setMe(null);
        window.location.href = "/entrar";
      }}
    >
      <LogOut className="h-4 w-4 text-brand-300" aria-hidden="true" />
      Salir
    </button>
  );
}

function CompanyBadge() {
  const me = useMe();
  if (!me?.company) return null;
  const role = roleLabel(me.member?.role);
  const initials = me.company.name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase() ?? "")
    .join("");
  return (
    <div
      className="flex items-center gap-3 rounded-xl border border-night-line bg-night-soft px-3 py-2.5"
      aria-label="Empresa y rol"
    >
      <span
        className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-brand-400 to-brand-700 font-display text-sm font-bold text-white"
        aria-hidden="true"
      >
        {initials || "·"}
      </span>
      <div className="min-w-0">
        <p className="truncate text-sm font-semibold text-white">{me.company.name}</p>
        <div className="mt-1 flex flex-wrap gap-1">
          {role ? (
            <span className="rounded-full bg-white/10 px-2 py-0.5 text-2xs font-semibold text-brand-100">{role}</span>
          ) : null}
          {me.member?.is_approver ? (
            <span className="inline-flex items-center gap-1 rounded-full bg-signal/15 px-2 py-0.5 text-2xs font-semibold text-signal">
              <ShieldCheck className="h-3 w-3" aria-hidden="true" />
              aprobador
            </span>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function Wordmark() {
  return (
    <Link href="/" className="flex items-center gap-3 rounded-lg focus-ring">
      <BrandMark />
      <span>
        <span className="block font-display text-lg font-bold leading-none tracking-tight text-white">Tachyon</span>
        <span className="mt-1 flex items-center gap-1.5 text-xs text-brand-200">
          <PulseDot tone="signal" />
          Pagos a proveedores
        </span>
      </span>
    </Link>
  );
}

export default function GlobalNav() {
  const pathname = usePathname();
  // The sign-in screen is a full-bleed hero with its own branding.
  if (pathname === "/entrar") return null;

  return (
    <>
      <header className="sticky top-0 z-30 bg-night text-white shadow-md md:hidden">
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <Wordmark />
        </div>
        <div className="px-4 pb-3">
          <CompanyBadge />
        </div>
        <nav aria-label="Principal" className="overflow-x-auto border-t border-night-line px-2 py-2">
          <NavLinks orientation="horizontal" />
        </nav>
      </header>

      <aside
        className="sticky top-0 hidden h-screen w-[var(--rail-width)] shrink-0 flex-col overflow-y-auto bg-night text-white md:flex"
        aria-label="Navegación principal"
      >
        <div className="pointer-events-none absolute inset-x-0 top-0 h-48 bg-grid-night opacity-30" aria-hidden="true" />
        <div className="relative space-y-5 px-5 pb-5 pt-6">
          <Wordmark />
          <CompanyBadge />
        </div>
        <nav className="relative flex-1 px-3">
          <p className="px-3 pb-2 text-eyebrow uppercase text-brand-300">Operación</p>
          <NavLinks orientation="vertical" />
          <div className="mt-4 border-t border-night-line pt-3">
            <SignOutButton />
          </div>
        </nav>
        <p className="relative m-3 rounded-lg border border-night-line bg-night-soft px-4 py-3 text-xs leading-relaxed text-brand-100">
          {RAIL_DISCLAIMER}
        </p>
      </aside>
    </>
  );
}
