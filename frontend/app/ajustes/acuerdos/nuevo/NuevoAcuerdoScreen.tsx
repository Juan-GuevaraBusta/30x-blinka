"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { PageHeader } from "@/components/ui/PageHeader";
import { Section } from "@/components/ui/Section";
import {
  applyDraftToFormState,
  buildAgreementTerms,
  emptyFormState,
  missingRequiredFields,
  type AgreementFormState,
} from "@/lib/agreement-form";
import type { AgreementDraftResponse, AgreementKind } from "@/lib/agreement-types";

const KIND_OPTIONS: { value: AgreementKind; label: string }[] = [
  { value: "retainer", label: "Retainer (monto fijo periódico)" },
  { value: "hourly", label: "Horas con extras" },
  { value: "installments", label: "Cuotas" },
  { value: "milestones", label: "Hitos" },
  { value: "unit_pricing", label: "Precio unitario" },
];

function FieldLabel({ children, htmlFor }: { children: string; htmlFor: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1 block text-xs font-medium text-ink-muted">
      {children}
    </label>
  );
}

function CiteHint({ field, draft }: { field: string; draft: AgreementDraftResponse | null }) {
  if (!draft) return null;
  const span = draft.spans[field];
  if (span) {
    return <p className="mt-1 text-xs text-accent">Cita: «{span}»</p>;
  }
  if (draft.missing.includes(field)) {
    return <p className="mt-1 text-xs text-ink-muted">Sin cita: complételo usted.</p>;
  }
  return null;
}

const inputClass =
  "block w-full rounded-md border border-line bg-paper px-3 py-2 text-sm text-ink focus-ring";

export default function NuevoAcuerdoScreen() {
  const router = useRouter();
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [draft, setDraft] = useState<AgreementDraftResponse | null>(null);
  const [form, setForm] = useState<AgreementFormState>(emptyFormState());
  const [confirmedBy, setConfirmedBy] = useState("");
  const [loadingDraft, setLoadingDraft] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const field = (name: keyof AgreementFormState, value: string) =>
    setForm((prev) => ({ ...prev, [name]: value }));

  const handleDraft = async () => {
    setError(null);
    setLoadingDraft(true);
    try {
      const body = new FormData();
      if (file) {
        body.append("file", file);
      } else {
        body.append("text", text);
      }
      const res = await fetch("/api/agreements/draft", { method: "POST", body });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: "error" }));
        setError(`No se pudo generar el borrador (${res.status}): ${detail.detail ?? "error"}`);
        return;
      }
      const result = (await res.json()) as AgreementDraftResponse;
      setDraft(result);
      setForm((prev) => applyDraftToFormState(prev, result.draft));
    } catch {
      setError("No se pudo contactar con el servidor.");
    } finally {
      setLoadingDraft(false);
    }
  };

  const missing = missingRequiredFields(form);
  const terms = buildAgreementTerms(form);
  const canConfirm = terms !== null && confirmedBy.trim() !== "" && !confirming;

  const handleConfirm = async () => {
    if (terms === null) return;
    setError(null);
    setConfirming(true);
    try {
      const res = await fetch(`/api/agreements/${encodeURIComponent(terms.vendor_key ?? "")}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          terms,
          confirmed_by: confirmedBy.trim(),
          expected_version: 0,
          source_sha256: draft?.source_sha256 ?? null,
          spans: draft?.spans ?? {},
        }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: "error" }));
        setError(`No se pudo confirmar (${res.status}): ${JSON.stringify(detail.detail ?? detail)}`);
        return;
      }
      const confirmed = await res.json();
      router.push(`/ajustes/acuerdos/${encodeURIComponent(confirmed.vendor_key)}`);
    } catch {
      setError("No se pudo contactar con el servidor.");
    } finally {
      setConfirming(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Nuevo acuerdo"
        description={<p>La IA solo propone. Nada se aplica hasta que usted confirme.</p>}
      />

      {error ? <AlertPanel>{error}</AlertPanel> : null}

      <Section title="1. Texto del acuerdo" description="Pegue el texto o suba un archivo .txt/.pdf.">
        <textarea
          className={`${inputClass} h-32`}
          placeholder="Pegue aquí el texto del acuerdo…"
          value={text}
          onChange={(event) => setText(event.target.value)}
          disabled={!!file}
        />
        <input
          type="file"
          accept=".txt,.pdf"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          className="block text-sm text-ink-muted"
        />
        <button
          type="button"
          onClick={handleDraft}
          disabled={loadingDraft || (!text.trim() && !file)}
          className="rounded-md border border-line bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 focus-ring disabled:opacity-50"
        >
          {loadingDraft ? "Generando borrador…" : "Generar borrador"}
        </button>
      </Section>

      <Section title="2. Revisar y confirmar" description="Cada campo muestra su cita del documento, si la IA la encontró.">
        <div>
          <FieldLabel htmlFor="kind">Tipo de acuerdo</FieldLabel>
          <select
            id="kind"
            className={inputClass}
            value={form.kind}
            onChange={(event) => field("kind", event.target.value)}
          >
            {KIND_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="grid gap-4 sm:grid-cols-2">
          <div>
            <FieldLabel htmlFor="vendor_name">Proveedor</FieldLabel>
            <input
              id="vendor_name"
              className={inputClass}
              value={form.vendor_name}
              onChange={(event) => field("vendor_name", event.target.value)}
            />
            <CiteHint field="vendor_name" draft={draft} />
          </div>
          <div>
            <FieldLabel htmlFor="currency">Moneda</FieldLabel>
            <input
              id="currency"
              className={inputClass}
              value={form.currency}
              onChange={(event) => field("currency", event.target.value)}
            />
            <CiteHint field="currency" draft={draft} />
          </div>
          <div>
            <FieldLabel htmlFor="valid_from">Vigente desde</FieldLabel>
            <input
              id="valid_from"
              type="date"
              className={inputClass}
              value={form.valid_from}
              onChange={(event) => field("valid_from", event.target.value)}
            />
            <CiteHint field="valid_from" draft={draft} />
          </div>
          <div>
            <FieldLabel htmlFor="valid_to">Vigente hasta (opcional)</FieldLabel>
            <input
              id="valid_to"
              type="date"
              className={inputClass}
              value={form.valid_to}
              onChange={(event) => field("valid_to", event.target.value)}
            />
            <CiteHint field="valid_to" draft={draft} />
          </div>
          <div>
            <FieldLabel htmlFor="department">Departamento (opcional)</FieldLabel>
            <input
              id="department"
              className={inputClass}
              value={form.department}
              onChange={(event) => field("department", event.target.value)}
            />
          </div>
        </div>

        {form.kind === "retainer" ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <FieldLabel htmlFor="periodicity">Periodicidad</FieldLabel>
              <select
                id="periodicity"
                className={inputClass}
                value={form.periodicity}
                onChange={(event) => field("periodicity", event.target.value)}
              >
                <option value="monthly">Mensual</option>
                <option value="biweekly">Quincenal</option>
                <option value="quarterly">Trimestral</option>
              </select>
            </div>
            <div />
            <div>
              <FieldLabel htmlFor="amount_min">Monto mínimo</FieldLabel>
              <input
                id="amount_min"
                className={inputClass}
                value={form.amount_min}
                onChange={(event) => field("amount_min", event.target.value)}
              />
              <CiteHint field="amount_min" draft={draft} />
            </div>
            <div>
              <FieldLabel htmlFor="amount_max">Monto máximo</FieldLabel>
              <input
                id="amount_max"
                className={inputClass}
                value={form.amount_max}
                onChange={(event) => field("amount_max", event.target.value)}
              />
              <CiteHint field="amount_max" draft={draft} />
            </div>
            <div>
              <FieldLabel htmlFor="total_cap">Tope total (opcional)</FieldLabel>
              <input
                id="total_cap"
                className={inputClass}
                value={form.total_cap}
                onChange={(event) => field("total_cap", event.target.value)}
              />
            </div>
          </div>
        ) : null}

        {form.kind === "hourly" ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <FieldLabel htmlFor="rate">Tarifa por hora</FieldLabel>
              <input
                id="rate"
                className={inputClass}
                value={form.rate}
                onChange={(event) => field("rate", event.target.value)}
              />
              <CiteHint field="rate" draft={draft} />
            </div>
            <div>
              <FieldLabel htmlFor="included_hours">Horas incluidas (opcional)</FieldLabel>
              <input
                id="included_hours"
                className={inputClass}
                value={form.included_hours}
                onChange={(event) => field("included_hours", event.target.value)}
              />
            </div>
            <div>
              <FieldLabel htmlFor="overtime_multiplier">Multiplicador de extras (opcional)</FieldLabel>
              <input
                id="overtime_multiplier"
                className={inputClass}
                value={form.overtime_multiplier}
                onChange={(event) => field("overtime_multiplier", event.target.value)}
              />
            </div>
            <div>
              <FieldLabel htmlFor="overtime_max_hours">Máximo de horas extra (opcional)</FieldLabel>
              <input
                id="overtime_max_hours"
                className={inputClass}
                value={form.overtime_max_hours}
                onChange={(event) => field("overtime_max_hours", event.target.value)}
              />
            </div>
            <div>
              <FieldLabel htmlFor="period_cap">Tope por periodo (opcional)</FieldLabel>
              <input
                id="period_cap"
                className={inputClass}
                value={form.period_cap}
                onChange={(event) => field("period_cap", event.target.value)}
              />
            </div>
          </div>
        ) : null}

        {form.kind === "installments" || form.kind === "milestones" ? (
          <div>
            <FieldLabel htmlFor="itemsText">
              {"Ítems (uno por línea: clave|desde|hasta|monto)"}
            </FieldLabel>
            <textarea
              id="itemsText"
              className={`${inputClass} h-24 font-mono`}
              placeholder="1/3|2026-02-01|2026-02-28|1000"
              value={form.itemsText}
              onChange={(event) => field("itemsText", event.target.value)}
            />
            <div className="mt-2 max-w-xs">
              <FieldLabel htmlFor="total_cap">Tope total (opcional)</FieldLabel>
              <input
                id="total_cap"
                className={inputClass}
                value={form.total_cap}
                onChange={(event) => field("total_cap", event.target.value)}
              />
            </div>
          </div>
        ) : null}

        {form.kind === "unit_pricing" ? (
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <FieldLabel htmlFor="unit">Unidad</FieldLabel>
              <input
                id="unit"
                className={inputClass}
                value={form.unit}
                onChange={(event) => field("unit", event.target.value)}
              />
              <CiteHint field="unit" draft={draft} />
            </div>
            <div>
              <FieldLabel htmlFor="formulaKind">Fórmula</FieldLabel>
              <select
                id="formulaKind"
                className={inputClass}
                value={form.formulaKind}
                onChange={(event) =>
                  setForm((prev) => ({
                    ...prev,
                    formulaKind: event.target.value as "unit_rate" | "tiered",
                  }))
                }
              >
                <option value="unit_rate">Tarifa única</option>
                <option value="tiered">Tramos</option>
              </select>
            </div>
            {form.formulaKind === "unit_rate" ? (
              <div>
                <FieldLabel htmlFor="rate">Tarifa</FieldLabel>
                <input
                  id="rate"
                  className={inputClass}
                  value={form.rate}
                  onChange={(event) => field("rate", event.target.value)}
                />
                <CiteHint field="rate" draft={draft} />
              </div>
            ) : (
              <div className="sm:col-span-2">
                <FieldLabel htmlFor="tiersText">
                  {"Tramos (uno por línea: hasta|tarifa; deje «hasta» vacío para el último tramo)"}
                </FieldLabel>
                <textarea
                  id="tiersText"
                  className={`${inputClass} h-20 font-mono`}
                  placeholder="100|10&#10;|8"
                  value={form.tiersText}
                  onChange={(event) => field("tiersText", event.target.value)}
                />
              </div>
            )}
            <div>
              <FieldLabel htmlFor="period_cap">Tope por periodo (opcional)</FieldLabel>
              <input
                id="period_cap"
                className={inputClass}
                value={form.period_cap}
                onChange={(event) => field("period_cap", event.target.value)}
              />
            </div>
          </div>
        ) : null}

        <div className="max-w-sm">
          <FieldLabel htmlFor="confirmedBy">Confirmado por (correo del aprobador)</FieldLabel>
          <input
            id="confirmedBy"
            className={inputClass}
            value={confirmedBy}
            onChange={(event) => setConfirmedBy(event.target.value)}
          />
        </div>

        {missing.length > 0 ? (
          <p className="text-xs text-ink-muted">Faltan campos: {missing.join(", ")}</p>
        ) : null}

        <button
          type="button"
          onClick={handleConfirm}
          disabled={!canConfirm}
          className="rounded-md border border-line bg-accent px-4 py-2 text-sm font-medium text-white hover:opacity-90 focus-ring disabled:opacity-50"
        >
          {confirming ? "Confirmando…" : "Confirmar acuerdo"}
        </button>
      </Section>
    </div>
  );
}
