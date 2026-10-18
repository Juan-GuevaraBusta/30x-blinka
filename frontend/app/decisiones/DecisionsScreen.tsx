"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import type { Decision, DecisionRecord } from "@/lib/decision-types";
import {
  DECISION_LIST_FILTERS,
  DEFAULT_DECISION_LIST_FILTER,
  FILTER_CONTROL_LABELS,
  type DecisionListFilter,
  decisionMotivo,
  emptyStateMessage,
  filterToApiDecision,
  rowStatusLabel,
  statusToneClass,
} from "@/lib/decisions-list";

const MONEY_NOTE =
  "Consultar esta lista no mueve dinero; solo refleja decisiones ya registradas.";

type DecisionRow = {
  id: string;
  invoice_id: string;
  decision: Decision;
  summary: string;
};

function isDecisionRow(value: unknown): value is DecisionRow {
  if (!value || typeof value !== "object") return false;
  const row = value as Partial<DecisionRecord>;
  return (
    typeof row.id === "string" &&
    row.id.length > 0 &&
    typeof row.invoice_id === "string" &&
    row.invoice_id.length > 0 &&
    (row.decision === "PAGAR" || row.decision === "ESCALAR" || row.decision === "FRENAR") &&
    typeof row.summary === "string" &&
    row.summary.length > 0
  );
}

function parseDecisionList(payload: unknown): DecisionRow[] {
  if (!Array.isArray(payload)) {
    throw new Error("INVALID_BODY");
  }
  const rows: DecisionRow[] = [];
  for (const item of payload) {
    if (!isDecisionRow(item)) {
      throw new Error("INVALID_BODY");
    }
    rows.push(item);
  }
  return rows;
}

async function fetchDecisions(decision: Decision): Promise<DecisionRow[]> {
  const res = await fetch(`/api/decisions?decision=${decision}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`HTTP_${res.status}`);
  }
  const body: unknown = await res.json();
  try {
    return parseDecisionList(body);
  } catch {
    throw new Error("INVALID_BODY");
  }
}

function fetchErrorMessage(err: unknown): string {
  if (err instanceof Error) {
    if (err.message.startsWith("HTTP_")) {
      const code = err.message.slice(5);
      return `No se pudo cargar el listado (HTTP ${code}).`;
    }
    if (err.message === "INVALID_BODY") {
      return "El servidor devolvió un formato inesperado (HTTP 200).";
    }
  }
  return "No se pudo cargar el listado. Compruebe la conexión e intente de nuevo.";
}

export default function DecisionsScreen({
  initialFilter = DEFAULT_DECISION_LIST_FILTER,
}: {
  initialFilter?: DecisionListFilter;
}) {
  const [filter, setFilter] = useState<DecisionListFilter>(initialFilter);
  const [rows, setRows] = useState<DecisionRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [counts, setCounts] = useState<Partial<Record<DecisionListFilter, number>>>({});

  // T6.7 (D057): per-tab counts are cheap on these small synthetic lists.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      const results = await Promise.allSettled(
        DECISION_LIST_FILTERS.map(async (key) => {
          const list = await fetchDecisions(filterToApiDecision(key));
          return [key, list.length] as const;
        }),
      );
      if (cancelled) return;
      const next: Partial<Record<DecisionListFilter, number>> = {};
      for (const result of results) {
        if (result.status === "fulfilled") {
          const [key, count] = result.value;
          next[key] = count;
        }
      }
      setCounts(next);
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const apiDecision = filterToApiDecision(filter);

    setLoading(true);
    setError(null);
    setRows([]);

    (async () => {
      try {
        const list = await fetchDecisions(apiDecision);
        if (cancelled) return;
        setRows(list);
      } catch (err) {
        if (cancelled) return;
        setError(fetchErrorMessage(err));
        setRows([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [filter]);

  return (
    <div className="space-y-8">
      <header className="border-b border-line pb-6">
        <p className="text-sm text-ink-muted">Puesto de control · Acme Demo Inc.</p>
        <h1 className="font-display mt-1 text-3xl text-ink">Decisiones registradas</h1>
        <p className="mt-2 max-w-prose text-sm text-ink-muted">{MONEY_NOTE}</p>
      </header>

      <fieldset>
        <legend className="mb-3 text-sm font-medium text-ink">Filtrar por estado</legend>
        <div className="flex flex-wrap gap-2">
          {DECISION_LIST_FILTERS.map((key) => {
            const active = filter === key;
            return (
              <button
                key={key}
                type="button"
                aria-pressed={active}
                onClick={() => setFilter(key)}
                className={`rounded-md border px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-accent/30 ${
                  active
                    ? "border-accent bg-surface text-ink shadow-sm ring-1 ring-accent/40"
                    : "border-line bg-surface/80 text-ink-muted hover:border-line hover:text-ink"
                }`}
              >
                {FILTER_CONTROL_LABELS[key]}
                {counts[key] !== undefined ? ` (${counts[key]})` : ""}
              </button>
            );
          })}
        </div>
      </fieldset>

      {loading ? (
        <p className="text-ink-muted" role="status">
          Cargando decisiones…
        </p>
      ) : error ? (
        <div
          className="rounded-md border border-danger/40 bg-danger/10 px-4 py-3 text-danger"
          role="alert"
        >
          {error}
        </div>
      ) : rows.length === 0 ? (
        <p className="text-ink-muted" role="status">
          {emptyStateMessage(filter)}
        </p>
      ) : (
        <>
          <div className="space-y-4 sm:hidden">
            {rows.map((row) => (
              <Link
                key={row.id}
                href={`/decisiones/${encodeURIComponent(row.id)}`}
                className="block rounded-md border border-line bg-surface/90 p-4 shadow-sm ring-1 ring-line/60 hover:border-accent focus:outline-none focus:ring-2 focus:ring-accent/40"
              >
                <article>
                  <p className="font-mono text-sm text-ink">{row.invoice_id}</p>
                  <p className={`mt-1 text-sm font-medium ${statusToneClass(row.decision)}`}>
                    {rowStatusLabel(row.decision)}
                  </p>
                  <p
                    className="mt-2 truncate text-sm text-ink-muted"
                    title={decisionMotivo(row.summary)}
                  >
                    {decisionMotivo(row.summary)}
                  </p>
                </article>
              </Link>
            ))}
          </div>

          <div className="hidden overflow-x-auto sm:block">
            <table className="w-full border-collapse text-left text-sm">
              <thead>
                <tr className="border-b border-line text-ink-muted">
                  <th scope="col" className="py-3 pr-4 font-medium">
                    Factura
                  </th>
                  <th scope="col" className="py-3 pr-4 font-medium">
                    Estado
                  </th>
                  <th scope="col" className="py-3 font-medium">
                    Motivo
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="border-b border-line/80">
                    <td className="py-3 pr-4 font-mono text-ink">
                      <Link
                        href={`/decisiones/${encodeURIComponent(row.id)}`}
                        className="hover:underline focus:outline-none focus:ring-2 focus:ring-accent/40"
                      >
                        {row.invoice_id}
                      </Link>
                    </td>
                    <td className={`py-3 pr-4 font-medium ${statusToneClass(row.decision)}`}>
                      {rowStatusLabel(row.decision)}
                    </td>
                    <td
                      className="max-w-md truncate py-3 text-ink-muted"
                      title={decisionMotivo(row.summary)}
                    >
                      {decisionMotivo(row.summary)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
