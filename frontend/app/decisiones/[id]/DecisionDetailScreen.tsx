"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AgentOperationTrail } from "@/components/decision/AgentOperationTrail";
import { AlertPanel } from "@/components/ui/AlertPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import { Section } from "@/components/ui/Section";
import type { DecisionRecord } from "@/lib/decision-types";
import { isValidDecisionId, severityLabel } from "@/lib/decision-present";

const I8_DISCLAIMER =
  "PAGAR es una decisión registrada. Esta pantalla no mueve dinero.";

const VERSIONS_NOTE =
  "Este registro conserva las versiones con las que se decidió. Cambiar reglas en /reglas no reescribe esta ficha.";

const MSG_NOT_FOUND = "No hay una decisión con ese identificador.";
const MSG_RATE_LIMITED =
  "Demasiadas solicitudes. Espera un momento y vuelve a abrir esta decisión.";

type LoadState =
  | { status: "loading" }
  | { status: "not_found" }
  | { status: "rate_limited" }
  | { status: "error"; message: string }
  | { status: "ready"; record: DecisionRecord };

async function loadDecision(id: string): Promise<LoadState> {
  if (!isValidDecisionId(id)) {
    return { status: "not_found" };
  }
  try {
    const res = await fetch(`/api/decisions/${encodeURIComponent(id)}`, {
      cache: "no-store",
    });
    if (res.status === 404) {
      return { status: "not_found" };
    }
    if (res.status === 429) {
      let detail: string | undefined;
      try {
        const body = (await res.json()) as { detail?: string };
        detail = body.detail;
      } catch {
        detail = undefined;
      }
      if (detail === "rate_limited") {
        return { status: "rate_limited" };
      }
      return { status: "rate_limited" };
    }
    if (!res.ok) {
      return {
        status: "error",
        message: `No se pudo cargar la decisión (HTTP ${res.status}).`,
      };
    }
    const record = (await res.json()) as DecisionRecord;
    return { status: "ready", record };
  } catch {
    return {
      status: "error",
      message: "No se pudo contactar con el servidor. Comprueba que el API esté en marcha.",
    };
  }
}

function decisionTone(decision: DecisionRecord["decision"]): string {
  if (decision === "PAGAR") return "text-success";
  if (decision === "FRENAR") return "text-danger";
  return "text-accent";
}

function FieldRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[minmax(0,11rem)_1fr] sm:gap-4">
      <dt className="text-sm font-medium text-ink-muted">{label}</dt>
      <dd className="text-sm text-ink break-words">{value}</dd>
    </div>
  );
}

function RecordBody({ record }: { record: DecisionRecord }) {
  return (
    <div className="space-y-8">
      <PageHeader
        title={`Decisión ${record.id}`}
        description={
          <>
            <p>
              <Link href="/reglas" className="text-accent hover:underline focus-ring">
                Reglas vigentes
              </Link>
              {" · "}
              Ficha de solo lectura. No se recalculan reglas ni se mueve dinero.
            </p>
          </>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2">
        <div className="panel px-4 py-4">
          <p className="text-xs text-ink-muted">Decisión registrada</p>
          <p className={`mt-1 text-2xl font-semibold ${decisionTone(record.decision)}`}>
            {record.decision}
          </p>
          <p className="mt-2 text-xs leading-relaxed text-ink-muted">{I8_DISCLAIMER}</p>
        </div>
        <div className="rounded-xl bg-ink px-4 py-4 text-surface">
          <p className="text-xs text-surface/70">Severidad (entero guardado)</p>
          <p className="mt-1 font-mono text-2xl tracking-tight">
            {record.severity} · {severityLabel(record.severity)}
          </p>
        </div>
      </div>

      <Section title="Historial de operaciones del agente">
        <AgentOperationTrail record={record} />
      </Section>

      <Section title="Identidad del registro">
        <dl className="space-y-3">
          <FieldRow label="Identificador" value={record.id} />
          <FieldRow label="Factura" value={record.invoice_id} />
          <FieldRow label="Recibida" value={record.received_at} />
          <FieldRow label="Decisión" value={record.decision} />
          <FieldRow
            label="Severidad"
            value={`${record.severity} · ${severityLabel(record.severity)}`}
          />
        </dl>
        <div className="mt-4 border-t border-line pt-4">
          <p className="text-sm font-medium text-ink">Versiones con las que se decidió</p>
          <dl className="mt-2 space-y-2">
            <FieldRow label="Reglas" value={record.versions.rules_version} />
            <FieldRow label="Extractor" value={record.versions.model_extractor} />
            <FieldRow label="Verificador" value={record.versions.model_verifier} />
            <FieldRow label="JEV" value={record.versions.jev} />
          </dl>
          <p className="mt-3 text-xs leading-relaxed text-ink-muted">{VERSIONS_NOTE}</p>
        </div>
      </Section>
    </div>
  );
}

export default function DecisionDetailScreen({ decisionId }: { decisionId: string }) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const next = await loadDecision(decisionId);
      if (!cancelled) setState(next);
    })();
    return () => {
      cancelled = true;
    };
  }, [decisionId]);

  if (state.status === "loading") {
    return (
      <p className="text-ink-muted" role="status">
        Cargando decisión…
      </p>
    );
  }

  if (state.status === "not_found") {
    return <AlertPanel>{MSG_NOT_FOUND}</AlertPanel>;
  }

  if (state.status === "rate_limited") {
    return <AlertPanel>{MSG_RATE_LIMITED}</AlertPanel>;
  }

  if (state.status === "error") {
    return <AlertPanel>{state.message}</AlertPanel>;
  }

  return <RecordBody record={state.record} />;
}
