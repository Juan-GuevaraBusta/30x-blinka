"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ChevronRight, FileSignature, Store, Truck } from "lucide-react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
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
      <div className="space-y-3" role="status">
        <p className="text-sm text-ink-muted">Cargando proveedores…</p>
        <div className="skeleton h-16" aria-hidden="true" />
        <div className="skeleton h-16" aria-hidden="true" />
      </div>
    );
  }

  const { vendors } = state;

  return (
    <div className="space-y-6">
      <PageHeader
        title="Proveedores"
        icon={Truck}
        description={<p>Proveedores permitidos. Abra uno para ver su calendario de pagos.</p>}
      />
      {vendors.length === 0 ? (
        <EmptyState
          icon={Store}
          title="Aún no hay proveedores."
          action={
            <ButtonLink href="/reglas/acuerdos/nuevo" icon={<FileSignature className="h-4 w-4" aria-hidden="true" />}>
              Crea el primero subiendo un acuerdo
            </ButtonLink>
          }
        />
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2">
          {vendors.map((vendor) => (
            <li key={vendor.name}>
              <Link
                href={`/reglas/proveedores/${encodeURIComponent(vendor.name)}`}
                className="group panel flex items-center gap-3 px-4 py-3.5 text-sm font-semibold text-ink transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-md focus-ring"
              >
                <span
                  className={`inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg ${
                    vendor.source === "agreement" ? "bg-brand-100 text-brand-700" : "bg-surface-sunken text-ink-muted"
                  }`}
                  aria-hidden="true"
                >
                  <Store className="h-5 w-5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate">{vendor.name}</span>
                  <Badge
                    tone={vendor.source === "agreement" ? "brand" : "neutral"}
                    size="sm"
                    className="mt-1 font-medium"
                  >
                    {vendorProvenanceLabel(vendor)}
                  </Badge>
                </span>
                <ChevronRight
                  className="h-4 w-4 shrink-0 text-ink-subtle transition-transform group-hover:translate-x-0.5 group-hover:text-brand-600"
                  aria-hidden="true"
                />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
