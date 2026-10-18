"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ArrowLeft, Bot, FileSignature, History, PowerOff, ShieldCheck } from "lucide-react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { buttonClass } from "@/components/ui/Button";
import { PageHeader } from "@/components/ui/PageHeader";
import { Section } from "@/components/ui/Section";
import { describeAgreement } from "@/lib/agreement-present";
import { AGREEMENT_KIND_LABELS, type AgreementHistory } from "@/lib/agreement-types";
import { apiFetch } from "@/lib/session";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; history: AgreementHistory };

async function loadHistory(vendorKey: string): Promise<LoadState> {
  try {
    const res = await apiFetch(`/api/agreements/${encodeURIComponent(vendorKey)}`, {
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

const STATUS_TONES: Record<string, BadgeTone> = {
  active: "pay",
  superseded: "info",
  inactive: "neutral",
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
      const res = await apiFetch(`/api/agreements/${encodeURIComponent(vendorKey)}/deactivate`, {
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
      <div className="space-y-3" role="status">
        <p className="text-sm text-ink-muted">Cargando acuerdo…</p>
        <div className="skeleton h-40" aria-hidden="true" />
      </div>
    );
  }

  if (state.status === "error") {
    return (
      <div className="space-y-4">
        <AlertPanel>{state.message}</AlertPanel>
        <Link href="/reglas/acuerdos" className={buttonClass("secondary", "sm")}>
          <ArrowLeft className="h-4 w-4" aria-hidden="true" />
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
        icon={FileSignature}
        description={
          <p>
            <Link
              href="/reglas/acuerdos"
              className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline focus-ring"
            >
              <ArrowLeft className="h-4 w-4" aria-hidden="true" />
              Acuerdos
            </Link>
          </p>
        }
      />

      {actionError ? <AlertPanel>{actionError}</AlertPanel> : null}

      {active ? (
        <Section
          title="Versión vigente"
          icon={ShieldCheck}
          action={
            <Badge tone="pay" icon={<ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />}>
              Vigente
            </Badge>
          }
        >
          <dl className="grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
            <div className="rounded-lg bg-surface-sunken px-3 py-2.5">
              <dt className="text-eyebrow uppercase text-ink-muted">Tipo</dt>
              <dd className="mt-1 font-semibold text-ink">{AGREEMENT_KIND_LABELS[active.terms.kind]}</dd>
            </div>
            <div className="rounded-lg bg-surface-sunken px-3 py-2.5">
              <dt className="text-eyebrow uppercase text-ink-muted">Versión</dt>
              <dd className="mt-1 font-semibold text-ink">v{active.version}</dd>
            </div>
            <div className="rounded-lg bg-surface-sunken px-3 py-2.5">
              <dt className="text-eyebrow uppercase text-ink-muted">Confirmado por</dt>
              <dd className="mt-1 font-semibold text-ink">{active.confirmed_by}</dd>
            </div>
          </dl>

          <div className="mt-4 flex gap-3 rounded-lg border border-brand-200 bg-brand-50 px-4 py-3">
            <Bot className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" aria-hidden="true" />
            <div>
              <p className="text-xs font-semibold text-brand-800">Cómo lo aplica el agente</p>
              <p className="mt-1 text-sm text-ink">{describeAgreement(active.terms)}</p>
            </div>
          </div>

          <button
            type="button"
            onClick={handleDeactivate}
            disabled={deactivating}
            className={buttonClass("secondary", "md", "mt-4 border-stop-200 text-stop-700 hover:border-stop-500 hover:bg-stop-50")}
          >
            <PowerOff className="h-4 w-4" aria-hidden="true" />
            {deactivating ? "Desactivando…" : "Desactivar acuerdo"}
          </button>
        </Section>
      ) : (
        <AlertPanel tone="neutral">Este proveedor no tiene una versión vigente.</AlertPanel>
      )}

      <Section title="Historial de versiones" icon={History}>
        <ol className="relative space-y-3 border-l-2 border-brand-100 pl-5">
          {history.versions
            .slice()
            .reverse()
            .map((version) => (
              <li
                key={version.version}
                className="relative flex flex-wrap items-center justify-between gap-2 rounded-lg border border-line bg-surface px-3 py-2.5 text-sm"
              >
                <span
                  className={`absolute -left-7 top-1/2 h-3 w-3 -translate-y-1/2 rounded-full ring-4 ring-surface ${
                    version.status === "active" ? "bg-pay-500" : "bg-brand-300"
                  }`}
                  aria-hidden="true"
                />
                <span className="font-mono font-semibold text-ink">v{version.version}</span>
                <Badge tone={STATUS_TONES[version.status] ?? "neutral"} size="sm">
                  {STATUS_LABELS[version.status] ?? version.status}
                </Badge>
                <span className="text-ink-muted">{version.confirmed_by}</span>
                <span className="text-ink-muted">{version.confirmed_at}</span>
              </li>
            ))}
        </ol>
      </Section>
    </div>
  );
}
