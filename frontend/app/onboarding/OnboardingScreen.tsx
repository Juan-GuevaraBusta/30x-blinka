"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { Building2, Check, LogIn, Plus, Sparkles } from "lucide-react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input, Select } from "@/components/ui/Field";
import { cn } from "@/lib/cn";
import { setMe, type Me, type MeCompany } from "@/lib/me";
import {
  SUPPORTED_CURRENCIES,
  companyErrorMessage,
  validateCompanyForm,
} from "@/lib/onboarding";
import { apiFetch } from "@/lib/session";

type Mode = "join" | "create";

async function readDetail(res: Response): Promise<unknown> {
  try {
    const body = (await res.json()) as { detail?: unknown };
    return body.detail;
  } catch {
    return null;
  }
}

/** T9.8 (D067): pick an existing company or create one (name, base currency, demo flag). */
export default function OnboardingScreen() {
  const router = useRouter();
  const [companies, setCompanies] = useState<MeCompany[] | null>(null);
  const [mode, setMode] = useState<Mode>("join");
  const [selected, setSelected] = useState("");
  const [name, setName] = useState("");
  const [baseCurrency, setBaseCurrency] = useState<string>("USD");
  const [isDemo, setIsDemo] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void (async () => {
      try {
        const res = await apiFetch("/api/companies", { cache: "no-store" });
        const list = res.ok ? ((await res.json()) as MeCompany[]) : [];
        setCompanies(list);
        if (list.length === 0) setMode("create");
      } catch {
        setCompanies([]);
        setMode("create");
      }
    })();
  }, []);

  async function finish(res: Response) {
    if (!res.ok) {
      setError(companyErrorMessage(await readDetail(res)));
      return;
    }
    setMe((await res.json()) as Me);
    router.replace("/");
  }

  async function onJoin(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    if (!selected) {
      setError("Elige una empresa de la lista.");
      return;
    }
    setBusy(true);
    try {
      await finish(
        await apiFetch(`/api/companies/${encodeURIComponent(selected)}/join`, { method: "POST" }),
      );
    } catch {
      setError(companyErrorMessage(null));
    } finally {
      setBusy(false);
    }
  }

  async function onCreate(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    const validated = validateCompanyForm({ name, baseCurrency, isDemo });
    if (!validated.ok) {
      setError(validated.message);
      return;
    }
    setBusy(true);
    try {
      await finish(
        await apiFetch("/api/companies", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(validated.body),
        }),
      );
    } catch {
      setError(companyErrorMessage(null));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-lg animate-fade-up py-4">
      <div className="mb-6 flex items-center gap-2 text-eyebrow uppercase text-brand-700">
        <span className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-brand-600 font-mono text-2xs text-white" aria-hidden="true">
          1
        </span>
        <span>Paso 1 de 1 · Configuración inicial</span>
      </div>
      <div className="overflow-hidden rounded-2xl border border-line bg-surface shadow-lg">
        <div className="relative overflow-hidden bg-night px-6 py-7 text-white">
          <div className="bg-grid-night absolute inset-0 opacity-40" aria-hidden="true" />
          <div className="relative flex items-start gap-4">
            <span className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-signal text-night shadow-md" aria-hidden="true">
              <Building2 className="h-6 w-6" />
            </span>
            <div>
              <h1 className="text-h1 text-white">Tu empresa</h1>
              <p className="mt-2 text-sm text-brand-100">
                Únete a la empresa de tu equipo o crea una nueva. Las reglas, proveedores, acuerdos y
                aprobaciones son de la empresa.
              </p>
            </div>
          </div>
        </div>

        <div className="p-6">
      <div className="flex gap-1 rounded-xl border border-line bg-surface-sunken p-1" role="tablist" aria-label="Cómo empezar">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "join"}
          className={cn(
            "inline-flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition-all duration-150 focus-ring",
            mode === "join" ? "bg-surface text-brand-700 shadow-sm" : "text-ink-muted hover:text-ink",
          )}
          onClick={() => setMode("join")}
        >
          <LogIn className="h-4 w-4" aria-hidden="true" />
          Unirme a una empresa
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "create"}
          className={cn(
            "inline-flex flex-1 items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition-all duration-150 focus-ring",
            mode === "create" ? "bg-surface text-brand-700 shadow-sm" : "text-ink-muted hover:text-ink",
          )}
          onClick={() => setMode("create")}
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Crear una empresa
        </button>
      </div>

      {mode === "join" ? (
        <form className="mt-6 space-y-4" onSubmit={onJoin}>
          {companies === null ? (
            <div className="space-y-2" role="status">
              <p className="text-sm text-ink-muted">Cargando empresas…</p>
              <div className="skeleton h-14" aria-hidden="true" />
              <div className="skeleton h-14" aria-hidden="true" />
            </div>
          ) : companies.length === 0 ? (
            <p className="rounded-lg border border-dashed border-line-strong bg-surface-sunken px-4 py-6 text-center text-sm text-ink-muted">
              Todavía no hay empresas. Crea la primera.
            </p>
          ) : (
            <fieldset className="space-y-2">
              <legend className="mb-2 text-sm font-semibold text-ink">Empresas</legend>
              {companies.map((company) => {
                const checked = selected === company.id;
                return (
                  <label
                    key={company.id}
                    className={cn(
                      "flex cursor-pointer items-center gap-3 rounded-xl border px-4 py-3 text-sm text-ink transition-all duration-150 focus-within:ring-4 focus-within:ring-brand-500/20",
                      checked ? "border-brand-500 bg-brand-50 shadow-sm" : "border-line hover:border-brand-300 hover:bg-brand-50/50",
                    )}
                  >
                    <input
                      type="radio"
                      name="company"
                      value={company.id}
                      checked={checked}
                      onChange={() => setSelected(company.id)}
                      className="sr-only"
                    />
                    <span
                      className={cn(
                        "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg font-display text-sm font-bold",
                        checked ? "bg-brand-600 text-white" : "bg-surface-sunken text-ink-muted",
                      )}
                      aria-hidden="true"
                    >
                      {checked ? <Check className="h-4 w-4" /> : company.name.slice(0, 1).toUpperCase()}
                    </span>
                    <span className="flex flex-1 flex-wrap items-center gap-2">
                      <span className="font-semibold">{company.name}</span>
                      <span className="text-ink-muted">· {company.base_currency}</span>
                      {company.is_demo ? (
                        <Badge tone="signal" size="sm">
                          demo
                        </Badge>
                      ) : null}
                    </span>
                  </label>
                );
              })}
            </fieldset>
          )}
          <Button
            type="submit"
            size="lg"
            disabled={busy || !companies || companies.length === 0}
            className="w-full"
            icon={<LogIn className="h-4 w-4" aria-hidden="true" />}
          >
            {busy ? "Un momento…" : "Unirme"}
          </Button>
        </form>
      ) : (
        <form className="mt-6 space-y-4" onSubmit={onCreate}>
          <label className="block space-y-1.5 text-sm font-semibold text-ink">
            <span>Nombre de la empresa</span>
            <Input
              type="text"
              required
              maxLength={120}
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="block space-y-1.5 text-sm font-semibold text-ink">
            <span>Moneda base (para convertir montos)</span>
            <Select value={baseCurrency} onChange={(e) => setBaseCurrency(e.target.value)}>
              {SUPPORTED_CURRENCIES.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </Select>
          </label>
          <label className="flex cursor-pointer items-center gap-3 rounded-xl border border-line bg-surface-sunken px-4 py-3 text-sm text-ink transition-colors hover:border-brand-300">
            <input
              type="checkbox"
              checked={isDemo}
              onChange={(e) => setIsDemo(e.target.checked)}
              className="h-4 w-4 accent-brand-600 focus-ring"
            />
            <Sparkles className="h-4 w-4 text-brand-600" aria-hidden="true" />
            Empresa demo (datos de prueba)
          </label>
          <p className="rounded-lg border border-info-200 bg-info-50 px-3 py-2 text-xs text-info-800">
            Quedarás como administrador y aprobador. Hasta que configures las reglas, cada
            factura queda en revisión humana.
          </p>
          <Button
            type="submit"
            size="lg"
            disabled={busy}
            className="w-full"
            icon={<Plus className="h-4 w-4" aria-hidden="true" />}
          >
            {busy ? "Un momento…" : "Crear empresa"}
          </Button>
        </form>
      )}

      {error ? (
        <div className="mt-4">
          <AlertPanel>{error}</AlertPanel>
        </div>
      ) : null}
        </div>
      </div>
    </div>
  );
}
