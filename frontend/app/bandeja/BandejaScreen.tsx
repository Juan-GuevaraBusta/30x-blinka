"use client";

import { ArrowRight, FileCheck2, HelpCircle, Inbox, Mail, MailX, Trash2, UploadCloud, Zap } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { Button, ButtonLink } from "@/components/ui/Button";
import { Card } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Field";
import { PageHeader } from "@/components/ui/PageHeader";
import {
  DEFAULT_APPROVAL_AUTHOR,
  MAX_HUMAN_FIELD_LENGTH,
  MSG_AUTHOR_REQUIRED,
  MSG_FIELD_TOO_LONG,
  MSG_REASON_REQUIRED,
  trimHumanField,
} from "@/lib/approvals";
import {
  classificationLabel,
  type InboxMessage,
  parseInboxList,
} from "@/lib/inbox-types";
import { apiFetch } from "@/lib/session";

const I7_NOTE =
  "El clasificador decide con señales deterministas; el modelo solo desempata en la zona gris y nunca manda un correo directo al pago.";

type Draft = {
  author: string;
  reason: string;
  error: string | null;
  submitting: "process" | "dismiss" | null;
};

const CLASSIFICATION_STYLE: Record<string, { tone: BadgeTone; icon: typeof Mail; rail: string }> = {
  es_factura: { tone: "pay", icon: FileCheck2, rail: "bg-pay-500" },
  revision: { tone: "escalate", icon: HelpCircle, rail: "bg-escalate-500" },
};
const DEFAULT_CLASSIFICATION_STYLE = { tone: "neutral" as BadgeTone, icon: MailX, rail: "bg-line-strong" };

function emptyDraft(): Draft {
  return { author: DEFAULT_APPROVAL_AUTHOR, reason: "", error: null, submitting: null };
}

function formatReceivedAt(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString("es-ES", { dateStyle: "medium", timeStyle: "short" });
}

async function fetchInbox(): Promise<InboxMessage[]> {
  const res = await apiFetch("/api/inbox", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`HTTP_${res.status}`);
  }
  const body: unknown = await res.json();
  try {
    return parseInboxList(body);
  } catch {
    throw new Error("INVALID_BODY");
  }
}

function fetchErrorMessage(err: unknown): string {
  if (err instanceof Error) {
    if (err.message.startsWith("HTTP_")) {
      return `No se pudo cargar la bandeja (HTTP ${err.message.slice(5)}).`;
    }
    if (err.message === "INVALID_BODY") {
      return "El servidor devolvió un formato inesperado (HTTP 200).";
    }
  }
  return "No se pudo cargar la bandeja. Compruebe la conexión e intente de nuevo.";
}

function UploadForm({ onUploaded }: { onUploaded: () => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const onSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!file) {
        setError("Seleccione un archivo .eml.");
        return;
      }
      setSubmitting(true);
      setError(null);
      try {
        const formData = new FormData();
        formData.append("file", file);
        const res = await apiFetch("/api/inbox", { method: "POST", body: formData });
        if (!res.ok) {
          const body: unknown = await res.json().catch(() => null);
          const detail =
            body && typeof body === "object" && "detail" in body
              ? String((body as { detail: unknown }).detail)
              : `HTTP ${res.status}`;
          setError(`No se pudo subir el correo (${detail}).`);
          return;
        }
        setFile(null);
        onUploaded();
      } catch {
        setError("No se pudo subir el correo. Compruebe la conexión e intente de nuevo.");
      } finally {
        setSubmitting(false);
      }
    },
    [file, onUploaded],
  );

  return (
    <form
      className="flex flex-wrap items-end gap-4 rounded-xl border border-dashed border-brand-300 bg-brand-50/70 p-5"
      onSubmit={onSubmit}
      noValidate
    >
      <span className="hidden h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-night text-signal sm:inline-flex" aria-hidden="true">
        <UploadCloud className="h-5 w-5" />
      </span>
      <div className="min-w-64 flex-1">
        <label htmlFor="inbox-file" className="mb-1.5 block text-sm font-semibold text-ink">
          Subir correo (.eml)
        </label>
        <input
          id="inbox-file"
          type="file"
          accept=".eml,message/rfc822"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="input-field file:mr-3 file:rounded-md file:border-0 file:bg-brand-600 file:px-3 file:py-1 file:text-sm file:font-semibold file:text-white"
        />
      </div>
      <Button type="submit" disabled={submitting} icon={<Mail className="h-4 w-4" aria-hidden="true" />}>
        {submitting ? "Subiendo…" : "Subir correo"}
      </Button>
      {error ? <p className="w-full text-sm font-medium text-stop-700" role="alert">{error}</p> : null}
    </form>
  );
}

function RowActions({
  message,
  draft,
  onDraftChange,
  onProcess,
  onDismiss,
}: {
  message: InboxMessage;
  draft: Draft;
  onDraftChange: (patch: Partial<Draft>) => void;
  onProcess: () => void;
  onDismiss: () => void;
}) {
  if (message.decision_id) {
    return (
      <ButtonLink
        href={`/decisiones/${encodeURIComponent(message.decision_id)}`}
        variant="secondary"
        size="sm"
        icon={<ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />}
      >
        Ver decisión
      </ButtonLink>
    );
  }
  if (message.classification !== "revision") {
    return <span className="text-sm text-ink-subtle">Sin decisión</span>;
  }
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <Input
          type="email"
          value={draft.author}
          disabled={draft.submitting !== null}
          onChange={(e) => onDraftChange({ author: e.target.value, error: null })}
          placeholder="Autor (aprobador)"
          className="w-56"
        />
        <Button
          size="sm"
          disabled={draft.submitting !== null}
          onClick={onProcess}
          icon={<Zap className="h-3.5 w-3.5" aria-hidden="true" />}
        >
          {draft.submitting === "process" ? "Procesando…" : "Procesar como factura"}
        </Button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <Input
          type="text"
          value={draft.reason}
          disabled={draft.submitting !== null}
          onChange={(e) => onDraftChange({ reason: e.target.value, error: null })}
          placeholder="Motivo del descarte"
          className="w-56"
        />
        <Button
          variant="secondary"
          size="sm"
          disabled={draft.submitting !== null}
          onClick={onDismiss}
          icon={<Trash2 className="h-3.5 w-3.5" aria-hidden="true" />}
        >
          {draft.submitting === "dismiss" ? "Descartando…" : "Descartar"}
        </Button>
      </div>
      {draft.error ? (
        <p className="text-sm font-medium text-stop-700" role="alert">
          {draft.error}
        </p>
      ) : null}
    </div>
  );
}

export default function BandejaScreen() {
  const [rows, setRows] = useState<InboxMessage[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [drafts, setDrafts] = useState<Record<string, Draft>>({});

  const reload = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchInbox()
      .then((list) => setRows(list))
      .catch((err) => setError(fetchErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const draftFor = useCallback(
    (id: string): Draft => drafts[id] ?? emptyDraft(),
    [drafts],
  );
  const patchDraft = useCallback((id: string, patch: Partial<Draft>) => {
    setDrafts((prev) => ({ ...prev, [id]: { ...(prev[id] ?? emptyDraft()), ...patch } }));
  }, []);

  const runProcess = useCallback(
    async (message: InboxMessage) => {
      const draft = draftFor(message.id);
      const author = trimHumanField(draft.author);
      if (author.length === 0) {
        patchDraft(message.id, { error: MSG_AUTHOR_REQUIRED });
        return;
      }
      if (author.length > MAX_HUMAN_FIELD_LENGTH) {
        patchDraft(message.id, { error: MSG_FIELD_TOO_LONG });
        return;
      }
      patchDraft(message.id, { submitting: "process", error: null });
      try {
        const res = await apiFetch(`/api/inbox/${encodeURIComponent(message.id)}/process`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ author }),
        });
        if (!res.ok) {
          const body: unknown = await res.json().catch(() => null);
          const detail =
            body && typeof body === "object" && "detail" in body
              ? String((body as { detail: unknown }).detail)
              : `HTTP ${res.status}`;
          patchDraft(message.id, { submitting: null, error: `No se pudo procesar (${detail}).` });
          return;
        }
        patchDraft(message.id, { submitting: null, error: null });
        reload();
      } catch {
        patchDraft(message.id, {
          submitting: null,
          error: "No se pudo procesar. Compruebe la conexión e intente de nuevo.",
        });
      }
    },
    [draftFor, patchDraft, reload],
  );

  const runDismiss = useCallback(
    async (message: InboxMessage) => {
      const draft = draftFor(message.id);
      const author = trimHumanField(draft.author);
      const reason = trimHumanField(draft.reason);
      if (author.length === 0) {
        patchDraft(message.id, { error: MSG_AUTHOR_REQUIRED });
        return;
      }
      if (reason.length === 0) {
        patchDraft(message.id, { error: MSG_REASON_REQUIRED });
        return;
      }
      if (author.length > MAX_HUMAN_FIELD_LENGTH || reason.length > MAX_HUMAN_FIELD_LENGTH) {
        patchDraft(message.id, { error: MSG_FIELD_TOO_LONG });
        return;
      }
      patchDraft(message.id, { submitting: "dismiss", error: null });
      try {
        const res = await apiFetch(`/api/inbox/${encodeURIComponent(message.id)}/dismiss`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ author, reason }),
        });
        if (!res.ok) {
          const body: unknown = await res.json().catch(() => null);
          const detail =
            body && typeof body === "object" && "detail" in body
              ? String((body as { detail: unknown }).detail)
              : `HTTP ${res.status}`;
          patchDraft(message.id, { submitting: null, error: `No se pudo descartar (${detail}).` });
          return;
        }
        patchDraft(message.id, { submitting: null, error: null });
        reload();
      } catch {
        patchDraft(message.id, {
          submitting: null,
          error: "No se pudo descartar. Compruebe la conexión e intente de nuevo.",
        });
      }
    },
    [draftFor, patchDraft, reload],
  );

  return (
    <div className="space-y-8">
      <PageHeader title="Bandeja de entrada" icon={Inbox} description={<p>{I7_NOTE}</p>} />

      <UploadForm onUploaded={reload} />

      {loading ? (
        <div className="space-y-3" role="status">
          <span className="sr-only">Cargando bandeja…</span>
          <p className="text-sm text-ink-muted" aria-hidden="true">
            Cargando bandeja…
          </p>
          <div className="skeleton h-24" aria-hidden="true" />
          <div className="skeleton h-24" aria-hidden="true" />
        </div>
      ) : error ? (
        <AlertPanel>{error}</AlertPanel>
      ) : rows.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title="No hay correos en la bandeja."
          description="Suba un correo .eml para que el clasificador decida si es una factura."
          action={
            <Button
              variant="primary"
              icon={<UploadCloud className="h-4 w-4" aria-hidden="true" />}
              onClick={() => document.getElementById("inbox-file")?.click()}
            >
              Subir correo
            </Button>
          }
        />
      ) : (
        <ul className="space-y-3" aria-label="Correos de la bandeja">
          {rows.map((row) => {
            const style = CLASSIFICATION_STYLE[row.classification] ?? DEFAULT_CLASSIFICATION_STYLE;
            const Icon = style.icon;
            return (
              <li key={row.id} className="animate-fade-up">
                <Card padded={false} className="relative overflow-hidden transition-shadow duration-200 hover:shadow-md">
                  <span className={`absolute inset-y-0 left-0 w-1 ${style.rail}`} aria-hidden="true" />
                  <div className="grid gap-4 p-5 pl-6 lg:grid-cols-[1fr_auto]">
                    <div className="min-w-0 space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge tone={style.tone} icon={<Icon className="h-3.5 w-3.5" aria-hidden="true" />}>
                          {classificationLabel(row.classification)}
                        </Badge>
                        <span className="font-mono text-xs text-ink-muted">{formatReceivedAt(row.received_at)}</span>
                      </div>
                      <p className="truncate text-h3 text-ink">{row.subject}</p>
                      <p className="text-sm text-ink-muted">
                        <span className="sr-only">Remitente: </span>
                        {row.from_addr}
                      </p>
                      <p className="max-w-prose text-sm text-ink-muted" title={row.reason}>
                        <span className="font-semibold text-ink">Motivo: </span>
                        {row.reason}
                      </p>
                    </div>
                    <div className="lg:min-w-72">
                      <RowActions
                        message={row}
                        draft={draftFor(row.id)}
                        onDraftChange={(patch) => patchDraft(row.id, patch)}
                        onProcess={() => runProcess(row)}
                        onDismiss={() => runDismiss(row)}
                      />
                    </div>
                  </div>
                </Card>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
