"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { AlertPanel } from "@/components/ui/AlertPanel";
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
  classificationToneClass,
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
    <form className="panel flex flex-wrap items-end gap-4 p-5" onSubmit={onSubmit} noValidate>
      <div className="flex-1 min-w-[16rem]">
        <label htmlFor="inbox-file" className="mb-1 block text-sm font-medium text-ink-muted">
          Subir correo (.eml)
        </label>
        <input
          id="inbox-file"
          type="file"
          accept=".eml,message/rfc822"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          className="input-field file:mr-3 file:rounded-lg file:border-0 file:bg-accent/15 file:px-3 file:py-1 file:text-sm file:text-ink"
        />
      </div>
      <button type="submit" disabled={submitting} className="btn-primary">
        {submitting ? "Subiendo…" : "Subir correo"}
      </button>
      {error ? <p className="w-full text-sm text-red-800" role="alert">{error}</p> : null}
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
      <Link
        href={`/decisiones/${encodeURIComponent(message.decision_id)}`}
        className="text-accent underline-offset-2 hover:underline focus-ring"
      >
        Ver decisión
      </Link>
    );
  }
  if (message.classification !== "revision") {
    return <span className="text-ink-muted">Sin decisión</span>;
  }
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="email"
          value={draft.author}
          disabled={draft.submitting !== null}
          onChange={(e) => onDraftChange({ author: e.target.value, error: null })}
          placeholder="Autor (aprobador)"
          className="input-field w-48"
        />
        <button
          type="button"
          disabled={draft.submitting !== null}
          onClick={onProcess}
          className="btn-primary"
        >
          {draft.submitting === "process" ? "Procesando…" : "Procesar como factura"}
        </button>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="text"
          value={draft.reason}
          disabled={draft.submitting !== null}
          onChange={(e) => onDraftChange({ reason: e.target.value, error: null })}
          placeholder="Motivo del descarte"
          className="input-field w-48"
        />
        <button
          type="button"
          disabled={draft.submitting !== null}
          onClick={onDismiss}
          className="btn-secondary"
        >
          {draft.submitting === "dismiss" ? "Descartando…" : "Descartar"}
        </button>
      </div>
      {draft.error ? (
        <p className="text-sm text-red-800" role="alert">
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
      <PageHeader title="Bandeja de entrada" description={<p>{I7_NOTE}</p>} />

      <UploadForm onUploaded={reload} />

      {loading ? (
        <p className="text-ink-muted" role="status">
          Cargando bandeja…
        </p>
      ) : error ? (
        <AlertPanel>{error}</AlertPanel>
      ) : rows.length === 0 ? (
        <p className="text-ink-muted" role="status">
          No hay correos en la bandeja.
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line text-ink-muted">
                <th scope="col" className="py-3 pr-4 font-medium">Fecha</th>
                <th scope="col" className="py-3 pr-4 font-medium">Remitente</th>
                <th scope="col" className="py-3 pr-4 font-medium">Asunto</th>
                <th scope="col" className="py-3 pr-4 font-medium">Clasificación</th>
                <th scope="col" className="py-3 pr-4 font-medium">Motivo</th>
                <th scope="col" className="py-3 font-medium">Acción</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-line/80 align-top">
                  <td className="py-3 pr-4 whitespace-nowrap text-ink">
                    {formatReceivedAt(row.received_at)}
                  </td>
                  <td className="py-3 pr-4 text-ink">{row.from_addr}</td>
                  <td className="py-3 pr-4 text-ink">{row.subject}</td>
                  <td className={`py-3 pr-4 font-medium ${classificationToneClass(row.classification)}`}>
                    {classificationLabel(row.classification)}
                  </td>
                  <td className="max-w-xs py-3 pr-4 text-ink-muted" title={row.reason}>
                    {row.reason}
                  </td>
                  <td className="py-3">
                    <RowActions
                      message={row}
                      draft={draftFor(row.id)}
                      onDraftChange={(patch) => patchDraft(row.id, patch)}
                      onProcess={() => runProcess(row)}
                      onDismiss={() => runDismiss(row)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
