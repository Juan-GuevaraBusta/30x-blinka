"use client";

import { useCallback, useEffect, useState } from "react";

import { Ban, Building2, Gauge, Plus, Save, ShieldCheck, Trash2, UserCheck, Users, Wallet } from "lucide-react";

import { Section } from "@/components/ui/Section";
import { PageHeader } from "@/components/ui/PageHeader";
import { AlertPanel } from "@/components/ui/AlertPanel";
import { Badge } from "@/components/ui/Badge";
import { buttonClass } from "@/components/ui/Button";
import type { RulesConfig } from "@/lib/rules-types";
import { cloneRulesConfig, validateDraft } from "@/lib/rules-form";
import { apiFetch } from "@/lib/session";

async function fetchRules(): Promise<RulesConfig> {
  const res = await apiFetch("/api/rules", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`No se pudieron cargar las reglas (HTTP ${res.status}).`);
  }
  return (await res.json()) as RulesConfig;
}

async function putRules(document: RulesConfig): Promise<RulesConfig> {
  const res = await apiFetch("/api/rules", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(document),
  });
  if (res.status === 422) {
    throw new Error("El servidor rechazó el documento. Revise los campos marcados.");
  }
  if (!res.ok) {
    throw new Error(`No se pudieron guardar las reglas (HTTP ${res.status}).`);
  }
  return (await res.json()) as RulesConfig;
}

function FieldLabel({ children, htmlFor }: { children: string; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="mb-1.5 block text-sm font-semibold text-ink">
      {children}
    </label>
  );
}

function TextInput({
  id,
  value,
  onChange,
  type = "text",
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
  type?: "text" | "email";
}) {
  return (
    <input
      id={id}
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="input-field"
    />
  );
}

function NumberInput({
  id,
  value,
  onChange,
  step = "1",
}: {
  id: string;
  value: string;
  onChange: (value: string) => void;
  step?: string;
}) {
  return (
    <input
      id={id}
      type="number"
      inputMode="decimal"
      step={step}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="input-field"
    />
  );
}

export default function ReglasScreen() {
  const [draft, setDraft] = useState<RulesConfig | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<string[]>([]);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  const applySaved = useCallback((doc: RulesConfig) => {
    setDraft(cloneRulesConfig(doc));
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const doc = await fetchRules();
        if (!cancelled) {
          applySaved(doc);
          setLoadError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setLoadError(err instanceof Error ? err.message : "Error al cargar las reglas.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [applySaved]);

  const updateDraft = (updater: (prev: RulesConfig) => RulesConfig) => {
    setDraft((prev) => (prev ? updater(prev) : prev));
    setFieldErrors([]);
    setSaveMessage(null);
  };

  const handleSave = async () => {
    if (!draft) return;
    setSaveMessage(null);
    const parsed = validateDraft(draft);
    if (!parsed.ok) {
      setFieldErrors(parsed.errors);
      return;
    }
    setFieldErrors([]);
    setSaving(true);
    try {
      const saved = await putRules(parsed.document);
      applySaved(saved);
      setSaveMessage("Reglas vigentes guardadas.");
    } catch (err) {
      setSaveMessage(err instanceof Error ? err.message : "No se pudo guardar.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-3" role="status">
        <p className="text-sm text-ink-muted">Cargando reglas vigentes…</p>
        <div className="skeleton h-32" aria-hidden="true" />
        <div className="skeleton h-32" aria-hidden="true" />
      </div>
    );
  }

  if (loadError || !draft) {
    return <AlertPanel>{loadError ?? "No hay datos de reglas para mostrar."}</AlertPanel>;
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 border-b border-line pb-6 sm:flex-row sm:items-end sm:justify-between">
        <PageHeader
          bordered={false}
          title="Reglas vigentes"
          icon={ShieldCheck}
          description={
            <p>
              Edite el paquete completo y guarde. Un campo inválido no se envía al servidor.
            </p>
          }
        />
      </div>

      {(fieldErrors.length > 0 || saveMessage) && (
        <div
          className={`animate-fade-up rounded-lg border px-4 py-3 text-sm ${
            fieldErrors.length > 0
              ? "border-stop-200 bg-stop-50 text-stop-800"
              : "border-pay-200 bg-pay-50 text-pay-800"
          }`}
          role="alert"
        >
          {fieldErrors.length > 0 ? (
            <ul className="list-disc space-y-1 pl-5">
              {fieldErrors.map((msg) => (
                <li key={msg}>{msg}</li>
              ))}
            </ul>
          ) : (
            saveMessage
          )}
        </div>
      )}

      <form
        className="space-y-6"
        onSubmit={(e) => {
          e.preventDefault();
          void handleSave();
        }}
      >
        <Section icon={Building2} title="Empresa" description="Identidad y moneda base del libro.">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <FieldLabel htmlFor="company-name">Nombre</FieldLabel>
              <TextInput
                id="company-name"
                value={draft.company.name}
                onChange={(v) =>
                  updateDraft((d) => ({ ...d, company: { ...d.company, name: v } }))
                }
              />
            </div>
            <div>
              <FieldLabel htmlFor="company-currency">Moneda base</FieldLabel>
              <TextInput
                id="company-currency"
                value={draft.company.base_currency}
                onChange={(v) =>
                  updateDraft((d) => ({
                    ...d,
                    company: { ...d.company, base_currency: v },
                  }))
                }
              />
            </div>
          </div>
        </Section>

        <Section icon={Gauge} title="Límites de pago">
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <FieldLabel htmlFor="per-payment">Máximo por pago</FieldLabel>
              <NumberInput
                id="per-payment"
                value={String(draft.limits.per_payment)}
                onChange={(v) =>
                  updateDraft((d) => ({
                    ...d,
                    limits: {
                      ...d.limits,
                      per_payment: v === "" ? Number.NaN : Number(v),
                    },
                  }))
                }
              />
            </div>
            <div>
              <FieldLabel htmlFor="per-period">Máximo por mes calendario</FieldLabel>
              <NumberInput
                id="per-period"
                value={String(draft.limits.per_period.amount)}
                onChange={(v) =>
                  updateDraft((d) => ({
                    ...d,
                    limits: {
                      ...d.limits,
                      per_period: {
                        type: "calendar_month",
                        amount: v === "" ? Number.NaN : Number(v),
                      },
                    },
                  }))
                }
              />
            </div>
          </div>
        </Section>

        <Section icon={ShieldCheck} title="Aprobación humana">
          <div className="max-w-sm">
            <FieldLabel htmlFor="human-threshold">Umbral (moneda base)</FieldLabel>
            <NumberInput
              id="human-threshold"
              value={String(draft.human_approval_threshold)}
              onChange={(v) =>
                updateDraft((d) => ({
                  ...d,
                  human_approval_threshold: v === "" ? Number.NaN : Number(v),
                }))
              }
            />
          </div>
        </Section>

        <Section icon={Users} title="Beneficiarios permitidos">
          <ul className="space-y-2">
            {draft.allowed_beneficiaries.map((name, index) => (
              <li key={`ben-${index}`} className="flex gap-2">
                <TextInput
                  id={`beneficiary-${index}`}
                  value={name}
                  onChange={(v) =>
                    updateDraft((d) => {
                      const list = [...d.allowed_beneficiaries];
                      list[index] = v;
                      return { ...d, allowed_beneficiaries: list };
                    })
                  }
                />
                <button
                  type="button"
                  className={buttonClass("secondary", "md", "shrink-0 text-stop-700 hover:border-stop-200 hover:bg-stop-50")}
                  onClick={() =>
                    updateDraft((d) => ({
                      ...d,
                      allowed_beneficiaries: d.allowed_beneficiaries.filter((_, i) => i !== index),
                    }))
                  }
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                  Quitar
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className={buttonClass("ghost", "sm", "text-brand-700")}
            onClick={() =>
              updateDraft((d) => ({
                ...d,
                allowed_beneficiaries: [...d.allowed_beneficiaries, ""],
              }))
            }
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            Añadir beneficiario
          </button>
        </Section>

        <Section icon={Wallet} title="Presupuestos por área">
          <ul className="space-y-2">
            {Object.entries(draft.department_budgets).map(([area, amount]) => (
              <li key={area} className="grid gap-2 sm:grid-cols-[1fr_140px_auto]">
                <TextInput
                  id={`budget-area-${area}`}
                  value={area}
                  onChange={(newArea) =>
                    updateDraft((d) => {
                      const next = { ...d.department_budgets };
                      delete next[area];
                      next[newArea] = amount;
                      return { ...d, department_budgets: next };
                    })
                  }
                />
                <NumberInput
                  id={`budget-amt-${area}`}
                  value={String(amount)}
                  onChange={(v) =>
                    updateDraft((d) => ({
                      ...d,
                      department_budgets: {
                        ...d.department_budgets,
                        [area]: v === "" ? Number.NaN : Number(v),
                      },
                    }))
                  }
                />
                <button
                  type="button"
                  className={buttonClass("secondary", "md", "shrink-0 text-stop-700 hover:border-stop-200 hover:bg-stop-50")}
                  onClick={() =>
                    updateDraft((d) => {
                      const next = { ...d.department_budgets };
                      delete next[area];
                      return { ...d, department_budgets: next };
                    })
                  }
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                  Quitar
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className={buttonClass("ghost", "sm", "text-brand-700")}
            onClick={() =>
              updateDraft((d) => ({
                ...d,
                department_budgets: { ...d.department_budgets, "Nueva área": 1000 },
              }))
            }
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            Añadir área
          </button>
        </Section>

        <Section icon={UserCheck} title="Aprobadores">
          <ul className="space-y-2">
            {Object.entries(draft.approvers).map(([role, email]) => (
              <li key={role} className="grid gap-2 sm:grid-cols-[1fr_1fr_auto]">
                <TextInput
                  id={`approver-role-${role}`}
                  value={role}
                  onChange={(newRole) =>
                    updateDraft((d) => {
                      const next = { ...d.approvers };
                      delete next[role];
                      next[newRole] = email;
                      return { ...d, approvers: next };
                    })
                  }
                />
                <TextInput
                  id={`approver-email-${role}`}
                  type="email"
                  value={email}
                  onChange={(v) =>
                    updateDraft((d) => ({
                      ...d,
                      approvers: { ...d.approvers, [role]: v },
                    }))
                  }
                />
                {role !== "default" ? (
                  <button
                    type="button"
                    className={buttonClass("secondary", "md", "shrink-0 text-stop-700 hover:border-stop-200 hover:bg-stop-50")}
                    onClick={() =>
                      updateDraft((d) => {
                        const next = { ...d.approvers };
                        delete next[role];
                        return { ...d, approvers: next };
                      })
                    }
                  >
                    <Trash2 className="h-4 w-4" aria-hidden="true" />
                    Quitar
                  </button>
                ) : (
                  <Badge tone="brand" size="sm" className="self-center justify-self-start">
                    Obligatorio
                  </Badge>
                )}
              </li>
            ))}
          </ul>
          <button
            type="button"
            className={buttonClass("ghost", "sm", "text-brand-700")}
            onClick={() =>
              updateDraft((d) => ({
                ...d,
                approvers: { ...d.approvers, "Área nueva": "finanzas@demo.test" },
              }))
            }
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            Añadir aprobador
          </button>
        </Section>

        <Section icon={Ban} title="Bloqueos manuales">
          {draft.manual_blocks.length === 0 ? (
            <p className="inline-flex items-center gap-2 rounded-lg bg-pay-50 px-3 py-2 text-sm font-medium text-pay-800">
              <ShieldCheck className="h-4 w-4" aria-hidden="true" />
              Sin bloqueos activos.
            </p>
          ) : null}
          <ul className="space-y-2">
            {draft.manual_blocks.map((block, index) => (
              <li key={`block-${index}`} className="flex gap-2">
                <TextInput
                  id={`block-${index}`}
                  value={block}
                  onChange={(v) =>
                    updateDraft((d) => {
                      const list = [...d.manual_blocks];
                      list[index] = v;
                      return { ...d, manual_blocks: list };
                    })
                  }
                />
                <button
                  type="button"
                  className={buttonClass("secondary", "md", "shrink-0 text-stop-700 hover:border-stop-200 hover:bg-stop-50")}
                  onClick={() =>
                    updateDraft((d) => ({
                      ...d,
                      manual_blocks: d.manual_blocks.filter((_, i) => i !== index),
                    }))
                  }
                >
                  <Trash2 className="h-4 w-4" aria-hidden="true" />
                  Quitar
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className={buttonClass("ghost", "sm", "text-brand-700")}
            onClick={() =>
              updateDraft((d) => ({ ...d, manual_blocks: [...d.manual_blocks, ""] }))
            }
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            Añadir bloqueo
          </button>
        </Section>

        <div className="sticky bottom-0 -mx-1 flex items-center justify-end rounded-xl border border-line bg-surface/90 px-4 py-3 shadow-lg backdrop-blur">
          <button type="submit" disabled={saving} className={buttonClass("primary", "lg")}>
            <Save className="h-4 w-4" aria-hidden="true" />
            {saving ? "Guardando…" : "Guardar reglas vigentes"}
          </button>
        </div>
      </form>
    </div>
  );
}
