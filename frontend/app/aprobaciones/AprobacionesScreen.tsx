"use client";

import { useCallback, useEffect, useState } from "react";

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
    author: DEFAULT_APPROVAL_AUTHOR,
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
      <dd className="text-sm text-ink break-words">{value}</dd>
    </div>
  );
}

function HumanEventsList({ events }: { events: HumanEvent[] }) {
  return (
    <ul className="mt-4 space-y-3 border-t border-line/70 pt-4">
      {events.map((event, index) => (
        <li
          key={`${event.at}-${event.author}-${index}`}
          className="rounded-md bg-canvas/60 px-3 py-2 text-sm text-ink ring-1 ring-line/50"
        >
          <p className="font-medium">{actionLabel(event.action)}</p>
          <p className="mt-1 text-ink-muted">
            {event.author} · {formatEventAt(event.at)}
          </p>
          <p className="mt-2 text-ink">{event.reason}</p>
        </li>
      ))}
    </ul>
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
    <article className="border-l-4 border-accent bg-surface/95 pl-5 pr-4 py-5 shadow-sm ring-1 ring-line/60">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="font-display text-xl text-ink">{record.invoice_id}</h2>
        <span className="text-sm font-semibold text-accent">ESCALAR · severidad {record.severity}</span>
      </header>
      <p className="mt-2 text-sm text-ink-muted">ID {record.id}</p>
      <p className="mt-3 text-base text-ink leading-relaxed">{record.summary}</p>

      <dl className="mt-4 space-y-2">
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
          <div>
            <label htmlFor={`author-${record.id}`} className="mb-1 block text-sm font-medium text-ink-muted">
              Autor
            </label>
            <input
              id={`author-${record.id}`}
              type="email"
              autoComplete="email"
              value={draft.author}
              disabled={draft.submitting !== null}
              onChange={(e) =>
                onDraftChange({ author: e.target.value, fieldError: null, actionError: null })
              }
              className="w-full rounded-md border border-line bg-surface px-3 py-2 text-ink shadow-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
          </div>
          <div>
            <label htmlFor={`reason-${record.id}`} className="mb-1 block text-sm font-medium text-ink-muted">
              Motivo
            </label>
            <textarea
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
              className="w-full rounded-md border border-line bg-surface px-3 py-2 text-ink shadow-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
              placeholder="Escriba el motivo de la aprobación o del rechazo"
            />
          </div>

          {draft.fieldError ? (
            <p className="text-sm text-red-800" role="alert">{draft.fieldError}</p>
          ) : null}
          {draft.actionError ? (
            <p className="text-sm text-red-800" role="alert">{draft.actionError}</p>
          ) : null}

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              disabled={draft.submitting !== null}
              onClick={onApprove}
              className="rounded-md bg-accent px-4 py-2 text-sm font-semibold text-white shadow-sm hover:bg-accent/90 focus:outline-none focus:ring-2 focus:ring-accent/40 disabled:opacity-60"
            >
              {draft.submitting === "approve" ? "Registrando…" : "Aprobar"}
            </button>
            <button
              type="button"
              disabled={draft.submitting !== null}
              onClick={onReject}
              className="rounded-md border border-line bg-surface px-4 py-2 text-sm font-semibold text-ink shadow-sm hover:bg-canvas focus:outline-none focus:ring-2 focus:ring-accent/30 disabled:opacity-60"
            >
              {draft.submitting === "reject" ? "Registrando…" : "Rechazar"}
            </button>
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
    const res = await fetch(QUEUE_URL, { cache: "no-store" });
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
      const res = await fetch(`/api/decisions/${encodeURIComponent(record.id)}/${path}`, {
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
      <header className="max-w-2xl">
        <h1 className="font-display text-3xl text-ink tracking-tight">Aprobaciones</h1>
        <p className="mt-3 text-base text-ink-muted leading-relaxed">
          Cola de decisiones del agente en ESCALAR. Registre aquí la aprobación o el rechazo humano
          con motivo.
        </p>
        <p className="mt-2 text-sm text-ink-muted">{I8_NOTE}</p>
      </header>

      {loading ? (
        <p className="text-sm text-ink-muted">Cargando cola…</p>
      ) : null}

      {loadError ? (
        <p className="text-sm text-red-800" role="alert">{loadError}</p>
      ) : null}

      {queueEmpty ? (
        <p className="rounded-md border border-line/80 bg-surface/90 px-4 py-6 text-sm text-ink-muted">
          No hay decisiones ESCALAR en cola en este momento.
        </p>
      ) : null}

      {pending.length > 0 ? (
        <section className="space-y-4">
          <h2 className="font-display text-lg text-ink">Pendientes de evento humano</h2>
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
          <h2 className="font-display text-lg text-ink">Con evento humano registrado</h2>
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
