"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { isActiveNavLink, NAV_LINKS } from "@/lib/nav";

const BRAND = "Agente de pagos · Hackathon Blinka";

export default function GlobalNav() {
  const pathname = usePathname();

  return (
    <header className="border-b border-line bg-surface">
      <nav
        aria-label="Principal"
        className="mx-auto flex max-w-4xl flex-wrap items-center gap-x-6 gap-y-3 px-4 py-4 sm:px-6"
      >
        <Link
          href="/"
          className="font-display shrink-0 text-base text-ink focus:outline-none focus:ring-2 focus:ring-accent/40"
        >
          {BRAND}
        </Link>
        <ul className="flex flex-wrap gap-x-4 gap-y-2 text-sm">
          {NAV_LINKS.map((link) => {
            const active = isActiveNavLink(pathname ?? "/", link.href);
            return (
              <li key={link.href}>
                <Link
                  href={link.href}
                  aria-current={active ? "page" : undefined}
                  className={`rounded-md px-1 py-0.5 font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-accent/30 ${
                    active ? "text-ink underline underline-offset-4" : "text-ink-muted hover:text-ink"
                  }`}
                >
                  {link.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </header>
  );
}
