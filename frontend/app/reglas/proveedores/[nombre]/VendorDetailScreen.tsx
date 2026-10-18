"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { ArrowLeft, ArrowUpRight, CalendarClock, CalendarDays, CheckCircle2, CircleDashed, Clock, FilePlus2, OctagonX, Store, type LucideIcon } from "lucide-react";

import { AlertPanel } from "@/components/ui/AlertPanel";
import { Badge, type BadgeTone } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ProgressBar } from "@/components/ui/ProgressBar";
import { PageHeader } from "@/components/ui/PageHeader";
import { Section } from "@/components/ui/Section";
import type { DecisionRecord } from "@/lib/decision-types";
import {
  buildVendorCalendar,
  PERIOD_STATE_LABELS,
  seriesForVendor,
  type PaymentSeries,
  type PeriodState,
  type VendorSeriesCalendar,
} from "@/lib/payment-series-calendar";
import { apiFetch } from "@/lib/session";
import { normalizeVendorKey } from "@/lib/agreement-form";
import { vendorProvenanceLabel } from "@/lib/vendor-aggregate";

type RulesDocument = { payment_series?: unknown };
type EffectiveRulesResponse = { rules: RulesDocument; provenance?: Record<string, string> };

/** Decision semantics applied to calendar period states: color + icon + text. */
const PERIOD_STATE_TONE: Record<PeriodState, { tone: BadgeTone; icon: LucideIcon; rail: string }> = {
  pagado: { tone: "pay", icon: CheckCircle2, rail: "bg-pay-500" },
  pendiente: { tone: "escalate", icon: Clock, rail: "bg-escalate-500" },
  frenado: { tone: "stop", icon: OctagonX, rail: "bg-stop-500" },
  sin_factura: { tone: "neutral", icon: CircleDashed, rail: "bg-line-strong" },
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; calendar: VendorSeriesCalendar | null; provenanceLabel: string | null };

function isPaymentSeriesArray(value: unknown): value is PaymentSeries[] {
  return Array.isArray(value);
}

async function loadVendorCalendar(vendorName: string): Promise<LoadState> {
  try {
    const [effectiveRes, decisionsRes] = await Promise.all([
      apiFetch("/api/rules/effective", { cache: "no-store" }),
      apiFetch("/api/decisions", { cache: "no-store" }),
    ]);
    if (!effectiveRes.ok) {
      return { status: "error", message: `No se pudieron cargar las reglas (HTTP ${effectiveRes.status}).` };
    }
    if (!decisionsRes.ok) {
      return {
        status: "error",
        message: `No se pudieron cargar las decisiones (HTTP ${decisionsRes.status}).`,
      };
    }
    const effective = (await effectiveRes.json()) as EffectiveRulesResponse;
    const decisions = (await decisionsRes.json()) as DecisionRecord[];
    const allSeries = isPaymentSeriesArray(effective.rules?.payment_series) ? effective.rules.payment_series : [];
    const series = seriesForVendor(allSeries, vendorName);

    const vendorKey = normalizeVendorKey(vendorName);
    const agreementVersion = effective.provenance?.[`payment_series:${vendorKey}`] ?? null;
    const provenanceLabel = vendorProvenanceLabel({
      name: vendorName,
      vendorKey,
      source: agreementVersion ? "agreement" : "base",
      agreementVersion,
      agreementKind: null,
      hasPaymentSeries: Boolean(series),
      hasVariablePricing: false,
    });

    if (!series) {
      return { status: "ready", calendar: null, provenanceLabel: agreementVersion ? provenanceLabel : null };
    }
    const matching = decisions.filter((record) => record.extracted.beneficiary === vendorName);
    const todayIso = new Date().toISOString().slice(0, 10);
    return {
      status: "ready",
      calendar: buildVendorCalendar(series, matching, todayIso),
      provenanceLabel: agreementVersion ? provenanceLabel : null,
    };
  } catch {
    return {
      status: "error",
      message: "No se pudo contactar con el servidor. Comprueba que el API esté en marcha.",
    };
  }
}

export default function VendorDetailScreen({ vendorNameParam }: { vendorNameParam: string }) {
  const vendorName = decodeURIComponent(vendorNameParam);
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const next = await loadVendorCalendar(vendorName);
      if (!cancelled) setState(next);
    })();
    return () => {
      cancelled = true;
    };
  }, [vendorName]);

  if (state.status === "loading") {
    return (
      <div className="space-y-3" role="status">
        <p className="text-sm text-ink-muted">Cargando calendario…</p>
        <div className="skeleton h-40" aria-hidden="true" />
      </div>
    );
  }

  if (state.status === "error") {
    return <AlertPanel>{state.message}</AlertPanel>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={vendorName}
        icon={Store}
        description={
          <>
            <p>
              <Link
                href="/reglas/proveedores"
                className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:underline focus-ring"
              >
                <ArrowLeft className="h-4 w-4" aria-hidden="true" />
                Proveedores
              </Link>
            </p>
            {state.provenanceLabel ? (
              <p>
                <Badge tone="brand">{state.provenanceLabel}</Badge>
              </p>
            ) : null}
          </>
        }
      />

      {!state.calendar ? (
        <EmptyState
          icon={CalendarClock}
          title="Este proveedor no tiene un calendario de pagos."
          action={
            <ButtonLink
              href={`/reglas/acuerdos/nuevo?proveedor=${encodeURIComponent(vendorName)}`}
              icon={<FilePlus2 className="h-4 w-4" aria-hidden="true" />}
            >
              Cree un acuerdo para empezar a programar sus pagos
            </ButtonLink>
          }
        />
      ) : (
        <Section title="Calendario de la serie" icon={CalendarDays}>
          <ul className="space-y-2">
            {state.calendar.periods.map((period) => {
              const tone = PERIOD_STATE_TONE[period.state];
              const Icon = tone.icon;
              return (
                <li
                  key={period.period}
                  className="relative flex flex-wrap items-center justify-between gap-3 overflow-hidden rounded-lg border border-line bg-surface py-2.5 pl-5 pr-3 transition-colors hover:bg-brand-50/50"
                >
                  <span className={`absolute inset-y-0 left-0 w-1 ${tone.rail}`} aria-hidden="true" />
                  <span className="font-mono text-sm font-semibold text-ink">{period.period}</span>
                  <Badge tone={tone.tone} icon={<Icon className="h-3.5 w-3.5" aria-hidden="true" />}>
                    {PERIOD_STATE_LABELS[period.state]}
                  </Badge>
                  {period.invoiceNumber ? (
                    <span className="text-sm text-ink-muted">Factura {period.invoiceNumber}</span>
                  ) : null}
                  {period.decisionId ? (
                    <Link
                      href={`/decisiones/${encodeURIComponent(period.decisionId)}`}
                      className="inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline focus-ring"
                    >
                      Ver decisión
                      <ArrowUpRight className="h-3.5 w-3.5" aria-hidden="true" />
                    </Link>
                  ) : null}
                </li>
              );
            })}
          </ul>
          <div className="mt-4 rounded-lg bg-surface-sunken p-4">
            <p className="text-sm font-medium text-ink">
              Total pagado:{" "}
              <span className="font-mono text-pay-800">
                {state.calendar.totalPaid} {state.calendar.currency}
              </span>{" "}
              de <span className="font-mono">{state.calendar.totalCap ?? "sin tope"}</span>
            </p>
            {typeof state.calendar.totalCap === "number" ? (
              <ProgressBar
                className="mt-3"
                tone="pay"
                label="Total pagado sobre el tope"
                value={Number(state.calendar.totalPaid)}
                max={state.calendar.totalCap}
              />
            ) : null}
          </div>
        </Section>
      )}
    </div>
  );
}
