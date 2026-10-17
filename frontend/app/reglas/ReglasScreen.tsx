"use client";

import { useCallback, useEffect, useState } from "react";

import type { FailAction, JevKey, RulesConfig } from "@/lib/rules-types";
import { JEV_KEYS, RULE_IDS } from "@/lib/rules-types";
import { cloneRulesConfig, validateDraft } from "@/lib/rules-form";
import { versionLabel } from "@/lib/version-label";

const VERSION_NOTE =
  "Las facturas ya decididas conservan la versión con la que se registraron. Esta pantalla solo sustituye las reglas vigentes.";

async function fetchRules(): Promise<RulesConfig> {
  const res = await fetch("/api/rules", { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`No se pudieron cargar las reglas (HTTP ${res.status}).`);
  }
  return (await res.json()) as RulesConfig;
}

async function putRules(document: RulesConfig): Promise<RulesConfig> {
  const res = await fetch("/api/rules", {
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
    <label htmlFor={htmlFor} className="mb-1 block text-sm font-medium text-ink-muted">
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
      className="w-full rounded-md border border-line bg-surface px-3 py-2 text-ink shadow-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
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
      className="w-full rounded-md border border-line bg-surface px-3 py-2 text-ink shadow-sm focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
    />
  );
}

function Section({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-l-4 border-accent/80 bg-surface/90 pl-5 pr-4 py-5 shadow-sm ring-1 ring-line/60">
      <h2 className="font-display text-lg text-ink">{title}</h2>
      {description ? <p className="mt-1 text-sm text-ink-muted">{description}</p> : null}
      <div className="mt-4 space-y-4">{children}</div>
    </section>
  );
}

export default function ReglasScreen() {
  const [draft, setDraft] = useState<RulesConfig | null>(null);
  const [savedLabel, setSavedLabel] = useState<string>("");
  const [loadError, setLoadError] = useState<string | null>(null);
  const [fieldErrors, setFieldErrors] = useState<string[]>([]);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  const applySaved = useCallback(async (doc: RulesConfig) => {
    setDraft(cloneRulesConfig(doc));
    setSavedLabel(await versionLabel(doc));
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const doc = await fetchRules();
        if (!cancelled) {
          await applySaved(doc);
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
      await applySaved(saved);
      setSaveMessage("Reglas vigentes guardadas.");
    } catch (err) {
      setSaveMessage(err instanceof Error ? err.message : "No se pudo guardar.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <p className="text-ink-muted" role="status">
        Cargando reglas vigentes…
      </p>
    );
  }

  if (loadError || !draft) {
    return (
      <div className="rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-danger" role="alert">
        {loadError ?? "No hay datos de reglas para mostrar."}
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header className="flex flex-col gap-4 border-b border-line pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm text-ink-muted">Puesto de control · Acme Demo Inc.</p>
          <h1 className="font-display mt-1 text-3xl text-ink">Reglas vigentes</h1>
          <p className="mt-2 max-w-prose text-sm text-ink-muted">
            Edite el paquete completo y guarde. Un campo inválido no se envía al servidor.
          </p>
        </div>
        <div className="rounded-md bg-ink px-4 py-3 text-surface">
          <p className="text-xs text-surface/70">Versión de contenido</p>
          <p className="font-mono text-lg tracking-wide">{savedLabel || "—"}</p>
          <p className="mt-2 max-w-xs text-xs leading-relaxed text-surface/80">{VERSION_NOTE}</p>
        </div>
      </header>

      {(fieldErrors.length > 0 || saveMessage) && (
        <div
          className={`rounded-md px-4 py-3 text-sm ${
            fieldErrors.length > 0
              ? "border border-danger/40 bg-danger/10 text-danger"
              : "border border-success/40 bg-success/10 text-success"
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
        <Section title="Empresa" description="Identidad y moneda base del libro.">
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

        <Section title="Límites de pago">
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

        <Section title="Aprobación humana">
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

        <Section title="Beneficiarios permitidos">
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
                  className="shrink-0 rounded-md border border-line px-3 text-sm text-ink-muted hover:bg-canvas focus:outline-none focus:ring-2 focus:ring-accent/40"
                  onClick={() =>
                    updateDraft((d) => ({
                      ...d,
                      allowed_beneficiaries: d.allowed_beneficiaries.filter((_, i) => i !== index),
                    }))
                  }
                >
                  Quitar
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="text-sm font-medium text-accent hover:underline focus:outline-none focus:ring-2 focus:ring-accent/40"
            onClick={() =>
              updateDraft((d) => ({
                ...d,
                allowed_beneficiaries: [...d.allowed_beneficiaries, ""],
              }))
            }
          >
            Añadir beneficiario
          </button>
        </Section>

        <Section title="Presupuestos por área">
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
                  className="rounded-md border border-line px-3 text-sm text-ink-muted hover:bg-canvas"
                  onClick={() =>
                    updateDraft((d) => {
                      const next = { ...d.department_budgets };
                      delete next[area];
                      return { ...d, department_budgets: next };
                    })
                  }
                >
                  Quitar
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="text-sm font-medium text-accent hover:underline"
            onClick={() =>
              updateDraft((d) => ({
                ...d,
                department_budgets: { ...d.department_budgets, "Nueva área": 1000 },
              }))
            }
          >
            Añadir área
          </button>
        </Section>

        <Section title="Aprobadores">
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
                    className="rounded-md border border-line px-3 text-sm text-ink-muted hover:bg-canvas"
                    onClick={() =>
                      updateDraft((d) => {
                        const next = { ...d.approvers };
                        delete next[role];
                        return { ...d, approvers: next };
                      })
                    }
                  >
                    Quitar
                  </button>
                ) : (
                  <span className="self-center text-xs text-ink-muted">Obligatorio</span>
                )}
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="text-sm font-medium text-accent hover:underline"
            onClick={() =>
              updateDraft((d) => ({
                ...d,
                approvers: { ...d.approvers, "Área nueva": "finanzas@demo.test" },
              }))
            }
          >
            Añadir aprobador
          </button>
        </Section>

        <Section title="Bloqueos manuales">
          {draft.manual_blocks.length === 0 ? (
            <p className="text-sm text-ink-muted">Sin bloqueos activos.</p>
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
                  className="rounded-md border border-line px-3 text-sm text-ink-muted hover:bg-canvas"
                  onClick={() =>
                    updateDraft((d) => ({
                      ...d,
                      manual_blocks: d.manual_blocks.filter((_, i) => i !== index),
                    }))
                  }
                >
                  Quitar
                </button>
              </li>
            ))}
          </ul>
          <button
            type="button"
            className="text-sm font-medium text-accent hover:underline"
            onClick={() =>
              updateDraft((d) => ({ ...d, manual_blocks: [...d.manual_blocks, ""] }))
            }
          >
            Añadir bloqueo
          </button>
        </Section>

        <Section title="Acción al fallar cada regla">
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {RULE_IDS.map((ruleId) => (
              <div key={ruleId}>
                <FieldLabel htmlFor={`on-fail-${ruleId}`}>{ruleId}</FieldLabel>
                <select
                  id={`on-fail-${ruleId}`}
                  value={draft.on_fail[ruleId]}
                  onChange={(e) =>
                    updateDraft((d) => ({
                      ...d,
                      on_fail: {
                        ...d.on_fail,
                        [ruleId]: e.target.value as FailAction,
                      },
                    }))
                  }
                  className="w-full rounded-md border border-line bg-surface px-3 py-2 text-ink focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
                >
                  <option value="FRENAR">Frenar</option>
                  <option value="ESCALAR">Escalar</option>
                </select>
              </div>
            ))}
          </div>
        </Section>

        <Section title="Umbrales JEV" description="Probabilidades entre 0 y 1. No se usa J5.">
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {JEV_KEYS.map((key: JevKey) => (
              <div key={key}>
                <FieldLabel htmlFor={`jev-${key}`}>{key}</FieldLabel>
                <NumberInput
                  id={`jev-${key}`}
                  step="0.01"
                  value={String(draft.jev_thresholds[key])}
                  onChange={(v) =>
                    updateDraft((d) => ({
                      ...d,
                      jev_thresholds: {
                        ...d.jev_thresholds,
                        [key]: v === "" ? Number.NaN : Number(v),
                      },
                    }))
                  }
                />
              </div>
            ))}
          </div>
        </Section>

        <div className="sticky bottom-0 border-t border-line bg-canvas/95 py-4 backdrop-blur">
          <button
            type="submit"
            disabled={saving}
            className="rounded-md bg-accent px-6 py-2.5 font-medium text-surface shadow-sm hover:bg-accent/90 focus:outline-none focus:ring-2 focus:ring-accent focus:ring-offset-2 disabled:opacity-60"
          >
            {saving ? "Guardando…" : "Guardar reglas vigentes"}
          </button>
        </div>
      </form>
    </div>
  );
}
