"use client";

import { ArrowRight, FileText, FileUp, Send, UploadCloud } from "lucide-react";
import Link from "next/link";
import { useCallback, useState } from "react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { DecisionBadge, DECISION_META } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Field, Input, Select } from "@/components/ui/Field";
import { PageHeader } from "@/components/ui/PageHeader";
import { cn } from "@/lib/cn";
import type { Decision } from "@/lib/decision-types";
import {
  INVOICE_CHANNELS,
  MSG_NETWORK,
  parseUploadResponse,
  type UploadSuccessPayload,
  validateUploadForm,
} from "@/lib/invoice-upload";
import { apiFetch } from "@/lib/session";

const I8_NOTE =
  "Subir una factura registra una decisión simulada en el sistema; no se mueve dinero.";

const CHANNEL_LABELS: Record<(typeof INVOICE_CHANNELS)[number], string> = {
  pdf_text: "Texto PDF",
  image: "Imagen",
  email: "Correo",
  chat: "Chat",
};

const RESULT_TONE: Record<Decision, string> = {
  PAGAR: "border-pay-200 bg-pay-50",
  FRENAR: "border-stop-200 bg-stop-50",
  ESCALAR: "border-escalate-200 bg-escalate-50",
};

export default function SubirScreen() {
  const [file, setFile] = useState<File | null>(null);
  const [invoiceId, setInvoiceId] = useState("");
  const [channel, setChannel] = useState<string>("pdf_text");
  const [receivedAt, setReceivedAt] = useState("");
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [lastAccepted, setLastAccepted] = useState<UploadSuccessPayload | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [dragging, setDragging] = useState(false);

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
        const res = await apiFetch("/api/invoices", {
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
        icon={FileUp}
        description={
          <>
            <p>
              <Link href="/reglas" className="font-semibold text-brand-700 hover:underline focus-ring">
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
          <label htmlFor="upload-file" className="mb-1.5 block text-sm font-semibold text-ink">
            Archivo de factura
          </label>
          <div
            className={cn(
              "group relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-all duration-200",
              dragging
                ? "border-brand-500 bg-brand-50 shadow-glow"
                : file
                  ? "border-pay-500 bg-pay-50"
                  : "border-line-strong bg-surface-sunken hover:border-brand-400 hover:bg-brand-50/60",
            )}
            onDragEnter={() => setDragging(true)}
            onDragLeave={() => setDragging(false)}
            onDrop={() => setDragging(false)}
          >
            <span
              className={cn(
                "mb-3 inline-flex h-14 w-14 items-center justify-center rounded-2xl shadow-md transition-transform duration-200 group-hover:-translate-y-1",
                file ? "bg-pay-600 text-white" : "bg-night text-signal",
              )}
              aria-hidden="true"
            >
              {file ? <FileText className="h-7 w-7" /> : <UploadCloud className="h-7 w-7" />}
            </span>
            {file ? (
              <p className="text-sm font-semibold text-pay-800">{file.name}</p>
            ) : (
              <p className="text-sm font-semibold text-ink">
                Arrastre la factura aquí o <span className="text-brand-700 underline">elija un archivo</span>
              </p>
            )}
            <p className="mt-1 text-xs text-ink-muted">PDF o texto plano</p>
            <input
              id="upload-file"
              name="file"
              type="file"
              accept=".pdf,.txt,application/pdf,text/plain"
              onChange={(e) => setFile(e.target.files?.[0] ?? null)}
              className="absolute inset-0 h-full w-full cursor-pointer opacity-0 focus-ring"
            />
          </div>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Identificador de factura" htmlFor="invoice-id">
            <Input
              id="invoice-id"
              name="invoice_id"
              type="text"
              value={invoiceId}
              onChange={(e) => setInvoiceId(e.target.value)}
              autoComplete="off"
            />
          </Field>
          <Field label="Canal" htmlFor="channel">
            <Select id="channel" name="channel" value={channel} onChange={(e) => setChannel(e.target.value)}>
              {INVOICE_CHANNELS.map((ch) => (
                <option key={ch} value={ch}>
                  {CHANNEL_LABELS[ch]}
                </option>
              ))}
            </Select>
          </Field>
        </div>

        <Field label="Fecha de recepción (ISO-8601 con zona)" htmlFor="received-at">
          <Input
            id="received-at"
            name="received_at"
            type="text"
            value={receivedAt}
            onChange={(e) => setReceivedAt(e.target.value)}
            placeholder="2025-12-22T10:00:00Z"
            className="font-mono"
          />
        </Field>

        <Button type="submit" disabled={submitting} size="lg" icon={<Send className="h-4 w-4" aria-hidden="true" />}>
          {submitting ? "Enviando al registro…" : "Enviar factura al registro"}
        </Button>
      </form>

      {submitError ? <AlertPanel>{submitError}</AlertPanel> : null}

      {lastAccepted ? (
        <section
          className={cn("animate-fade-up space-y-4 rounded-xl border p-5 shadow-md sm:p-6", RESULT_TONE[lastAccepted.decision] ?? "border-line bg-surface")}
          aria-labelledby="last-accepted-heading"
        >
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 id="last-accepted-heading" className="text-h2 text-ink">
              Último envío aceptado
            </h2>
            <DecisionBadge decision={lastAccepted.decision} size="lg" />
          </div>
          <p className="text-sm text-ink-muted">{I8_NOTE}</p>
          <dl className="space-y-3 rounded-lg border border-line bg-surface p-4">
            <div>
              <dt className="text-eyebrow uppercase text-ink-muted">Decisión</dt>
              <dd className="mt-1 text-2xl font-semibold text-ink">
                {lastAccepted.decision}
                {DECISION_META[lastAccepted.decision] ? (
                  <span className="ml-2 text-sm font-medium text-ink-muted">{DECISION_META[lastAccepted.decision].verb}</span>
                ) : null}
              </dd>
            </div>
            <div>
              <dt className="text-eyebrow uppercase text-ink-muted">Resumen</dt>
              <dd className="mt-1 max-w-prose text-base leading-relaxed text-ink">{lastAccepted.summary}</dd>
            </div>
            <div>
              <dt className="text-eyebrow uppercase text-ink-muted">Identificador del registro</dt>
              <dd className="mt-1 font-mono text-sm text-ink">{lastAccepted.id}</dd>
            </div>
          </dl>
          <p className="text-sm">
            <Link
              href={`/decisiones/${encodeURIComponent(lastAccepted.id)}`}
              className="inline-flex items-center gap-1.5 font-semibold text-brand-700 underline-offset-2 hover:underline focus-ring"
            >
              Ver ficha de detalle (puede no existir si el registro aún no está en el almacén)
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </p>
          <details className="text-sm text-ink-muted">
            <summary className="cursor-pointer font-medium text-ink">Cuerpo completo del registro</summary>
            <pre className="mt-2 max-h-64 overflow-auto rounded-lg border border-night-line bg-night p-3 font-mono text-xs text-brand-100">
              {JSON.stringify(lastAccepted.fullRecord, null, 2)}
            </pre>
          </details>
        </section>
      ) : null}
    </div>
  );
}
