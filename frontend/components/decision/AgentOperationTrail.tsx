import {
  Activity,
  BrainCircuit,
  ExternalLink,
  FileText,
  Gavel,
  ListChecks,
  ShieldCheck,
  UserCheck,
  type LucideIcon,
} from "lucide-react";

import { CHECK_META, CheckBadge, DecisionBadge } from "@/components/ui/Badge";
import { buttonClass } from "@/components/ui/Button";
import { cn } from "@/lib/cn";
import type { CheckResult, CheckResultKind, DecisionRecord, HumanEvent } from "@/lib/decision-types";
import {
  EVIDENCE_NULL_LABEL,
  formatNullable,
  formatOnFail,
  hasCheckEvidence,
  tracePresentation,
} from "@/lib/decision-present";
import { rulePlainExplanation } from "@/lib/rule-explanations";

const NODE_TONES: Record<string, { node: string; ring: string; card: string }> = {
  pay: { node: "bg-pay-600 text-white", ring: "ring-pay-100", card: "border-pay-200 bg-pay-50/60" },
  stop: { node: "bg-stop-600 text-white", ring: "ring-stop-100", card: "border-stop-200 bg-stop-50/60" },
  escalate: {
    node: "bg-escalate-500 text-white",
    ring: "ring-escalate-100",
    card: "border-escalate-200 bg-escalate-50/60",
  },
  neutral: { node: "bg-ink-subtle text-white", ring: "ring-line", card: "border-line bg-surface-sunken" },
};

function TrailStep({
  title,
  icon: Icon,
  children,
  isLast = false,
}: {
  title: string;
  icon: LucideIcon;
  children: React.ReactNode;
  isLast?: boolean;
}) {
  return (
    <li className="relative flex gap-4 pb-8 last:pb-0 animate-fade-up">
      <div className="flex flex-col items-center">
        <span
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-night text-signal shadow-sm ring-4 ring-brand-50"
          aria-hidden
        >
          <Icon className="h-4 w-4" />
        </span>
        {!isLast ? (
          <span className="mt-2 w-0.5 flex-1 rounded-full bg-gradient-to-b from-brand-200 to-line" aria-hidden />
        ) : null}
      </div>
      <div className="min-w-0 flex-1 pt-1.5">
        <h3 className="text-h3 text-ink">{title}</h3>
        <div className="mt-3 space-y-2 text-sm text-ink-muted">{children}</div>
      </div>
    </li>
  );
}

function CheckTrailItem({ check, isLast }: { check: CheckResult; isLast: boolean }) {
  const evidence = check.evidence;
  const showEvidence = hasCheckEvidence(evidence);
  const plainExplanation = rulePlainExplanation(check.rule);
  const meta = check.result in CHECK_META ? CHECK_META[check.result as CheckResultKind] : null;
  const tone = NODE_TONES[meta?.tone ?? "neutral"] ?? NODE_TONES.neutral;
  const NodeIcon = meta?.icon;
  return (
    <li className="relative flex gap-3 pb-3 last:pb-0">
      <div className="flex flex-col items-center">
        <span
          className={cn("mt-2 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full ring-4", tone.node, tone.ring)}
          aria-hidden
        >
          {NodeIcon ? <NodeIcon className="h-3.5 w-3.5" /> : null}
        </span>
        {!isLast ? <span className="mt-1 w-px flex-1 bg-line-strong" aria-hidden /> : null}
      </div>
      <div className={cn("min-w-0 flex-1 rounded-lg border px-3.5 py-3 transition-shadow hover:shadow-sm", tone.card)}>
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-ink">
            <span className="rounded bg-night px-1.5 py-0.5 font-mono text-2xs font-semibold text-signal">{check.rule}</span>
            <span className="text-ink-muted"> · </span>
            <span className="font-semibold">{check.name}</span>
          </p>
          <CheckBadge result={check.result} />
        </div>
        <p className="mt-2 text-ink">{check.detail}</p>
        {plainExplanation ? <p className="mt-1 text-xs text-ink-muted">{plainExplanation}</p> : null}
        <p className="mt-1 text-xs text-ink-muted">
          Si falla: <span className="font-semibold text-ink">{formatOnFail(check.on_fail ?? null)}</span>
        </p>
        {showEvidence ? (
          <p className="mt-2 border-l-2 border-brand-300 pl-2 text-xs italic text-ink-muted">
            {evidence?.clause ? `Cláusula ${evidence.clause}. ` : null}
            {evidence?.quote ? `«${evidence.quote}»` : null}
          </p>
        ) : (
          <p className="mt-1 text-xs text-ink-subtle">{EVIDENCE_NULL_LABEL}</p>
        )}
      </div>
    </li>
  );
}

function humanActionLabel(action: HumanEvent["action"]): string {
  if (action === "aprobada_humano") return "Aprobada por humano";
  return "Rechazada por humano";
}

export function AgentOperationTrail({ record }: { record: DecisionRecord }) {
  const extracted = record.extracted;
  const traceView = tracePresentation(record.trace);
  const spanEntries = Object.entries(extracted.source_spans ?? {});
  const lines = extracted.lines ?? [];

  const steps: { key: string; title: string; icon: LucideIcon; body: React.ReactNode }[] = [
    {
      key: "read",
      icon: FileText,
      title: "Lectura de la factura",
      body: (
        <>
          <p className="text-ink">
            Beneficiario {formatNullable(extracted.beneficiary)} · Monto{" "}
            {formatNullable(extracted.amount)}
            {extracted.currency ? ` ${extracted.currency}` : ""}
            {extracted.amount_base != null ? ` (base ${extracted.amount_base})` : ""}
          </p>
          <p>
            Vence {formatNullable(extracted.due_date)} · Nº{" "}
            {formatNullable(extracted.invoice_number)}
          </p>
          {lines.length > 0 ? (
            <ul className="space-y-1">
              {lines.map((line, index) => (
                <li key={`line-${index}`} className="text-xs">
                  {line.description} — {formatNullable(line.amount ?? null)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs">sin líneas en el registro</p>
          )}
          {spanEntries.length > 0 ? (
            <dl className="space-y-1 text-xs">
              {spanEntries.map(([key, text]) => (
                <div key={key}>
                  <dt className="font-medium text-ink">{key}</dt>
                  <dd>{text}</dd>
                </div>
              ))}
            </dl>
          ) : (
            <p className="text-xs">sin citas de origen en el registro</p>
          )}
        </>
      ),
    },
    {
      key: "checks",
      icon: ListChecks,
      title: "Chequeos de reglas",
      body: record.checks.length === 0 ? (
        <p>sin chequeos en el registro</p>
      ) : (
        <ol className="list-none" aria-label="Chequeos de reglas">
          {record.checks.map((check, index) => (
            <CheckTrailItem
              key={`${check.rule}-${check.name}`}
              check={check}
              isLast={index === record.checks.length - 1}
            />
          ))}
        </ol>
      ),
    },
    {
      key: "jev",
      icon: BrainCircuit,
      title: "Señales JEV",
      body:
        record.jev_signals.length === 0 ? (
          <p>sin señales JEV en el registro</p>
        ) : (
          <ul className="space-y-1">
            {record.jev_signals.map((signal) => (
              <li key={signal.id} className="rounded-md bg-surface-sunken px-2.5 py-1.5 font-mono text-xs text-ink">
                {signal.id} · respuesta {String(signal.answer)} · p={signal.probability}
              </li>
            ))}
          </ul>
        ),
    },
    {
      key: "verifier",
      icon: ShieldCheck,
      title: "Verificador",
      body: (
        <>
          <p
            className={cn(
              "inline-flex items-center gap-1.5 font-semibold",
              record.verifier.consistent ? "text-pay-700" : "text-stop-700",
            )}
          >
            <ShieldCheck className="h-4 w-4" aria-hidden />
            {record.verifier.consistent ? "Coherente con el registro." : "No coherente."}
          </p>
          {record.verifier.issues.length === 0 ? (
            <p>sin hallazgos del verificador</p>
          ) : (
            <ul className="space-y-2">
              {record.verifier.issues.map((issue) => (
                <li key={`${issue.code}-${issue.kind}`} className="text-xs text-ink">
                  <span className="font-mono">{issue.code}</span> ({issue.kind})
                  {issue.evidence ? ` — ${issue.evidence}` : null}
                  {issue.admin_message ? ` — ${issue.admin_message}` : null}
                </li>
              ))}
            </ul>
          )}
        </>
      ),
    },
    {
      key: "decision",
      icon: Gavel,
      title: "Decisión registrada",
      body: (
        <>
          <div className="rounded-xl border border-line bg-surface p-4 shadow-sm">
            <DecisionBadge decision={record.decision} size="lg" />
            <p className="mt-3 text-ink">{record.summary}</p>
          </div>
          <p>
            Siguiente paso: <span className="text-ink">{record.next_step}</span>
          </p>
          <p>
            Aviso al administrador:{" "}
            <span className="text-ink">
              {record.admin_notice ?? "sin aviso al administrador"}
            </span>
          </p>
        </>
      ),
    },
    {
      key: "human",
      icon: UserCheck,
      title: "Eventos humanos",
      body:
        record.human_events.length === 0 ? (
          <p>sin eventos humanos</p>
        ) : (
          <ul className="space-y-2">
            {record.human_events.map((event, index) => (
              <li
                key={`${event.at}-${index}`}
                className={cn(
                  "rounded-lg border px-3 py-2 text-ink",
                  event.action === "aprobada_humano" ? "border-pay-200 bg-pay-50" : "border-stop-200 bg-stop-50",
                )}
              >
                <p className="font-medium">{humanActionLabel(event.action)}</p>
                <p className="text-xs text-ink-muted">
                  {event.author} · {event.at}
                </p>
                <p className="mt-1">{event.reason}</p>
              </li>
            ))}
          </ul>
        ),
    },
    {
      key: "trace",
      icon: Activity,
      title: "Traza de observabilidad",
      body: (
        <>
          {traceView.kind === "link" ? (
            <>
              <a
                href={traceView.href}
                target="_blank"
                rel="noopener noreferrer"
                aria-label={traceView.label}
                title={traceView.label}
                className={buttonClass("primary", "md")}
              >
                <Activity className="h-4 w-4" aria-hidden />
                Ver traza en LangSmith
                <ExternalLink className="h-3.5 w-3.5" aria-hidden />
              </a>
              <p className="break-all font-mono text-xs text-ink-subtle">{traceView.href}</p>
            </>
          ) : (
            <p>{traceView.text}</p>
          )}
          {record.trace.langsmith_run_id ? (
            <p className="mt-2 font-mono text-xs text-ink">
              Identificador de ejecución guardado: {record.trace.langsmith_run_id}
            </p>
          ) : null}
        </>
      ),
    },
  ];

  return (
    <ol className="list-none" aria-label="Historial de operaciones del agente">
      {steps.map((step, index) => (
        <TrailStep key={step.key} title={step.title} icon={step.icon} isLast={index === steps.length - 1}>
          {step.body}
        </TrailStep>
      ))}
    </ol>
  );
}
