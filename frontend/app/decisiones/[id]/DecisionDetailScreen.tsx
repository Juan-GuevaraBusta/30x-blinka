"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AgentOperationTrail } from "@/components/decision/AgentOperationTrail";
import { AlertPanel } from "@/components/ui/AlertPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import { Section } from "@/components/ui/Section";
import type { DecisionRecord } from "@/lib/decision-types";
import { isValidDecisionId, severityLabel } from "@/lib/decision-present";
import type { ApprovalStatusBody } from "@/lib/approval-status-present";
import {
  approvalCountLabel,
  approversSummary,
  pendingChecksSentence,
  routeDisplayLabel,
} from "@/lib/approval-status-present";
import {
  DEFAULT_APPROVAL_AUTHOR,
  validateHumanDecisionInput,
} from "@/lib/approvals";
import type { RulesConfig } from "@/lib/rules-types";
import { apiFetch } from "@/lib/session";

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
  | {
      status: "ready";
      record: DecisionRecord;
      approval: ApprovalStatusBody | null;
      rules: RulesConfig | null;
    };

const ADD_VENDOR_WARNING =
  "Esta factura no se pagará. La próxima factura de este proveedor quedará pendiente de aprobación.";

/** Best-effort «x de N aprobaciones» status; a failure just omits the panel (T7.5 §2). */
async function loadApprovalStatus(id: string): Promise<ApprovalStatusBody | null> {
  try {
    const res = await apiFetch(`/api/decisions/${encodeURIComponent(id)}/approval`, {
      cache: "no-store",
    });
    if (!res.ok) return null;
    return (await res.json()) as ApprovalStatusBody;
  } catch {
    return null;
  }
}

async function loadRules(): Promise<RulesConfig | null> {
  try {
    const res = await apiFetch("/api/rules", { cache: "no-store" });
    if (!res.ok) return null;
    return (await res.json()) as RulesConfig;
  } catch {
    return null;
  }
}

function hasR01Failure(record: DecisionRecord): boolean {
  return record.checks.some((check) => check.rule === "R01" && check.result === "FALLA");
}

async function loadDecision(id: string): Promise<LoadState> {
  if (!isValidDecisionId(id)) {
    return { status: "not_found" };
  }
  try {
    const res = await apiFetch(`/api/decisions/${encodeURIComponent(id)}`, {
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
    const [approval, rules] = await Promise.all([loadApprovalStatus(id), loadRules()]);
    return { status: "ready", record, approval, rules };
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

function AddBeneficiaryPanel({ decisionId }: { decisionId: string }) {
  const [author, setAuthor] = useState(DEFAULT_APPROVAL_AUTHOR);
  const [reason, setReason] = useState("");
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit() {
    const validated = validateHumanDecisionInput(author, reason);
    if (!validated.ok) {
      setFieldError(validated.message);
      return;
    }
    setFieldError(null);
    setActionError(null);
    setSubmitting(true);
    try {
      const res = await apiFetch(
        `/api/decisions/${encodeURIComponent(decisionId)}/add-beneficiary`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(validated.body),
        },
      );
      if (!res.ok) {
        let detail = `No se pudo agregar el proveedor (HTTP ${res.status}).`;
        try {
          const body = (await res.json()) as { detail?: string };
          if (body.detail === "vendor_onboarding_disabled") {
            detail = "El alta auditada de proveedores no está habilitada en reglas.";
          } else if (body.detail === "r01_not_failed") {
            detail = "Solo aplica cuando R01 está en fallo.";
          } else if (body.detail === "already_allowed") {
            detail = "Ese beneficiario ya está en la lista permitida.";
          }
        } catch {
          /* keep generic */
        }
        setActionError(detail);
        return;
      }
      setSuccess(true);
    } catch {
      setActionError("No se pudo contactar con el servidor.");
    } finally {
      setSubmitting(false);
    }
  }

  if (success) {
    return (
      <p className="text-sm text-success" role="status">
        Proveedor agregado a la lista permitida. Esta ficha de decisión no cambia.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-sm text-ink-muted">{ADD_VENDOR_WARNING}</p>
      <label className="block text-sm">
        <span className="font-medium text-ink">Autor</span>
        <input
          className="mt-1 w-full rounded-md border border-line bg-surface px-3 py-2 text-sm focus-ring"
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          autoComplete="off"
        />
      </label>
      <label className="block text-sm">
        <span className="font-medium text-ink">Motivo (obligatorio)</span>
        <textarea
          className="mt-1 w-full rounded-md border border-line bg-surface px-3 py-2 text-sm focus-ring"
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
        />
      </label>
      {fieldError ? <p className="text-sm text-danger">{fieldError}</p> : null}
      {actionError ? <p className="text-sm text-danger">{actionError}</p> : null}
      <button
        type="button"
        className="rounded-md bg-accent px-4 py-2 text-sm font-medium text-surface hover:opacity-90 focus-ring disabled:opacity-50"
        disabled={submitting}
        onClick={() => void onSubmit()}
      >
        {submitting ? "Guardando…" : "Agregar a proveedores permitidos"}
      </button>
    </div>
  );
}

function RecordBody({
  record,
  approval,
  rules,
}: {
  record: DecisionRecord;
  approval: ApprovalStatusBody | null;
  rules: RulesConfig | null;
}) {
  const pendingSentence = approval ? pendingChecksSentence(approval, record.checks) : null;
  const showAddVendor =
    rules?.vendor_onboarding?.enabled === true && hasR01Failure(record);

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

      {showAddVendor ? (
        <Section title="Alta de proveedor">
          <AddBeneficiaryPanel decisionId={record.id} />
        </Section>
      ) : null}

      {approval ? (
        <Section title="Aprobaciones">
          <p className="text-sm font-medium text-ink">{approvalCountLabel(approval)}</p>
          <p className="text-sm text-ink-muted">{routeDisplayLabel(approval.route_id)}</p>
          <p className="text-sm text-ink-muted">{approversSummary(approval)}</p>
          {pendingSentence ? <p className="text-sm text-ink-muted">{pendingSentence}</p> : null}
        </Section>
      ) : null}

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

  return (
    <RecordBody record={state.record} approval={state.approval} rules={state.rules} />
  );
}
