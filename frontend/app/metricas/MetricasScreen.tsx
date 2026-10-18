"use client";

import { useEffect, useState } from "react";

import { BarChart3, Gauge, ShieldCheck, ShieldX } from "lucide-react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatCard } from "@/components/ui/StatCard";
import {
  formatMetricNumber,
  presentMetricsFromResponse,
  type MetricsPresentation,
} from "@/lib/metrics-present";

const METRICS_INTRO =
  "Lectura del último reporte que expone el API. No se recalcula desde decisiones ni se dispara un despliegue.";

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
      <div className="space-y-4" role="status">
        <span className="sr-only">Cargando métricas de evaluación…</span>
        <p className="text-sm text-ink-muted" aria-hidden="true">
          Cargando métricas de evaluación…
        </p>
        <div className="grid gap-4 sm:grid-cols-2" aria-hidden="true">
          <div className="skeleton h-36" />
          <div className="skeleton h-36" />
        </div>
      </div>
    );
  }

  if (!view || view.kind === "error") {
    return (
      <AlertPanel>
        {view?.kind === "error" ? view.message : "No hay datos de métricas para mostrar."}
      </AlertPanel>
    );
  }

  if (view.kind === "empty") {
    return (
      <div className="space-y-8">
        <PageHeader title="Métricas de evaluación" icon={BarChart3} description={<p>{METRICS_INTRO}</p>} />
        <EmptyState icon={BarChart3} title="Sin reporte de métricas" description={view.message} />
      </div>
    );
  }

  const safe = view.unsafe_pay === 0;
  return (
    <div className="space-y-8">
      <PageHeader title="Métricas de evaluación" icon={BarChart3} description={<p>{METRICS_INTRO}</p>} />

      <div className="grid gap-4 sm:grid-cols-2">
        <StatCard
          label="Pagos indebidos"
          icon={safe ? ShieldCheck : ShieldX}
          tone={safe ? "pay" : "stop"}
          className="animate-fade-up"
          value={
            <p
              className="text-5xl leading-none sm:text-6xl"
              aria-label={`Pagos indebidos: ${formatMetricNumber(view.unsafe_pay)}`}
            >
              <span className="sr-only">Pagos indebidos: </span>
              {formatMetricNumber(view.unsafe_pay)}
            </p>
          }
          hint={safe ? "Ningún pago fuera de reglas en el último reporte" : "Pagos fuera de reglas en el último reporte"}
        />
        <StatCard
          label="Autonomía"
          icon={Gauge}
          tone="info"
          className="animate-fade-up"
          value={<span>{formatMetricNumber(view.autonomy_pct)} %</span>}
          hint={
            <div className="space-y-2">
              <ProgressBar value={view.autonomy_pct} max={100} label="Autonomía" tone="info" className="mt-2" />
              <p className="text-sm text-ink-muted">Autonomía: {formatMetricNumber(view.autonomy_pct)} %</p>
            </div>
          }
        />
      </div>
      {view.blocked ? (
        <div className="max-w-prose rounded-lg border border-stop-200 bg-stop-50 px-4 py-3 text-sm leading-relaxed text-stop-800" role="status">
          {view.blockMessage}
        </div>
      ) : null}
    </div>
  );
}
