"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { CheckResult, DecisionRecord } from "@/lib/decision-types";
import {
  EVIDENCE_NULL_LABEL,
  formatNullable,
  formatOnFail,
  hasCheckEvidence,
  isValidDecisionId,
  tracePresentation,
} from "@/lib/decision-present";

const I8_DISCLAIMER =
  "PAGAR es una decisión registrada. Esta pantalla no mueve dinero.";

const VERSIONS_NOTE =
  "Este registro conserva las versiones con las que se decidió. Cambiar reglas en /reglas no reescribe esta ficha.";

const MSG_NOT_FOUND = "No hay una decisión con ese identificador.";
const MSG_RATE_LIMITED =
  "Demasiadas solicitudes. Espera un momento y vuelve a abrir esta decisión.";

type LoadState =
  | { status: "loading" }
  | { status: "not_found" }
  | { status: "rate_limited" }
  | { status: "error"; message: string }
  | { status: "ready"; record: DecisionRecord };

async function loadDecision(id: string): Promise<LoadState> {
  if (!isValidDecisionId(id)) {
    return { status: "not_found" };
  }
  try {
    const res = await fetch(`/api/decisions/${encodeURIComponent(id)}`, {
      cache: "no-store",
    });
    if (res.status === 404) {
      return { status: "not_found" };
    }
    if (res.status === 429) {
      let detail: string | undefined;
      try {
        const body = (await res.json()) as { detail?: string };
        detail = body.detail;
      } catch {
        detail = undefined;
      }
      if (detail === "rate_limited") {
        return { status: "rate_limited" };
      }
      return { status: "rate_limited" };
    }
    if (!res.ok) {
      return {
        status: "error",
        message: `No se pudo cargar la decisión (HTTP ${res.status}).`,
      };
    }
    const record = (await res.json()) as DecisionRecord;
    return { status: "ready", record };
  } catch {
    return {
      status: "error",
      message: "No se pudo contactar con el servidor. Comprueba que el API esté en marcha.",
    };
  }
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

function FieldRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="grid gap-1 sm:grid-cols-[minmax(0,11rem)_1fr] sm:gap-4">
      <dt className="text-sm font-medium text-ink-muted">{label}</dt>
      <dd className="text-sm text-ink break-words">{value}</dd>
    </div>
  );
}

function resultTone(result: CheckResult["result"]): string {
  if (result === "OK") return "text-success";
  if (result === "FALLA") return "text-danger";
  return "text-ink-muted";
}

function decisionTone(decision: DecisionRecord["decision"]): string {
  if (decision === "PAGAR") return "text-success";
  if (decision === "FRENAR") return "text-danger";
  return "text-accent";
}

function CheckBlock({ check }: { check: CheckResult }) {
  const evidence = check.evidence;
  const showEvidence = hasCheckEvidence(evidence);

  return (
    <article className="rounded-md border border-line/80 bg-canvas/40 px-4 py-3">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="font-mono text-sm text-ink">{check.rule}</span>
        <span className="font-medium text-ink">{check.name}</span>
        <span className={`text-sm font-semibold ${resultTone(check.result)}`}>{check.result}</span>
      </div>
      <p className="mt-2 text-sm text-ink">{check.detail}</p>
      <p className="mt-2 text-sm text-ink-muted">
        Acción si falla: <span className="text-ink">{formatOnFail(check.on_fail ?? null)}</span>
      </p>
      <div className="mt-2 text-sm text-ink-muted">
        {showEvidence ? (
          <dl className="space-y-1">
            {evidence?.clause ? (
              <div>
                <dt className="inline font-medium">Cláusula: </dt>
                <dd className="inline text-ink">{evidence.clause}</dd>
              </div>
            ) : null}
            {evidence?.quote ? (
              <div>
                <dt className="inline font-medium">Cita: </dt>
                <dd className="inline text-ink">{evidence.quote}</dd>
              </div>
            ) : null}
          </dl>
        ) : (
          <p>{EVIDENCE_NULL_LABEL}</p>
        )}
      </div>
    </article>
  );
}

function RecordBody({ record }: { record: DecisionRecord }) {
  const extracted = record.extracted;
  const lines = extracted.lines ?? [];
  const spanEntries = Object.entries(extracted.source_spans ?? {});
  const traceView = tracePresentation(record.trace);

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-4 border-b border-line pb-6">
        <div>
          <p className="text-sm text-ink-muted">
            <Link
              href="/reglas"
              className="text-accent hover:underline focus:outline-none focus:ring-2 focus:ring-accent/40"
            >
              Reglas vigentes
            </Link>
            {" · "}
            Puesto de control · Acme Demo Inc.
          </p>
          <h1 className="font-display mt-1 text-3xl text-ink">Decisión {record.id}</h1>
          <p className="mt-2 max-w-prose text-sm text-ink-muted">
            Ficha de solo lectura del registro guardado. No se recalculan reglas ni se mueve dinero.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="rounded-md border border-line bg-surface px-4 py-3">
            <p className="text-xs text-ink-muted">Decisión registrada</p>
            <p className={`font-display text-2xl ${decisionTone(record.decision)}`}>
              {record.decision}
            </p>
            <p className="mt-2 text-xs leading-relaxed text-ink-muted">{I8_DISCLAIMER}</p>
          </div>
          <div className="rounded-md bg-ink px-4 py-3 text-surface">
            <p className="text-xs text-surface/70">Severidad (entero guardado)</p>
            <p className="font-mono text-2xl tracking-wide">{record.severity}</p>
          </div>
        </div>
      </header>

      <Section title="Identidad del registro">
        <dl className="space-y-3">
          <FieldRow label="Identificador" value={record.id} />
          <FieldRow label="Factura" value={record.invoice_id} />
          <FieldRow label="Recibida" value={record.received_at} />
          <FieldRow label="Decisión" value={record.decision} />
          <FieldRow label="Severidad" value={String(record.severity)} />
        </dl>
        <div className="mt-4 border-t border-line/60 pt-4">
          <p className="text-sm font-medium text-ink">Versiones con las que se decidió</p>
          <dl className="mt-2 space-y-2">
            <FieldRow label="Reglas" value={record.versions.rules_version} />
            <FieldRow label="Extractor" value={record.versions.model_extractor} />
            <FieldRow label="Verificador" value={record.versions.model_verifier} />
            <FieldRow label="JEV" value={record.versions.jev} />
          </dl>
          <p className="mt-3 text-xs leading-relaxed text-ink-muted">{VERSIONS_NOTE}</p>
        </div>
      </Section>

      <Section title="Datos leídos de la factura">
        <dl className="space-y-3">
          <FieldRow label="Beneficiario" value={formatNullable(extracted.beneficiary)} />
          <FieldRow label="Monto" value={formatNullable(extracted.amount)} />
          <FieldRow label="Moneda" value={formatNullable(extracted.currency)} />
          <FieldRow label="Monto en moneda base" value={formatNullable(extracted.amount_base)} />
          <FieldRow
            label="Tipo de cambio"
            value={
              extracted.fx
                ? `${extracted.fx.rate} (${extracted.fx.date})`
                : formatNullable(null)
            }
          />
          <FieldRow label="Vencimiento" value={formatNullable(extracted.due_date)} />
          <FieldRow label="Número de factura" value={formatNullable(extracted.invoice_number)} />
          <FieldRow label="Receptor" value={formatNullable(extracted.recipient)} />
          <FieldRow label="Área" value={formatNullable(extracted.department)} />
          <FieldRow label="Tipo de factura" value={formatNullable(extracted.invoice_type)} />
        </dl>
        <div className="mt-4">
          <p className="text-sm font-medium text-ink">Líneas</p>
          {lines.length === 0 ? (
            <p className="mt-2 text-sm text-ink-muted">sin líneas</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {lines.map((line, index) => (
                <li
                  key={`line-${index}`}
                  className="rounded-md border border-line/60 bg-canvas/30 px-3 py-2 text-sm"
                >
                  <p className="text-ink">{line.description}</p>
                  <p className="text-ink-muted">
                    Monto: {formatNullable(line.amount ?? null)}
                  </p>
                  <p className="text-ink-muted">
                    Cita en origen: {formatNullable(line.source_span ?? null)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="mt-4">
          <p className="text-sm font-medium text-ink">Citas de origen en el registro</p>
          {spanEntries.length === 0 ? (
            <p className="mt-2 text-sm text-ink-muted">sin citas de origen en el registro</p>
          ) : (
            <dl className="mt-2 space-y-2">
              {spanEntries.map(([key, text]) => (
                <div key={key} className="text-sm">
                  <dt className="font-medium text-ink-muted">{key}</dt>
                  <dd className="text-ink">{text}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      </Section>

      <Section title="Chequeos de reglas">
        {record.checks.length === 0 ? (
          <p className="text-sm text-ink-muted">sin chequeos en el registro</p>
        ) : (
          <div className="space-y-3">
            {record.checks.map((check) => (
              <CheckBlock key={`${check.rule}-${check.name}`} check={check} />
            ))}
          </div>
        )}
      </Section>

      <Section title="Explicación guardada">
        <div className="space-y-4 text-sm text-ink">
          <div>
            <p className="font-medium text-ink-muted">Resumen</p>
            <p className="mt-1">{record.summary}</p>
          </div>
          <div>
            <p className="font-medium text-ink-muted">Siguiente paso</p>
            <p className="mt-1">{record.next_step}</p>
          </div>
          <div>
            <p className="font-medium text-ink-muted">Aviso al administrador</p>
            <p className="mt-1">
              {record.admin_notice ?? "sin aviso al administrador"}
            </p>
          </div>
        </div>
      </Section>

      <Section title="Verificador y señales">
        <FieldRow
          label="Coherencia del verificador"
          value={record.verifier.consistent ? "consistente" : "no consistente"}
        />
        <div className="mt-4">
          <p className="text-sm font-medium text-ink">Hallazgos del verificador</p>
          {record.verifier.issues.length === 0 ? (
            <p className="mt-2 text-sm text-ink-muted">sin hallazgos del verificador</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {record.verifier.issues.map((issue) => (
                <li
                  key={`${issue.code}-${issue.kind}`}
                  className="rounded-md border border-line/60 px-3 py-2 text-sm"
                >
                  <p className="font-mono text-ink">{issue.code}</p>
                  <p className="text-ink-muted">Tipo: {issue.kind}</p>
                  <p className="text-ink-muted">
                    Evidencia: {formatNullable(issue.evidence ?? null)}
                  </p>
                  <p className="text-ink-muted">
                    Mensaje admin: {formatNullable(issue.admin_message ?? null)}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="mt-4">
          <p className="text-sm font-medium text-ink">Señales JEV</p>
          {record.jev_signals.length === 0 ? (
            <p className="mt-2 text-sm text-ink-muted">sin señales JEV en el registro</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {record.jev_signals.map((signal) => (
                <li key={signal.id} className="text-sm text-ink">
                  <span className="font-mono">{signal.id}</span>
                  {" · "}
                  respuesta {String(signal.answer)}
                  {" · "}
                  probabilidad {signal.probability}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div className="mt-4">
          <p className="text-sm font-medium text-ink">Eventos humanos</p>
          {record.human_events.length === 0 ? (
            <p className="mt-2 text-sm text-ink-muted">sin eventos humanos</p>
          ) : (
            <ul className="mt-2 space-y-2">
              {record.human_events.map((event, index) => (
                <li
                  key={`${event.at}-${index}`}
                  className="rounded-md border border-line/60 px-3 py-2 text-sm"
                >
                  <p className="text-ink">{event.author}</p>
                  <p className="text-ink-muted">{event.at}</p>
                  <p className="text-ink">{event.action}</p>
                  <p className="text-ink-muted">{event.reason}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </Section>

      <Section title="Traza de observabilidad">
        {traceView.kind === "link" ? (
          <p className="text-sm">
            <a
              href={traceView.href}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-accent hover:underline focus:outline-none focus:ring-2 focus:ring-accent/40"
            >
              {traceView.label}
            </a>
            <span className="mt-1 block break-all font-mono text-xs text-ink-muted">
              {traceView.href}
            </span>
          </p>
        ) : (
          <p className="text-sm text-ink-muted">{traceView.text}</p>
        )}
        {record.trace.langsmith_run_id ? (
          <p className="mt-3 text-sm text-ink-muted">
            Identificador de ejecución guardado:{" "}
            <span className="font-mono text-ink">{record.trace.langsmith_run_id}</span>
          </p>
        ) : null}
      </Section>
    </div>
  );
}

function ErrorPanel({ message }: { message: string }) {
  return (
    <div
      className="rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-danger"
      role="alert"
    >
      {message}
    </div>
  );
}

export default function DecisionDetailScreen({ decisionId }: { decisionId: string }) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const next = await loadDecision(decisionId);
      if (!cancelled) setState(next);
    })();
    return () => {
      cancelled = true;
    };
  }, [decisionId]);

  if (state.status === "loading") {
    return (
      <p className="text-ink-muted" role="status">
        Cargando decisión…
      </p>
    );
  }

  if (state.status === "not_found") {
    return <ErrorPanel message={MSG_NOT_FOUND} />;
  }

  if (state.status === "rate_limited") {
    return <ErrorPanel message={MSG_RATE_LIMITED} />;
  }

  if (state.status === "error") {
    return <ErrorPanel message={state.message} />;
  }

  return <RecordBody record={state.record} />;
}
