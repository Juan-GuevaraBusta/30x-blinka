"use client";

import { useCallback, useEffect, useState } from "react";

import { CheckCircle2, Inbox, ShieldCheck, Users, XCircle } from "lucide-react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { Badge, DecisionBadge } from "@/components/ui/Badge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { Field, Input, Textarea } from "@/components/ui/Field";
import { PageHeader } from "@/components/ui/PageHeader";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatCard } from "@/components/ui/StatCard";
import { cn } from "@/lib/cn";
import type { DecisionRecord, HumanEvent } from "@/lib/decision-types";
import { formatNullable } from "@/lib/decision-present";
import {
  DEFAULT_APPROVAL_AUTHOR,
  humanActionHttpErrorMessage,
  mergeHumanActionSuccess,
  partitionEscalarQueue,
  parseErrorDetail,
  validateHumanDecisionInput,
} from "@/lib/approvals";
import type { ApprovalStatusBody } from "@/lib/approval-status-present";
import { approvalCountLabel, routeDisplayLabel } from "@/lib/approval-status-present";
import { apiFetch, getStoredUserEmail } from "@/lib/session";

const I8_NOTE =
  "Aprobar o rechazar registra un evento humano. No se mueve dinero; la decisión del agente sigue siendo ESCALAR.";

const QUEUE_URL = "/api/decisions?decision=ESCALAR";

type CardDraft = {
  author: string;
  reason: string;
  fieldError: string | null;
  actionError: string | null;
  submitting: "approve" | "reject" | null;
};

function emptyDraft(): CardDraft {
  return {
    // T9.8: the signed-in approver by default; the API checks it is a company approver.
    author: getStoredUserEmail() ?? DEFAULT_APPROVAL_AUTHOR,
    reason: "",
    fieldError: null,
    actionError: null,
    submitting: null,
  };
}

function formatAmount(record: DecisionRecord): string {
  const amount = record.extracted?.amount;
  const currency = record.extracted?.currency?.trim();
  if (amount === null || amount === undefined) {
    return formatNullable(null);
  }
  const base = formatNullable(amount);
  if (!currency) return base;
  return `${base} ${currency}`;
}

function actionLabel(action: HumanEvent["action"]): string {
  if (action === "aprobada_humano") return "Aprobada por humano";
  return "Rechazada por humano";
}

function formatEventAt(at: string): string {
  const parsed = new Date(at);
  if (Number.isNaN(parsed.getTime())) return at;
  return parsed.toLocaleString("es-ES", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

function FieldRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[minmax(0,10rem)_1fr] sm:gap-3">
      <dt className="text-sm font-medium text-ink-muted">{label}</dt>
      <dd className="break-words text-sm font-medium text-ink">{value}</dd>
    </div>
  );
}

function HumanEventsList({ events }: { events: HumanEvent[] }) {
  return (
    <ul className="mt-4 space-y-3 border-t border-line/70 pt-4">
      {events.map((event, index) => (
        <li
          key={`${event.at}-${event.author}-${index}`}
          className={cn(
            "rounded-lg border px-3 py-2 text-sm text-ink",
            event.action === "aprobada_humano" ? "border-pay-200 bg-pay-50" : "border-stop-200 bg-stop-50",
          )}
        >
          <p
            className={cn(
              "inline-flex items-center gap-1.5 font-semibold",
              event.action === "aprobada_humano" ? "text-pay-800" : "text-stop-800",
            )}
          >
            {event.action === "aprobada_humano" ? (
              <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
            ) : (
              <XCircle className="h-4 w-4" aria-hidden="true" />
            )}
            {actionLabel(event.action)}
          </p>
          <p className="mt-1 text-ink-muted">
            {event.author} · {formatEventAt(event.at)}
          </p>
          <p className="mt-2 text-ink">{event.reason}</p>
        </li>
      ))}
    </ul>
  );
}

/** Per-row «x de N aprobaciones» + ruta, fetched from `GET /decisions/{id}/approval` (T7.5 §2). */
function ApprovalStatusLine({ decisionId }: { decisionId: string }) {
  const [status, setStatus] = useState<ApprovalStatusBody | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await apiFetch(`/api/decisions/${encodeURIComponent(decisionId)}/approval`, {
          cache: "no-store",
        });
        if (!res.ok) {
          if (!cancelled) setFailed(true);
          return;
        }
        const body = (await res.json()) as ApprovalStatusBody;
        if (!cancelled) setStatus(body);
      } catch {
        if (!cancelled) setFailed(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [decisionId]);

  if (failed) {
    return <p className="mt-1 text-xs text-ink-muted">No se pudo cargar el estado de aprobación.</p>;
  }
  if (!status) {
    return null;
  }
  return (
    <div className="mt-3 rounded-lg border border-brand-100 bg-brand-50/60 p-3">
      <p className="text-sm font-semibold text-ink">
        {approvalCountLabel(status)} · <span className="font-medium text-ink-muted">{routeDisplayLabel(status.route_id)}</span>
      </p>
      <ProgressBar
        className="mt-2"
        value={Math.min(status.collected, status.required)}
        max={status.required}
        label={approvalCountLabel(status)}
        tone={status.collected >= status.required ? "pay" : "brand"}
      />
    </div>
  );
}

function DecisionCard({
  record,
  pending,
  draft,
  onDraftChange,
  onApprove,
  onReject,
}: {
  record: DecisionRecord;
  pending: boolean;
  draft: CardDraft;
  onDraftChange: (patch: Partial<CardDraft>) => void;
  onApprove: () => void;
  onReject: () => void;
}) {
  const beneficiary = formatNullable(record.extracted?.beneficiary);

  return (
    <article className="panel relative overflow-hidden p-5 sm:p-6 animate-fade-up">
      <span className="absolute inset-y-0 left-0 w-1 bg-escalate-500" aria-hidden="true" />
      <header className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="font-mono text-h2 text-ink">{record.invoice_id}</h2>
        <span className="inline-flex items-center gap-2">
          <DecisionBadge decision="ESCALAR" />
          <Badge tone="neutral" size="sm">
            ESCALAR · severidad {record.severity}
          </Badge>
        </span>
      </header>
      <p className="mt-1 font-mono text-xs text-ink-subtle">ID {record.id}</p>
      <ApprovalStatusLine decisionId={record.id} />
      <p className="mt-4 text-base leading-relaxed text-ink">{record.summary}</p>

      <dl className="mt-4 space-y-2 rounded-lg bg-surface-sunken p-3">
        <FieldRow label="Beneficiario" value={beneficiary} />
        <FieldRow label="Monto" value={formatAmount(record)} />
        <FieldRow label="Siguiente paso" value={formatNullable(record.next_step)} />
      </dl>

      {record.human_events.length > 0 ? (
        <HumanEventsList events={record.human_events} />
      ) : null}

      {pending ? (
        <form
          className="mt-5 space-y-4 border-t border-line/70 pt-5"
          onSubmit={(e) => e.preventDefault()}
        >
          <Field label="Autor" htmlFor={`author-${record.id}`}>
            <Input
              id={`author-${record.id}`}
              type="email"
              autoComplete="email"
              value={draft.author}
              disabled={draft.submitting !== null}
              onChange={(e) =>
                onDraftChange({ author: e.target.value, fieldError: null, actionError: null })
              }
            />
          </Field>
          <Field label="Motivo" htmlFor={`reason-${record.id}`}>
            <Textarea
              id={`reason-${record.id}`}
              rows={3}
              value={draft.reason}
              disabled={draft.submitting !== null}
              onChange={(e) =>
                onDraftChange({ reason: e.target.value, fieldError: null, actionError: null })
              }
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                }
              }}
              placeholder="Escriba el motivo de la aprobación o del rechazo"
            />
          </Field>

          {draft.fieldError ? (
            <p className="text-sm font-medium text-stop-700" role="alert">{draft.fieldError}</p>
          ) : null}
          {draft.actionError ? (
            <p className="text-sm font-medium text-stop-700" role="alert">{draft.actionError}</p>
          ) : null}

          <div className="flex flex-wrap gap-3">
            <Button
              variant="success"
              disabled={draft.submitting !== null}
              onClick={onApprove}
              icon={<CheckCircle2 className="h-4 w-4" aria-hidden="true" />}
            >
              {draft.submitting === "approve" ? "Registrando…" : "Aprobar"}
            </Button>
            <Button
              variant="danger"
              disabled={draft.submitting !== null}
              onClick={onReject}
              icon={<XCircle className="h-4 w-4" aria-hidden="true" />}
            >
              {draft.submitting === "reject" ? "Registrando…" : "Rechazar"}
            </Button>
          </div>
        </form>
      ) : null}
    </article>
  );
}

export default function AprobacionesScreen() {
  const [records, setRecords] = useState<DecisionRecord[]>([]);
  const [drafts, setDrafts] = useState<Record<string, CardDraft>>({});
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const loadQueue = useCallback(async () => {
    const res = await apiFetch(QUEUE_URL, { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`No se pudo cargar la cola (HTTP ${res.status}).`);
    }
    return (await res.json()) as DecisionRecord[];
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await loadQueue();
        if (!cancelled) {
          setRecords(list);
          setLoadError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(
            err instanceof Error
              ? err.message
              : "No se pudo contactar con el servidor. Comprueba que el API esté en marcha.",
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [loadQueue]);

  const getDraft = (id: string): CardDraft => drafts[id] ?? emptyDraft();

  const patchDraft = (id: string, patch: Partial<CardDraft>) => {
    setDrafts((prev) => ({
      ...prev,
      [id]: { ...(prev[id] ?? emptyDraft()), ...patch },
    }));
  };

  const submitAction = async (record: DecisionRecord, kind: "approve" | "reject") => {
    const draft = getDraft(record.id);
    const validated = validateHumanDecisionInput(draft.author, draft.reason);
    if (!validated.ok) {
      patchDraft(record.id, { fieldError: validated.message, actionError: null });
      return;
    }

    patchDraft(record.id, {
      fieldError: null,
      actionError: null,
      submitting: kind,
    });

    const path = kind === "approve" ? "approve" : "reject";
    try {
      const res = await apiFetch(`/api/decisions/${encodeURIComponent(record.id)}/${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(validated.body),
      });

      if (!res.ok) {
        const detail = await parseErrorDetail(res);
        patchDraft(record.id, {
          submitting: null,
          actionError: humanActionHttpErrorMessage(res.status, detail),
        });
        return;
      }

      const body = (await res.json()) as DecisionRecord;
      const merged = mergeHumanActionSuccess(record, body);
      if (!merged.ok) {
        patchDraft(record.id, {
          submitting: null,
          actionError: merged.message,
        });
        return;
      }

      setRecords((prev) =>
        prev.map((item) => (item.id === record.id ? merged.record : item)),
      );
      patchDraft(record.id, {
        submitting: null,
        reason: "",
        fieldError: null,
        actionError: null,
      });
    } catch {
      patchDraft(record.id, {
        submitting: null,
        actionError:
          "No se pudo contactar con el servidor. Comprueba que el API esté en marcha.",
      });
    }
  };

  const { pending, withEvents } = partitionEscalarQueue(records);
  const queueEmpty = !loading && !loadError && pending.length === 0 && withEvents.length === 0;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Aprobaciones"
        icon={ShieldCheck}
        description={
          <>
            <p>
              Cola de decisiones del agente en ESCALAR. Registre aquí la aprobación o el rechazo
              humano con motivo.
            </p>
            <p>{I8_NOTE}</p>
          </>
        }
      />

      {loading ? (
        <div className="space-y-3" role="status">
          <p className="text-sm text-ink-muted">Cargando cola…</p>
          <div className="skeleton h-48 w-full" aria-hidden="true" />
        </div>
      ) : null}

      {!loading && !loadError && (pending.length > 0 || withEvents.length > 0) ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <StatCard label="Pendientes de evento humano" value={pending.length} icon={Users} tone="escalate" />
          <StatCard label="Con evento humano registrado" value={withEvents.length} icon={CheckCircle2} tone="pay" />
        </div>
      ) : null}

      {loadError ? <AlertPanel>{loadError}</AlertPanel> : null}

      {queueEmpty ? (
        <EmptyState
          icon={CheckCircle2}
          title="No hay decisiones ESCALAR en cola en este momento."
          action={
            <ButtonLink href="/bandeja" variant="secondary" icon={<Inbox className="h-4 w-4" aria-hidden="true" />}>
              Revisa la bandeja de entrada
            </ButtonLink>
          }
        />
      ) : null}

      {pending.length > 0 ? (
        <section className="space-y-4">
          <h2 className="text-h2 text-ink">Pendientes de evento humano</h2>
          <div className="space-y-6">
            {pending.map((record) => (
              <DecisionCard
                key={record.id}
                record={record}
                pending
                draft={getDraft(record.id)}
                onDraftChange={(patch) => patchDraft(record.id, patch)}
                onApprove={() => submitAction(record, "approve")}
                onReject={() => submitAction(record, "reject")}
              />
            ))}
          </div>
        </section>
      ) : null}

      {withEvents.length > 0 ? (
        <section className="space-y-4">
          <h2 className="text-h2 text-ink">Con evento humano registrado</h2>
          <p className="text-sm text-ink-muted">
            La decisión del agente sigue siendo ESCALAR; solo se añadió el evento.
          </p>
          <div className="space-y-6">
            {withEvents.map((record) => (
              <DecisionCard
                key={record.id}
                record={record}
                pending={false}
                draft={getDraft(record.id)}
                onDraftChange={(patch) => patchDraft(record.id, patch)}
                onApprove={() => submitAction(record, "approve")}
                onReject={() => submitAction(record, "reject")}
              />
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
