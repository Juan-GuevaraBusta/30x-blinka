"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ArrowLeft, Fingerprint, Gauge, ScrollText, UserPlus, Users, Workflow } from "lucide-react";

import { AgentOperationTrail } from "@/components/decision/AgentOperationTrail";
import { AlertPanel } from "@/components/ui/AlertPanel";
import { DECISION_META } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { Field, Input, Textarea } from "@/components/ui/Field";
import { PageHeader } from "@/components/ui/PageHeader";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { Section } from "@/components/ui/Section";
import { cn } from "@/lib/cn";
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

const HERO_TONES = {
  pay: "border-pay-200 bg-gradient-to-br from-pay-50 to-surface",
  stop: "border-stop-200 bg-gradient-to-br from-stop-50 to-surface",
  escalate: "border-escalate-200 bg-gradient-to-br from-escalate-50 to-surface",
} as const;

const HERO_TEXT = { pay: "text-pay-800", stop: "text-stop-800", escalate: "text-escalate-800" } as const;
const HERO_ICON = { pay: "bg-pay-600", stop: "bg-stop-600", escalate: "bg-escalate-500" } as const;

function HeroIcon({ decision }: { decision: DecisionRecord["decision"] }) {
  const meta = DECISION_META[decision];
  const Icon = meta.icon;
  return (
    <span
      className={cn(
        "inline-flex h-12 w-12 items-center justify-center rounded-xl text-white shadow-md",
        HERO_ICON[meta.tone as keyof typeof HERO_ICON],
      )}
      aria-hidden="true"
    >
      <Icon className="h-6 w-6" />
    </span>
  );
}

const SEVERITY_BAR = ["bg-pay-500", "bg-escalate-500", "bg-stop-500"] as const;

function FieldRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[minmax(0,11rem)_1fr] sm:gap-4">
      <dt className="text-sm font-medium text-ink-muted">{label}</dt>
      <dd className="break-words font-mono text-sm text-ink">{value}</dd>
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
      <AlertPanel tone="success">
        Proveedor agregado a la lista permitida. Esta ficha de decisión no cambia.
      </AlertPanel>
    );
  }

  return (
    <div className="space-y-3">
      <AlertPanel tone="warning">{ADD_VENDOR_WARNING}</AlertPanel>
      <Field label="Autor" htmlFor="add-vendor-author">
        <Input
          id="add-vendor-author"
          value={author}
          onChange={(e) => setAuthor(e.target.value)}
          autoComplete="off"
        />
      </Field>
      <Field label="Motivo (obligatorio)" htmlFor="add-vendor-reason">
        <Textarea id="add-vendor-reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} />
      </Field>
      {fieldError ? <p className="text-sm font-medium text-stop-700">{fieldError}</p> : null}
      {actionError ? <p className="text-sm font-medium text-stop-700">{actionError}</p> : null}
      <Button
        disabled={submitting}
        onClick={() => void onSubmit()}
        icon={<UserPlus className="h-4 w-4" aria-hidden="true" />}
      >
        {submitting ? "Guardando…" : "Agregar a proveedores permitidos"}
      </Button>
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
        icon={ScrollText}
        description={
          <>
            <p>
              <Link
                href="/reglas"
                className="font-semibold text-brand-700 hover:underline focus-ring"
              >
                Reglas vigentes
              </Link>
              {" · "}
              Ficha de solo lectura. No se recalculan reglas ni se mueve dinero.
            </p>
          </>
        }
        actions={
          <Link
            href="/decisiones"
            className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-semibold text-ink-muted transition-colors hover:bg-brand-50 hover:text-brand-700 focus-ring"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Decisiones
          </Link>
        }
      />

      <div className="grid gap-4 lg:grid-cols-3">
        <div
          className={cn(
            "relative overflow-hidden rounded-xl border p-5 shadow-sm lg:col-span-2 animate-fade-up",
            HERO_TONES[DECISION_META[record.decision].tone as keyof typeof HERO_TONES],
          )}
        >
          <p className="text-eyebrow uppercase text-ink-muted">Decisión registrada</p>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <HeroIcon decision={record.decision} />
            <span className={cn("font-display text-display", HERO_TEXT[DECISION_META[record.decision].tone as keyof typeof HERO_TEXT])}>
              {record.decision}
            </span>
          </div>
          <p className="mt-3 max-w-prose text-sm leading-relaxed text-ink">{record.summary}</p>
          <p className="mt-3 text-xs leading-relaxed text-ink-muted">{I8_DISCLAIMER}</p>
        </div>
        <Card tone="night" className="bg-grid-night animate-fade-up">
          <p className="flex items-center gap-2 text-xs text-white/70">
            <Gauge className="h-4 w-4 text-signal" aria-hidden="true" />
            Severidad (entero guardado)
          </p>
          <p className="mt-3 font-mono text-2xl tracking-tight text-white">
            {record.severity} · {severityLabel(record.severity)}
          </p>
          <div className="mt-4 flex gap-1.5" aria-hidden="true">
            {SEVERITY_BAR.map((bar, i) => (
              <span
                key={bar}
                className={cn("h-1.5 flex-1 rounded-full", i <= record.severity ? bar : "bg-night-line")}
              />
            ))}
          </div>
        </Card>
      </div>

      {showAddVendor ? (
        <Section title="Alta de proveedor" icon={UserPlus}>
          <AddBeneficiaryPanel decisionId={record.id} />
        </Section>
      ) : null}

      {approval ? (
        <Section title="Aprobaciones" icon={Users}>
          <div className="space-y-2">
            <p className="text-sm font-semibold text-ink">{approvalCountLabel(approval)}</p>
            <ProgressBar
              value={Math.min(approval.collected, approval.required)}
              max={approval.required}
              label={approvalCountLabel(approval)}
              tone={approval.collected >= approval.required ? "pay" : "brand"}
            />
          </div>
          <p className="text-sm text-ink-muted">{routeDisplayLabel(approval.route_id)}</p>
          <p className="text-sm text-ink-muted">{approversSummary(approval)}</p>
          {pendingSentence ? <p className="text-sm text-ink-muted">{pendingSentence}</p> : null}
        </Section>
      ) : null}

      <Section title="Historial de operaciones del agente" icon={Workflow}>
        <AgentOperationTrail record={record} />
      </Section>

      <Section title="Identidad del registro" icon={Fingerprint}>
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
          <p className="text-sm font-semibold text-ink">Versiones con las que se decidió</p>
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
      <div className="space-y-4" role="status">
        <p className="text-sm text-ink-muted">Cargando decisión…</p>
        <div className="skeleton h-10 w-2/3" aria-hidden="true" />
        <div className="grid gap-4 lg:grid-cols-3" aria-hidden="true">
          <div className="skeleton h-40 lg:col-span-2" />
          <div className="skeleton h-40" />
        </div>
      </div>
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
