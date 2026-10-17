"use client";

import { useEffect, useState } from "react";

import {
  formatMetricNumber,
  presentMetricsFromResponse,
  type MetricsPresentation,
} from "@/lib/metrics-present";

export default function MetricasScreen() {
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<MetricsPresentation | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/metrics", { cache: "no-store" });
        let body: unknown = null;
        try {
          body = await res.json();
        } catch {
          body = null;
        }
        if (!cancelled) {
          setView(presentMetricsFromResponse(res.status, body));
        }
      } catch {
        if (!cancelled) {
          setView({
            kind: "error",
            message:
              "No se pudo leer las métricas. Compruebe la conexión con el servidor e intente recargar la página.",
          });
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <p className="text-ink-muted" role="status">
        Cargando métricas de evaluación…
      </p>
    );
  }

  if (!view || view.kind === "error") {
    return (
      <div className="rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-danger" role="alert">
        {view?.kind === "error" ? view.message : "No hay datos de métricas para mostrar."}
      </div>
    );
  }

  if (view.kind === "empty") {
    return (
      <div className="space-y-8">
        <header className="border-b border-line pb-6">
          <p className="text-sm text-ink-muted">Puesto de control · Acme Demo Inc.</p>
          <h1 className="font-display mt-1 text-3xl text-ink">Métricas de evaluación</h1>
          <p className="mt-2 max-w-prose text-sm text-ink-muted">
            Lectura del último reporte que expone el API. No se recalcula desde decisiones ni se dispara un
            despliegue.
          </p>
        </header>
        <p className="max-w-prose text-base leading-relaxed text-ink">{view.message}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <header className="border-b border-line pb-6">
        <p className="text-sm text-ink-muted">Puesto de control · Acme Demo Inc.</p>
        <h1 className="font-display mt-1 text-3xl text-ink">Métricas de evaluación</h1>
        <p className="mt-2 max-w-prose text-sm text-ink-muted">
          Lectura del último reporte que expone el API. No se recalcula desde decisiones ni se dispara un
          despliegue.
        </p>
      </header>

      <div className="space-y-3">
        <p
          className="font-display text-5xl leading-none text-ink sm:text-6xl"
          aria-label={`Pagos indebidos: ${formatMetricNumber(view.unsafe_pay)}`}
        >
          <span className="sr-only">Pagos indebidos: </span>
          {formatMetricNumber(view.unsafe_pay)}
        </p>
        <p className="text-sm text-ink-muted">
          Autonomía: {formatMetricNumber(view.autonomy_pct)} %
        </p>
        {view.blocked ? (
          <p className="max-w-prose text-sm leading-relaxed text-danger" role="status">
            {view.blockMessage}
          </p>
        ) : null}
      </div>
    </div>
  );
}
