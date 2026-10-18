"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import type { Decision } from "@/lib/decision-types";
import {
  INVOICE_CHANNELS,
  MSG_NETWORK,
  parseUploadResponse,
  type UploadSuccessPayload,
  validateUploadForm,
} from "@/lib/invoice-upload";

const I8_NOTE =
  "Subir una factura registra una decisión simulada en el sistema; no se mueve dinero.";

const CHANNEL_LABELS: Record<(typeof INVOICE_CHANNELS)[number], string> = {
  pdf_text: "Texto PDF",
  image: "Imagen",
  email: "Correo",
  chat: "Chat",
};

function decisionTone(decision: Decision): string {
  if (decision === "PAGAR") return "text-success";
  if (decision === "FRENAR") return "text-danger";
  return "text-accent";
}

export default function SubirScreen() {
  const [file, setFile] = useState<File | null>(null);
  const [invoiceId, setInvoiceId] = useState("");
  const [channel, setChannel] = useState<string>("pdf_text");
  const [receivedAt, setReceivedAt] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [lastAccepted, setLastAccepted] = useState<UploadSuccessPayload | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const onSubmit = useCallback(
    async (event: React.FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      setSubmitError(null);

      const validation = validateUploadForm({
        file,
        invoiceId,
        channel,
        receivedAt,
      });
      if (!validation.ok) {
        setSubmitError(validation.message);
        return;
      }

      const formData = new FormData();
      formData.append("file", file as File);
      formData.append("invoice_id", invoiceId.trim());
      formData.append("channel", channel);
      formData.append("received_at", receivedAt.trim());

      setSubmitting(true);
      try {
        const res = await fetch("/api/invoices", {
          method: "POST",
          body: formData,
        });
        let body: unknown = null;
        try {
          body = await res.json();
        } catch {
          body = null;
        }
        const parsed = parseUploadResponse(res.status, body);
        if (!parsed.ok) {
          setSubmitError(parsed.message);
          return;
        }
        setLastAccepted(parsed.data);
      } catch {
        setSubmitError(MSG_NETWORK);
      } finally {
        setSubmitting(false);
      }
    },
    [file, invoiceId, channel, receivedAt],
  );

  return (
    <div className="space-y-8">
      <PageHeader
        title="Subir factura"
        description={
          <>
            <p>
              <Link href="/reglas" className="text-accent hover:underline focus-ring">
                Reglas vigentes
              </Link>
              {" · "}
              Adjunte un archivo sintético y envíelo al registro del API. La decisión mostrada es la
              que devuelve el servidor; esta pantalla no calcula pagos.
            </p>
            <p>{I8_NOTE}</p>
          </>
        }
      />

      <form className="panel space-y-6 p-5 sm:p-6" onSubmit={onSubmit} noValidate>
        <div>
          <label htmlFor="upload-file" className="mb-1 block text-sm font-medium text-ink-muted">
            Archivo de factura
          </label>
          <input
            id="upload-file"
            name="file"
            type="file"
            accept=".pdf,.txt,application/pdf,text/plain"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="input-field file:mr-3 file:rounded-lg file:border-0 file:bg-accent/15 file:px-3 file:py-1 file:text-sm file:text-ink"
          />
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <label htmlFor="invoice-id" className="mb-1 block text-sm font-medium text-ink-muted">
              Identificador de factura
            </label>
            <input
              id="invoice-id"
              name="invoice_id"
              type="text"
              value={invoiceId}
              onChange={(e) => setInvoiceId(e.target.value)}
              autoComplete="off"
              className="input-field"
            />
          </div>
          <div>
            <label htmlFor="channel" className="mb-1 block text-sm font-medium text-ink-muted">
              Canal
            </label>
            <select
              id="channel"
              name="channel"
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
              className="input-field"
            >
              {INVOICE_CHANNELS.map((ch) => (
                <option key={ch} value={ch}>
                  {CHANNEL_LABELS[ch]}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="received-at" className="mb-1 block text-sm font-medium text-ink-muted">
            Fecha de recepción (ISO-8601 con zona)
          </label>
          <input
            id="received-at"
            name="received_at"
            type="text"
            value={receivedAt}
            onChange={(e) => setReceivedAt(e.target.value)}
            placeholder="2025-12-22T10:00:00Z"
            className="input-field font-mono"
          />
        </div>

        <button type="submit" disabled={submitting} className="btn-primary">
          {submitting ? "Enviando al registro…" : "Enviar factura al registro"}
        </button>
      </form>

      {submitError ? <AlertPanel>{submitError}</AlertPanel> : null}

      {lastAccepted ? (
        <section className="panel space-y-4 p-5 sm:p-6" aria-labelledby="last-accepted-heading">
          <h2 id="last-accepted-heading" className="text-lg font-semibold text-ink">
            Último envío aceptado
          </h2>
          <p className="text-sm text-ink-muted">{I8_NOTE}</p>
          <dl className="space-y-3">
            <div>
              <dt className="text-sm text-ink-muted">Decisión</dt>
              <dd className={`text-2xl font-semibold ${decisionTone(lastAccepted.decision)}`}>
                {lastAccepted.decision}
              </dd>
            </div>
            <div>
              <dt className="text-sm text-ink-muted">Resumen</dt>
              <dd className="max-w-prose text-base leading-relaxed text-ink">{lastAccepted.summary}</dd>
            </div>
            <div>
              <dt className="text-sm text-ink-muted">Identificador del registro</dt>
              <dd className="font-mono text-sm text-ink">{lastAccepted.id}</dd>
            </div>
          </dl>
          <p className="text-sm">
            <Link
              href={`/decisiones/${encodeURIComponent(lastAccepted.id)}`}
              className="text-accent underline-offset-2 hover:underline focus-ring"
            >
              Ver ficha de detalle (puede no existir si el registro aún no está en el almacén)
            </Link>
          </p>
          <details className="text-sm text-ink-muted">
            <summary className="cursor-pointer text-ink">Cuerpo completo del registro</summary>
            <pre className="mt-2 max-h-64 overflow-auto rounded-lg border border-line bg-paper p-3 font-mono text-xs text-ink">
              {JSON.stringify(lastAccepted.fullRecord, null, 2)}
            </pre>
          </details>
        </section>
      ) : null}
    </div>
  );
}
