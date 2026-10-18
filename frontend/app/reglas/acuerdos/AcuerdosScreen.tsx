"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { CalendarRange, ChevronRight, FilePlus2, FileSignature, UserCheck } from "lucide-react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { Badge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { AGREEMENT_KIND_LABELS, type AgreementListEntry } from "@/lib/agreement-types";
import { apiFetch } from "@/lib/session";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; entries: AgreementListEntry[] };

async function loadAgreements(): Promise<LoadState> {
  try {
    const res = await apiFetch("/api/agreements", { cache: "no-store" });
    if (!res.ok) {
      return { status: "error", message: `No se pudieron cargar los acuerdos (HTTP ${res.status}).` };
    }
    const entries = (await res.json()) as AgreementListEntry[];
    return { status: "ready", entries };
  } catch {
    return {
      status: "error",
      message: "No se pudo contactar con el servidor. Comprueba que el API esté en marcha.",
    };
  }
}

export default function AcuerdosScreen() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const next = await loadAgreements();
      if (!cancelled) setState(next);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Acuerdos"
        icon={FileSignature}
        description={
          <p>
            Registro estructurado de acuerdos por proveedor. La IA solo propone. Nada se aplica
            hasta que usted confirme.
          </p>
        }
      >
        <ButtonLink href="/reglas/acuerdos/nuevo" icon={<FilePlus2 className="h-4 w-4" aria-hidden="true" />}>
          Nuevo acuerdo
        </ButtonLink>
      </PageHeader>

      {state.status === "loading" ? (
        <div className="space-y-3" role="status">
          <p className="text-sm text-ink-muted">Cargando acuerdos…</p>
          <div className="skeleton h-20" aria-hidden="true" />
          <div className="skeleton h-20" aria-hidden="true" />
        </div>
      ) : state.status === "error" ? (
        <AlertPanel>{state.message}</AlertPanel>
      ) : state.entries.length === 0 ? (
        <EmptyState
          icon={FileSignature}
          title="No hay acuerdos confirmados todavía."
          action={
            <ButtonLink href="/reglas/acuerdos/nuevo" icon={<FilePlus2 className="h-4 w-4" aria-hidden="true" />}>
              Crear el primer acuerdo
            </ButtonLink>
          }
        />
      ) : (
        <ul className="space-y-3">
          {state.entries.map((entry) => (
            <li key={entry.vendor_key}>
              <Link
                href={`/reglas/acuerdos/${encodeURIComponent(entry.vendor_key)}`}
                className="group panel flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-4 text-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-md focus-ring"
              >
                <span
                  className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700"
                  aria-hidden="true"
                >
                  <FileSignature className="h-5 w-5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block font-semibold text-ink">{entry.vendor_name}</span>
                  <span className="mt-1 flex flex-wrap items-center gap-2">
                    <Badge tone="info" size="sm">
                      {AGREEMENT_KIND_LABELS[entry.kind]}
                    </Badge>
                    <Badge tone="neutral" size="sm" className="font-mono">
                      v{entry.version}
                    </Badge>
                  </span>
                </span>
                <span className="inline-flex items-center gap-1.5 text-ink-muted">
                  <CalendarRange className="h-4 w-4 text-brand-500" aria-hidden="true" />
                  {entry.valid_from} – {entry.valid_to ?? "sin fin"}
                </span>
                <span className="inline-flex items-center gap-1.5 text-xs text-ink-muted">
                  <UserCheck className="h-4 w-4 text-pay-600" aria-hidden="true" />
                  Confirmado por {entry.confirmed_by}
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
