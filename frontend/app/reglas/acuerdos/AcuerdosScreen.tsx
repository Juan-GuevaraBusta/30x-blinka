"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AlertPanel } from "@/components/ui/AlertPanel";
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
        description={
          <p>
            Registro estructurado de acuerdos por proveedor. La IA solo propone. Nada se aplica
            hasta que usted confirme.
          </p>
        }
      >
        <Link
          href="/reglas/acuerdos/nuevo"
          className="inline-flex items-center rounded-lg border border-line bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 focus-ring"
        >
          Nuevo acuerdo
        </Link>
      </PageHeader>

      {state.status === "loading" ? (
        <p className="text-sm text-ink-muted" role="status">
          Cargando acuerdos…
        </p>
      ) : state.status === "error" ? (
        <AlertPanel>{state.message}</AlertPanel>
      ) : state.entries.length === 0 ? (
        <p className="text-sm text-ink-muted">
          No hay acuerdos confirmados todavía.{" "}
          <Link href="/reglas/acuerdos/nuevo" className="text-accent hover:underline focus-ring">
            Crear el primer acuerdo
          </Link>
        </p>
      ) : (
        <ul className="space-y-2">
          {state.entries.map((entry) => (
            <li key={entry.vendor_key}>
              <Link
                href={`/reglas/acuerdos/${encodeURIComponent(entry.vendor_key)}`}
                className="panel flex flex-wrap items-baseline justify-between gap-2 px-4 py-3 text-sm hover:bg-paper focus-ring"
              >
                <span className="font-medium text-ink">{entry.vendor_name}</span>
                <span className="text-ink-muted">{AGREEMENT_KIND_LABELS[entry.kind]}</span>
                <span className="text-ink-muted">
                  {entry.valid_from} – {entry.valid_to ?? "sin fin"}
                </span>
                <span className="text-xs text-ink-muted">v{entry.version}</span>
                <span className="text-xs text-ink-muted">Confirmado por {entry.confirmed_by}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
