"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { AlertPanel } from "@/components/ui/AlertPanel";
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
    <div className="mx-auto max-w-md">
      <h1 className="text-2xl font-semibold text-ink">Tu empresa</h1>
      <p className="mt-2 text-sm text-ink-muted">
        Únete a la empresa de tu equipo o crea una nueva. Las reglas, proveedores, acuerdos y
        aprobaciones son de la empresa.
      </p>

      <div className="mt-6 flex gap-2" role="tablist" aria-label="Cómo empezar">
        <button
          type="button"
          role="tab"
          aria-selected={mode === "join"}
          className={`rounded-lg px-3 py-2 text-sm font-medium focus-ring ${
            mode === "join" ? "bg-accent/10 text-ink" : "text-ink-muted"
          }`}
          onClick={() => setMode("join")}
        >
          Unirme a una empresa
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === "create"}
          className={`rounded-lg px-3 py-2 text-sm font-medium focus-ring ${
            mode === "create" ? "bg-accent/10 text-ink" : "text-ink-muted"
          }`}
          onClick={() => setMode("create")}
        >
          Crear una empresa
        </button>
      </div>

      {mode === "join" ? (
        <form className="mt-6 space-y-4" onSubmit={onJoin}>
          {companies === null ? (
            <p className="text-sm text-ink-muted" role="status">
              Cargando empresas…
            </p>
          ) : companies.length === 0 ? (
            <p className="text-sm text-ink-muted">Todavía no hay empresas. Crea la primera.</p>
          ) : (
            <fieldset className="space-y-2">
              <legend className="text-sm font-medium text-ink">Empresas</legend>
              {companies.map((company) => (
                <label key={company.id} className="flex items-center gap-2 text-sm text-ink">
                  <input
                    type="radio"
                    name="company"
                    value={company.id}
                    checked={selected === company.id}
                    onChange={() => setSelected(company.id)}
                  />
                  <span>
                    {company.name} · {company.base_currency}
                    {company.is_demo ? " · demo" : ""}
                  </span>
                </label>
              ))}
            </fieldset>
          )}
          <button
            type="submit"
            disabled={busy || !companies || companies.length === 0}
            className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white focus-ring disabled:opacity-60"
          >
            {busy ? "Un momento…" : "Unirme"}
          </button>
        </form>
      ) : (
        <form className="mt-6 space-y-4" onSubmit={onCreate}>
          <label className="block text-sm font-medium text-ink">
            Nombre de la empresa
            <input
              type="text"
              required
              maxLength={120}
              className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-ink focus-ring"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="block text-sm font-medium text-ink">
            Moneda base (para convertir montos)
            <select
              className="mt-1 w-full rounded-lg border border-line bg-surface px-3 py-2 text-ink focus-ring"
              value={baseCurrency}
              onChange={(e) => setBaseCurrency(e.target.value)}
            >
              {SUPPORTED_CURRENCIES.map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm text-ink">
            <input type="checkbox" checked={isDemo} onChange={(e) => setIsDemo(e.target.checked)} />
            Empresa demo (datos de prueba)
          </label>
          <p className="text-xs text-ink-muted">
            Quedarás como administrador y aprobador. Hasta que configures las reglas, cada
            factura queda en revisión humana.
          </p>
          <button
            type="submit"
            disabled={busy}
            className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-semibold text-white focus-ring disabled:opacity-60"
          >
            {busy ? "Un momento…" : "Crear empresa"}
          </button>
        </form>
      )}

      {error ? (
        <div className="mt-4">
          <AlertPanel>{error}</AlertPanel>
        </div>
      ) : null}
    </div>
  );
}
