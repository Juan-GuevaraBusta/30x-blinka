"use client";

import { useEffect, useState } from "react";

import {
  BarChart3,
  CheckCircle2,
  ClipboardList,
  Gauge,
  ShieldCheck,
  ShieldX,
} from "lucide-react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { StatCard } from "@/components/ui/StatCard";
import {
  formatMetricNumber,
  presentEvaluationFromResponse,
  presentLiveMetricsFromResponse,
  type EvaluationPresentation,
  type LiveMetricsPresentation,
} from "@/lib/metrics-present";

const LIVE_INTRO =
  "Conteos de tu empresa calculados a partir de las decisiones guardadas. No lee reportes de eval/.";

const EVALUATION_INTRO =
  "Cifras de los artefactos de evaluación versionados en el repositorio. Cada figura muestra su archivo fuente; nada se recalcula aquí.";

async function fetchJson(url: string): Promise<{ status: number; body: unknown }> {
  const res = await fetch(url, { cache: "no-store" });
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    body = null;
  }
  return { status: res.status, body };
}

function LiveSection({ view }: { view: LiveMetricsPresentation }) {
  if (view.kind === "error") {
    return <AlertPanel>{view.message}</AlertPanel>;
  }
  if (view.kind === "empty") {
    return (
      <EmptyState icon={ClipboardList} title="Sin decisiones todavía" description={view.message} />
    );
  }
  const { metrics } = view;
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatCard
        label="Total de decisiones"
        icon={ClipboardList}
        tone="brand"
        value={<span>{metrics.total}</span>}
        hint={`PAGAR ${metrics.pagar} · FRENAR ${metrics.frenar} · ESCALAR ${metrics.escalar}`}
      />
      <StatCard
        label="Decididas automáticamente"
        icon={Gauge}
        tone="info"
        value={
          <span>
            {metrics.auto_decided_pct === null ? "—" : formatMetricNumber(metrics.auto_decided_pct)} %
          </span>
        }
        hint={
          <ProgressBar
            value={metrics.auto_decided_pct ?? 0}
            max={100}
            label="Decididas automáticamente"
            tone="info"
            className="mt-2"
          />
        }
      />
      <StatCard
        label="Aprobaciones pendientes"
        icon={ShieldX}
        tone={metrics.pending_approvals > 0 ? "escalate" : "pay"}
        value={<span>{metrics.pending_approvals}</span>}
        hint="ESCALAR sin evento de aprobación/rechazo humano"
      />
      <StatCard
        label="Aprobadas por humanos"
        icon={CheckCircle2}
        tone="pay"
        value={<span>{metrics.approved_by_humans}</span>}
        hint="Decisiones con al menos un evento aprobada_humano"
      />
    </div>
  );
}

function EvaluationSection({ view }: { view: EvaluationPresentation }) {
  if (view.kind === "error") {
    return <AlertPanel>{view.message}</AlertPanel>;
  }
  if (view.kind === "empty") {
    return (
      <EmptyState icon={BarChart3} title="Sin evidencia de evaluación" description={view.message} />
    );
  }
  return (
    <div className="space-y-3">
      {view.generated_at ? (
        <p className="text-xs text-ink-subtle">Generado: {view.generated_at}</p>
      ) : null}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {view.entries.map((entry) => (
          <StatCard
            key={entry.id}
            label={entry.label}
            icon={ShieldCheck}
            tone="brand"
            value={<span className="text-2xl">{String(entry.value)}</span>}
            hint={<code className="text-xs text-ink-subtle">{entry.source}</code>}
          />
        ))}
      </div>
    </div>
  );
}

export default function MetricasScreen() {
  const [loading, setLoading] = useState(true);
  const [liveView, setLiveView] = useState<LiveMetricsPresentation | null>(null);
  const [evaluationView, setEvaluationView] = useState<EvaluationPresentation | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [live, evaluation] = await Promise.all([
          fetchJson("/api/metrics/live"),
          fetchJson("/api/metrics/evaluation"),
        ]);
        if (!cancelled) {
          setLiveView(presentLiveMetricsFromResponse(live.status, live.body));
          setEvaluationView(presentEvaluationFromResponse(evaluation.status, evaluation.body));
        }
      } catch {
        if (!cancelled) {
          const message =
            "No se pudo leer las métricas. Compruebe la conexión con el servidor e intente recargar la página.";
          setLiveView({ kind: "error", message });
          setEvaluationView({ kind: "error", message });
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
        <span className="sr-only">Cargando métricas…</span>
        <p className="text-sm text-ink-muted" aria-hidden="true">
          Cargando métricas…
        </p>
        <div className="grid gap-4 sm:grid-cols-2" aria-hidden="true">
          <div className="skeleton h-36" />
          <div className="skeleton h-36" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <PageHeader title="Métricas" icon={BarChart3} description={<p>{LIVE_INTRO}</p>} />

      <section className="space-y-4" aria-labelledby="live-metrics-heading">
        <h2 id="live-metrics-heading" className="text-h3 text-ink">
          Operación de tu empresa (en vivo)
        </h2>
        {liveView ? <LiveSection view={liveView} /> : null}
      </section>

      <section className="space-y-4" aria-labelledby="evaluation-metrics-heading">
        <h2 id="evaluation-metrics-heading" className="text-h3 text-ink">
          Evaluación (evidencia versionada)
        </h2>
        <p className="max-w-prose text-sm text-ink-muted">{EVALUATION_INTRO}</p>
        {evaluationView ? <EvaluationSection view={evaluationView} /> : null}
      </section>
    </div>
  );
}
