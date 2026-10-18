"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import type { AgreementListEntry } from "@/lib/agreement-types";
import { mergeVendorData, vendorProvenanceLabel, type EffectiveRulesResponse, type VendorSummary } from "@/lib/vendor-aggregate";
import { apiFetch } from "@/lib/session";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; vendors: VendorSummary[] };

async function loadVendors(): Promise<LoadState> {
  try {
    const [effectiveRes, agreementsRes] = await Promise.all([
      apiFetch("/api/rules/effective", { cache: "no-store" }),
      apiFetch("/api/agreements", { cache: "no-store" }),
    ]);
    if (!effectiveRes.ok) {
      return { status: "error", message: `No se pudieron cargar los proveedores (HTTP ${effectiveRes.status}).` };
    }
    if (!agreementsRes.ok) {
      return { status: "error", message: `No se pudieron cargar los acuerdos (HTTP ${agreementsRes.status}).` };
    }
    const effective = (await effectiveRes.json()) as EffectiveRulesResponse;
    const agreements = (await agreementsRes.json()) as AgreementListEntry[];
    return { status: "ready", vendors: mergeVendorData(effective, agreements) };
  } catch {
    return {
      status: "error",
      message: "No se pudo contactar con el servidor. Comprueba que el API esté en marcha.",
    };
  }
}

export default function ProveedoresScreen() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const next = await loadVendors();
      if (!cancelled) setState(next);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.status === "error") {
    return <AlertPanel>{state.message}</AlertPanel>;
  }

  if (state.status === "loading") {
    return (
      <p className="text-sm text-ink-muted" role="status">
        Cargando proveedores…
      </p>
    );
  }

  const { vendors } = state;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Proveedores"
        description={<p>Proveedores permitidos. Abra uno para ver su calendario de pagos.</p>}
      />
      {vendors.length === 0 ? (
        <p className="text-sm text-ink-muted">
          Aún no hay proveedores.{" "}
          <Link href="/reglas/acuerdos/nuevo" className="text-accent hover:underline focus-ring">
            Crea el primero subiendo un acuerdo
          </Link>
        </p>
      ) : (
        <ul className="space-y-2">
          {vendors.map((vendor) => (
            <li key={vendor.name}>
              <Link
                href={`/reglas/proveedores/${encodeURIComponent(vendor.name)}`}
                className="panel flex flex-wrap items-baseline justify-between gap-2 px-4 py-3 text-sm font-medium text-ink hover:bg-paper focus-ring"
              >
                <span>{vendor.name}</span>
                <span
                  className={`text-xs font-normal ${
                    vendor.source === "agreement" ? "text-accent" : "text-ink-muted"
                  }`}
                >
                  {vendorProvenanceLabel(vendor)}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
