"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import { Section } from "@/components/ui/Section";
import { describeAgreement } from "@/lib/agreement-present";
import { AGREEMENT_KIND_LABELS, type AgreementHistory } from "@/lib/agreement-types";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; history: AgreementHistory };

async function loadHistory(vendorKey: string): Promise<LoadState> {
  try {
    const res = await fetch(`/api/agreements/${encodeURIComponent(vendorKey)}`, {
      cache: "no-store",
    });
    if (res.status === 404) {
      return { status: "error", message: "No hay acuerdo confirmado para este proveedor." };
    }
    if (!res.ok) {
      return { status: "error", message: `No se pudo cargar el acuerdo (HTTP ${res.status}).` };
    }
    const history = (await res.json()) as AgreementHistory;
    return { status: "ready", history };
  } catch {
    return {
      status: "error",
      message: "No se pudo contactar con el servidor. Comprueba que el API esté en marcha.",
    };
  }
}

const STATUS_LABELS: Record<string, string> = {
  active: "Vigente",
  superseded: "Reemplazada",
  inactive: "Desactivada",
};

export default function AcuerdoDetailScreen({ vendorKeyParam }: { vendorKeyParam: string }) {
  const vendorKey = decodeURIComponent(vendorKeyParam);
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [deactivating, setDeactivating] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const next = await loadHistory(vendorKey);
      if (!cancelled) setState(next);
    })();
    return () => {
      cancelled = true;
    };
  }, [vendorKey]);

  const handleDeactivate = async () => {
    setActionError(null);
    setDeactivating(true);
    try {
      const author = window.prompt("Correo de quien desactiva este acuerdo:");
      if (!author) {
        setDeactivating(false);
        return;
      }
      const res = await fetch(`/api/agreements/${encodeURIComponent(vendorKey)}/deactivate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ author }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: "error" }));
        setActionError(`No se pudo desactivar (${res.status}): ${body.detail ?? "error"}`);
        return;
      }
      setState(await loadHistory(vendorKey));
    } catch {
      setActionError("No se pudo contactar con el servidor.");
    } finally {
      setDeactivating(false);
    }
  };

  if (state.status === "loading") {
    return (
      <p className="text-sm text-ink-muted" role="status">
        Cargando acuerdo…
      </p>
    );
  }

  if (state.status === "error") {
    return (
      <div className="space-y-4">
        <AlertPanel>{state.message}</AlertPanel>
        <Link href="/reglas/acuerdos" className="text-sm text-accent hover:underline focus-ring">
          Volver a acuerdos
        </Link>
      </div>
    );
  }

  const { history } = state;
  const { active } = history;

  return (
    <div className="space-y-6">
      <PageHeader
        title={active?.terms.vendor_name ?? vendorKey}
        description={
          <p>
            <Link href="/reglas/acuerdos" className="text-accent hover:underline focus-ring">
              Acuerdos
            </Link>
          </p>
        }
      />

      {actionError ? <AlertPanel>{actionError}</AlertPanel> : null}

      {active ? (
        <Section title="Versión vigente">
          <dl className="grid grid-cols-2 gap-2 text-sm sm:grid-cols-3">
            <div>
              <dt className="text-ink-muted">Tipo</dt>
              <dd className="font-medium text-ink">{AGREEMENT_KIND_LABELS[active.terms.kind]}</dd>
            </div>
            <div>
              <dt className="text-ink-muted">Versión</dt>
              <dd className="font-medium text-ink">v{active.version}</dd>
            </div>
            <div>
              <dt className="text-ink-muted">Confirmado por</dt>
              <dd className="font-medium text-ink">{active.confirmed_by}</dd>
            </div>
          </dl>

          <div className="mt-4 rounded-md border border-line/70 bg-paper px-3 py-2">
            <p className="text-xs font-medium text-ink-muted">Cómo lo aplica el agente</p>
            <p className="mt-1 text-sm text-ink">{describeAgreement(active.terms)}</p>
          </div>

          <button
            type="button"
            onClick={handleDeactivate}
            disabled={deactivating}
            className="mt-4 rounded-md border border-danger/40 px-3 py-1.5 text-sm font-medium text-danger hover:bg-danger/10 focus-ring disabled:opacity-50"
          >
            {deactivating ? "Desactivando…" : "Desactivar acuerdo"}
          </button>
        </Section>
      ) : (
        <AlertPanel tone="neutral">Este proveedor no tiene una versión vigente.</AlertPanel>
      )}

      <Section title="Historial de versiones">
        <ul className="space-y-2">
          {history.versions
            .slice()
            .reverse()
            .map((version) => (
              <li
                key={version.version}
                className="flex flex-wrap items-baseline justify-between gap-2 rounded-md border border-line/70 px-3 py-2 text-sm"
              >
                <span className="font-mono text-ink">v{version.version}</span>
                <span className="text-ink-muted">{STATUS_LABELS[version.status] ?? version.status}</span>
                <span className="text-ink-muted">{version.confirmed_by}</span>
                <span className="text-ink-muted">{version.confirmed_at}</span>
              </li>
            ))}
        </ul>
      </Section>
    </div>
  );
}
