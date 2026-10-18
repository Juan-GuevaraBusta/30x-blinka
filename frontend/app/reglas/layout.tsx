"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

import { isActiveReglasLink, REGLAS_NAV_LINKS } from "@/lib/reglas-nav";

function ReglasNavLinks() {
  const pathname = usePathname();
  return (
    <ul className="flex flex-row gap-1 overflow-x-auto md:flex-col md:gap-0.5 md:overflow-visible">
      {REGLAS_NAV_LINKS.map((link) => {
        const active = isActiveReglasLink(pathname ?? "/", link.href);
        return (
          <li key={link.href} className="shrink-0 md:shrink">
            <Link
              href={link.href}
              aria-current={active ? "page" : undefined}
              className={`block rounded-lg px-3 py-2 text-sm font-medium whitespace-nowrap transition-colors focus-ring ${
                active ? "bg-accent/10 text-ink" : "text-ink-muted hover:bg-paper hover:text-ink"
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

/** `/reglas` workspace shell (T7.5 §2): left-hand nav on desktop, stacked above content on mobile. */
export default function ReglasLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-6 md:flex-row md:gap-8">
      <nav
        aria-label="Reglas"
        className="shrink-0 border-b border-line pb-4 md:w-56 md:border-b-0 md:border-r md:border-line md:pb-0 md:pr-6"
      >
        <ReglasNavLinks />
      </nav>
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
