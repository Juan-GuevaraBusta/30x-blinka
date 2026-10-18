import Link from "next/link";

import { PageHeader } from "@/components/ui/PageHeader";
import { SETTINGS_NAV_LINKS } from "@/lib/ajustes-nav";

export default function AjustesIndexPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Ajustes"
        description={<p>Elija una sección para configurar el espacio de trabajo.</p>}
      />
      <ul className="space-y-2">
        {SETTINGS_NAV_LINKS.map((link) => (
          <li key={link.href}>
            <Link
              href={link.href}
              className="panel block px-4 py-3 text-sm font-medium text-ink hover:bg-paper focus-ring"
            >
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}
