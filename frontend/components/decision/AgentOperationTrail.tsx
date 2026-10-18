import type { CheckResult, DecisionRecord, HumanEvent } from "@/lib/decision-types";
import {
  EVIDENCE_NULL_LABEL,
  formatNullable,
  formatOnFail,
  hasCheckEvidence,
  tracePresentation,
} from "@/lib/decision-present";
import { rulePlainExplanation } from "@/lib/rule-explanations";

function TrailStep({
  title,
  children,
  isLast = false,
}: {
  title: string;
  children: React.ReactNode;
  isLast?: boolean;
}) {
  return (
    <li className="relative flex gap-4 pb-8 last:pb-0">
      <div className="flex flex-col items-center">
        <span
          className="mt-1.5 size-2 shrink-0 rounded-full bg-accent ring-4 ring-accent/15"
          aria-hidden
        />
        {!isLast ? <span className="mt-2 w-px flex-1 bg-line" aria-hidden /> : null}
      </div>
      <div className="min-w-0 flex-1 pt-0">
        <h3 className="text-sm font-semibold text-ink">{title}</h3>
        <div className="mt-2 space-y-2 text-sm text-ink-muted">{children}</div>
      </div>
    </li>
  );
}

function CheckTrailItem({ check }: { check: CheckResult }) {
  const evidence = check.evidence;
  const showEvidence = hasCheckEvidence(evidence);
  const plainExplanation = rulePlainExplanation(check.rule);
  return (
    <div className="rounded-lg border border-line/80 bg-paper px-3 py-2">
      <p className="text-ink">
        <span className="font-mono text-xs">{check.rule}</span>
        <span className="text-ink-muted"> · </span>
        <span className="font-medium">{check.name}</span>
        <span className="text-ink-muted"> · </span>
        <span className="font-medium text-ink">{check.result}</span>
      </p>
      <p className="mt-1 text-ink">{check.detail}</p>
      {plainExplanation ? <p className="mt-1 text-xs text-ink-muted">{plainExplanation}</p> : null}
      <p className="mt-1 text-xs text-ink-muted">
        Si falla: {formatOnFail(check.on_fail ?? null)}
      </p>
      {showEvidence ? (
        <p className="mt-1 text-xs text-ink-muted">
          {evidence?.clause ? `Cláusula ${evidence.clause}. ` : null}
          {evidence?.quote ? `«${evidence.quote}»` : null}
        </p>
      ) : (
        <p className="mt-1 text-xs text-ink-muted">{EVIDENCE_NULL_LABEL}</p>
      )}
    </div>
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

  const steps: { key: string; title: string; body: React.ReactNode }[] = [
    {
      key: "read",
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
      title: "Chequeos de reglas",
      body: record.checks.length === 0 ? (
        <p>sin chequeos en el registro</p>
      ) : (
        <div className="space-y-2">
          {record.checks.map((check) => (
            <CheckTrailItem key={`${check.rule}-${check.name}`} check={check} />
          ))}
        </div>
      ),
    },
    {
      key: "jev",
      title: "Señales JEV",
      body:
        record.jev_signals.length === 0 ? (
          <p>sin señales JEV en el registro</p>
        ) : (
          <ul className="space-y-1">
            {record.jev_signals.map((signal) => (
              <li key={signal.id} className="font-mono text-xs text-ink">
                {signal.id} · respuesta {String(signal.answer)} · p={signal.probability}
              </li>
            ))}
          </ul>
        ),
    },
    {
      key: "verifier",
      title: "Verificador",
      body: (
        <>
          <p className="text-ink">
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
      title: "Decisión registrada",
      body: (
        <>
          <p className="text-base font-medium text-ink">{record.decision}</p>
          <p className="text-ink">{record.summary}</p>
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
      title: "Eventos humanos",
      body:
        record.human_events.length === 0 ? (
          <p>sin eventos humanos</p>
        ) : (
          <ul className="space-y-2">
            {record.human_events.map((event, index) => (
              <li key={`${event.at}-${index}`} className="rounded-lg bg-paper px-3 py-2 text-ink">
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
      title: "Traza de observabilidad",
      body: (
        <>
          {traceView.kind === "link" ? (
            <>
              <a
                href={traceView.href}
                target="_blank"
                rel="noopener noreferrer"
                className="font-medium text-accent hover:underline focus-ring"
              >
                {traceView.label}
              </a>
              <p className="break-all font-mono text-xs">{traceView.href}</p>
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
        <TrailStep key={step.key} title={step.title} isLast={index === steps.length - 1}>
          {step.body}
        </TrailStep>
      ))}
    </ol>
  );
}
