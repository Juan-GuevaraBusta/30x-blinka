"use client";

import { usePathname } from "next/navigation";

import { Tabs } from "@/components/ui/Tabs";
import { isActiveReglasLink, REGLAS_NAV_LINKS } from "@/lib/reglas-nav";

function ReglasNavLinks() {
  const pathname = usePathname() ?? "/";
  const active = REGLAS_NAV_LINKS.find((link) => isActiveReglasLink(pathname, link.href));
  return (
    <Tabs
      label="Reglas"
      activeKey={active?.href ?? ""}
      items={REGLAS_NAV_LINKS.map((link) => ({ key: link.href, label: link.label, href: link.href }))}
    />
  );
}

/** `/reglas` workspace shell (T7.5 §2): pill sub-navigation above the section content. */
export default function ReglasLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-6">
      <ReglasNavLinks />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}
