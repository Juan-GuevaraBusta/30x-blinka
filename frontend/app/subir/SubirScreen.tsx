"use client";

import Link from "next/link";
import { useCallback, useState } from "react";

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
  return "text-ink";
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
      <header className="border-b border-line pb-6">
        <p className="text-sm text-ink-muted">
          Puesto de control · Acme Demo Inc. ·{" "}
          <Link href="/reglas" className="text-accent underline-offset-2 hover:underline">
            Reglas vigentes
          </Link>
        </p>
        <h1 className="font-display mt-1 text-3xl text-ink">Subir factura</h1>
        <p className="mt-2 max-w-prose text-sm text-ink-muted">
          Adjunte un archivo sintético y envíelo al registro del API. La decisión mostrada es la que
          devuelve el servidor; esta pantalla no calcula pagos.
        </p>
        <p className="mt-2 max-w-prose text-sm text-ink-muted">{I8_NOTE}</p>
      </header>

      <form className="space-y-6" onSubmit={onSubmit} noValidate>
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
            className="w-full rounded-md border border-line bg-surface px-3 py-2 text-sm text-ink file:mr-3 file:rounded file:border-0 file:bg-accent/15 file:px-3 file:py-1 file:text-sm file:text-ink focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
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
              className="w-full rounded-md border border-line bg-surface px-3 py-2 text-ink shadow-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
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
              className="w-full rounded-md border border-line bg-surface px-3 py-2 text-ink shadow-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
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
            className="w-full rounded-md border border-line bg-surface px-3 py-2 text-ink shadow-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="rounded-md bg-accent px-4 py-2.5 text-sm font-medium text-surface shadow-sm transition hover:bg-accent/90 focus:outline-none focus:ring-2 focus:ring-accent/40 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {submitting ? "Enviando al registro…" : "Enviar factura al registro"}
        </button>
      </form>

      {submitError ? (
        <div
          className="rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-sm text-danger"
          role="alert"
        >
          {submitError}
        </div>
      ) : null}

      {lastAccepted ? (
        <section
          className="space-y-4 rounded-md border border-line bg-surface/60 px-4 py-5"
          aria-labelledby="last-accepted-heading"
        >
          <h2 id="last-accepted-heading" className="font-display text-xl text-ink">
            Último envío aceptado
          </h2>
          <p className="text-sm text-ink-muted">{I8_NOTE}</p>
          <dl className="space-y-3">
            <div>
              <dt className="text-sm text-ink-muted">Decisión</dt>
              <dd className={`font-display text-2xl ${decisionTone(lastAccepted.decision)}`}>
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
              className="text-accent underline-offset-2 hover:underline"
            >
              Ver ficha de detalle (puede no existir si el registro aún no está en el almacén)
            </Link>
          </p>
          <details className="text-sm text-ink-muted">
            <summary className="cursor-pointer text-ink">Cuerpo completo del registro</summary>
            <pre className="mt-2 max-h-64 overflow-auto rounded border border-line bg-canvas p-3 text-xs text-ink">
              {JSON.stringify(lastAccepted.fullRecord, null, 2)}
            </pre>
          </details>
        </section>
      ) : null}
    </div>
  );
}
