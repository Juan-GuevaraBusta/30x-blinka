"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { PageHeader } from "@/components/ui/PageHeader";

type RulesDocument = { allowed_beneficiaries?: unknown };

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}

export default function ProveedoresScreen() {
  const [vendors, setVendors] = useState<string[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/rules", { cache: "no-store" });
        if (!res.ok) {
          throw new Error(`No se pudieron cargar los proveedores (HTTP ${res.status}).`);
        }
        const document = (await res.json()) as RulesDocument;
        if (!cancelled) {
          setVendors(isStringArray(document.allowed_beneficiaries) ? document.allowed_beneficiaries : []);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : "Error al cargar proveedores.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loadError) {
    return <AlertPanel>{loadError}</AlertPanel>;
  }

  if (vendors === null) {
    return (
      <p className="text-sm text-ink-muted" role="status">
        Cargando proveedores…
      </p>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Proveedores"
        description={<p>Proveedores permitidos. Abra uno para ver su calendario de pagos.</p>}
      />
      {vendors.length === 0 ? (
        <p className="text-sm text-ink-muted">No hay proveedores permitidos configurados.</p>
      ) : (
        <ul className="space-y-2">
          {vendors.map((name) => (
            <li key={name}>
              <Link
                href={`/ajustes/proveedores/${encodeURIComponent(name)}`}
                className="panel block px-4 py-3 text-sm font-medium text-ink hover:bg-paper focus-ring"
              >
                {name}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
