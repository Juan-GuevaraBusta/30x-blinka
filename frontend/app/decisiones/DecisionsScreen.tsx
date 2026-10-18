"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ChevronRight, FileSearch, ListChecks, Upload } from "lucide-react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { DECISION_META, DecisionBadge } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { PageHeader } from "@/components/ui/PageHeader";
import { Table, TableWrap, Td, Th, THead, Tr } from "@/components/ui/Table";
import { cn } from "@/lib/cn";
import type { Decision, DecisionRecord, Extraction } from "@/lib/decision-types";
import { apiFetch } from "@/lib/session";
import {
  DECISION_LIST_FILTERS,
  DEFAULT_DECISION_LIST_FILTER,
  FILTER_CONTROL_LABELS,
  type DecisionListFilter,
  decisionMotivo,
  emptyStateMessage,
  filterToApiDecision,
  formatListAmount,
  formatListBeneficiary,
} from "@/lib/decisions-list";

import ChainIntegrityBadge from "./ChainIntegrityBadge";

const MONEY_NOTE =
  "Consultar esta lista no mueve dinero; solo refleja decisiones ya registradas.";

type FilterTone = "pay" | "stop" | "escalate" | "neutral";

const FILTER_TONES: Record<FilterTone, { active: string; icon: string; iconActive: string; bar: string }> = {
  pay: {
    active: "border-pay-200 bg-pay-50 text-pay-800 shadow-sm",
    icon: "bg-pay-50 text-pay-700",
    iconActive: "bg-pay-600 text-white",
    bar: "bg-pay-500",
  },
  stop: {
    active: "border-stop-200 bg-stop-50 text-stop-800 shadow-sm",
    icon: "bg-stop-50 text-stop-700",
    iconActive: "bg-stop-600 text-white",
    bar: "bg-stop-500",
  },
  escalate: {
    active: "border-escalate-200 bg-escalate-50 text-escalate-800 shadow-sm",
    icon: "bg-escalate-50 text-escalate-700",
    iconActive: "bg-escalate-600 text-white",
    bar: "bg-escalate-500",
  },
  neutral: {
    active: "border-brand-200 bg-brand-50 text-brand-800 shadow-sm",
    icon: "bg-brand-50 text-brand-700",
    iconActive: "bg-brand-600 text-white",
    bar: "bg-brand-500",
  },
};

type DecisionRow = {
  id: string;
  invoice_id: string;
  received_at: string;
  decision: Decision;
  summary: string;
  extracted?: Extraction;
};

function isDecisionRow(value: unknown): value is DecisionRow {
  if (!value || typeof value !== "object") return false;
  const row = value as Partial<DecisionRecord>;
  return (
    typeof row.id === "string" &&
    row.id.length > 0 &&
    typeof row.invoice_id === "string" &&
    row.invoice_id.length > 0 &&
    typeof row.received_at === "string" &&
    row.received_at.length > 0 &&
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
    rows.push({
      id: item.id,
      invoice_id: item.invoice_id,
      received_at: item.received_at,
      decision: item.decision,
      summary: item.summary,
      extracted: item.extracted,
    });
  }
  // Most recent first, regardless of which filter (or "todas") is active.
  return rows.sort((a, b) => b.received_at.localeCompare(a.received_at));
}

/** `decision: null` (the "todas" tab) omits the filter so the API returns every decision. */
async function fetchDecisions(decision: Decision | null): Promise<DecisionRow[]> {
  const query = decision ? `?decision=${decision}` : "";
  const res = await apiFetch(`/api/decisions${query}`, { cache: "no-store" });
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
      <PageHeader
        title="Decisiones registradas"
        icon={ListChecks}
        description={<p>{MONEY_NOTE}</p>}
      >
        <ChainIntegrityBadge />
      </PageHeader>

      <fieldset>
        <legend className="mb-3 text-eyebrow uppercase text-ink-muted">Filtrar por estado</legend>
        <div className="grid gap-3 sm:grid-cols-4">
          {DECISION_LIST_FILTERS.map((key) => {
            const active = filter === key;
            const apiDecision = filterToApiDecision(key);
            const Icon = apiDecision ? DECISION_META[apiDecision].icon : ListChecks;
            const tone = FILTER_TONES[apiDecision ? (DECISION_META[apiDecision].tone as FilterTone) : "neutral"];
            return (
              <button
                key={key}
                type="button"
                aria-pressed={active}
                onClick={() => setFilter(key)}
                className={cn(
                  "group relative flex items-center gap-3 overflow-hidden rounded-xl border bg-surface px-4 py-3 text-left text-sm font-semibold shadow-xs transition-all duration-200 focus-ring",
                  active ? tone.active : "border-line text-ink-muted hover:-translate-y-0.5 hover:shadow-sm",
                )}
              >
                <span
                  className={cn(
                    "inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors",
                    active ? tone.iconActive : tone.icon,
                  )}
                  aria-hidden="true"
                >
                  <Icon className="h-5 w-5" />
                </span>
                <span className="min-w-0 flex-1">
                  {FILTER_CONTROL_LABELS[key]}
                  {counts[key] !== undefined ? ` (${counts[key]})` : ""}
                </span>
                {active ? <span className={cn("absolute inset-x-0 bottom-0 h-1", tone.bar)} aria-hidden="true" /> : null}
              </button>
            );
          })}
        </div>
      </fieldset>

      {loading ? (
        <div className="space-y-2" role="status" aria-live="polite">
          <span className="sr-only">Cargando decisiones…</span>
          <p className="text-sm text-ink-muted" aria-hidden="true">
            Cargando decisiones…
          </p>
          {[0, 1, 2].map((n) => (
            <div key={n} className="skeleton h-14 w-full" aria-hidden="true" />
          ))}
        </div>
      ) : error ? (
        <AlertPanel>{error}</AlertPanel>
      ) : rows.length === 0 ? (
        <EmptyState
          icon={FileSearch}
          title={emptyStateMessage(filter)}
          action={
            <ButtonLink href="/subir" icon={<Upload className="h-4 w-4" aria-hidden="true" />}>
              Sube tu primera factura
            </ButtonLink>
          }
        />
      ) : (
        <>
          <div className="space-y-3 sm:hidden">
            {rows.map((row) => {
              return (
                <Link
                  key={row.id}
                  href={`/decisiones/${encodeURIComponent(row.id)}`}
                  className="block panel p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-md focus-ring animate-fade-up"
                >
                  <article>
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-mono text-sm font-semibold text-ink">{row.invoice_id}</p>
                      <DecisionBadge decision={row.decision} size="sm" />
                    </div>
                    <p className="mt-2 text-sm text-ink">
                      {formatListBeneficiary(row.extracted)} ·{" "}
                      <span className="font-mono font-semibold">{formatListAmount(row.extracted)}</span>
                    </p>
                    <p className="mt-2 line-clamp-2 text-sm text-ink-muted" title={decisionMotivo(row.summary)}>
                      {decisionMotivo(row.summary)}
                    </p>
                  </article>
                </Link>
              );
            })}
          </div>

          <TableWrap className="hidden animate-fade-up sm:block">
            <Table>
              <THead>
                <tr>
                  <Th>Factura</Th>
                  <Th>Beneficiario</Th>
                  <Th className="text-right">Monto</Th>
                  <Th>Estado</Th>
                  <Th>Motivo</Th>
                </tr>
              </THead>
              <tbody>
                {rows.map((row) => {
                  return (
                    <Tr key={row.id}>
                      <Td className="font-mono font-semibold">
                        <Link
                          href={`/decisiones/${encodeURIComponent(row.id)}`}
                          className="inline-flex items-center gap-1 rounded text-brand-700 hover:text-brand-800 hover:underline focus-ring"
                        >
                          {row.invoice_id}
                          <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                        </Link>
                      </Td>
                      <Td>{formatListBeneficiary(row.extracted)}</Td>
                      <Td className="text-right font-mono font-semibold tabular-nums">
                        {formatListAmount(row.extracted)}
                      </Td>
                      <Td>
                        <DecisionBadge decision={row.decision} size="sm" />
                      </Td>
                      <Td className="max-w-xs truncate text-ink-muted" title={decisionMotivo(row.summary)}>
                        {decisionMotivo(row.summary)}
                      </Td>
                    </Tr>
                  );
                })}
              </tbody>
            </Table>
          </TableWrap>
        </>
      )}
    </div>
  );
}
