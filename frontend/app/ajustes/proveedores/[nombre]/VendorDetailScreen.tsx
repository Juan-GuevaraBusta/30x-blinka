"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { AlertPanel } from "@/components/ui/AlertPanel";
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

type RulesDocument = { payment_series?: unknown };

/** Mirrors `statusToneClass` (`lib/decisions-list.ts`) tones, applied to calendar period states. */
const PERIOD_STATE_TONE: Record<PeriodState, string> = {
  pagado: "text-success",
  pendiente: "text-accent",
  frenado: "text-danger",
  sin_factura: "text-ink-muted",
};

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; calendar: VendorSeriesCalendar | null };

function isPaymentSeriesArray(value: unknown): value is PaymentSeries[] {
  return Array.isArray(value);
}

async function loadVendorCalendar(vendorName: string): Promise<LoadState> {
  try {
    const [rulesRes, decisionsRes] = await Promise.all([
      fetch("/api/rules", { cache: "no-store" }),
      apiFetch("/api/decisions", { cache: "no-store" }),
    ]);
    if (!rulesRes.ok) {
      return { status: "error", message: `No se pudieron cargar las reglas (HTTP ${rulesRes.status}).` };
    }
    if (!decisionsRes.ok) {
      return {
        status: "error",
        message: `No se pudieron cargar las decisiones (HTTP ${decisionsRes.status}).`,
      };
    }
    const rulesDocument = (await rulesRes.json()) as RulesDocument;
    const decisions = (await decisionsRes.json()) as DecisionRecord[];
    const allSeries = isPaymentSeriesArray(rulesDocument.payment_series) ? rulesDocument.payment_series : [];
    const series = seriesForVendor(allSeries, vendorName);
    if (!series) {
      return { status: "ready", calendar: null };
    }
    const matching = decisions.filter((record) => record.extracted.beneficiary === vendorName);
    const todayIso = new Date().toISOString().slice(0, 10);
    return { status: "ready", calendar: buildVendorCalendar(series, matching, todayIso) };
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
      <p className="text-sm text-ink-muted" role="status">
        Cargando calendario…
      </p>
    );
  }

  if (state.status === "error") {
    return <AlertPanel>{state.message}</AlertPanel>;
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title={vendorName}
        description={
          <p>
            <Link href="/ajustes/proveedores" className="text-accent hover:underline focus-ring">
              Proveedores
            </Link>
          </p>
        }
      />

      {!state.calendar ? (
        <p className="text-sm text-ink-muted">Este proveedor no tiene un calendario de pagos.</p>
      ) : (
        <Section title="Calendario de la serie">
          <ul className="space-y-2">
            {state.calendar.periods.map((period) => (
              <li
                key={period.period}
                className="flex flex-wrap items-baseline justify-between gap-2 rounded-md border border-line/70 px-3 py-2"
              >
                <span className="font-mono text-sm text-ink">{period.period}</span>
                <span className={`text-sm font-medium ${PERIOD_STATE_TONE[period.state]}`}>
                  {PERIOD_STATE_LABELS[period.state]}
                </span>
                {period.invoiceNumber ? (
                  <span className="text-sm text-ink-muted">Factura {period.invoiceNumber}</span>
                ) : null}
                {period.decisionId ? (
                  <Link
                    href={`/decisiones/${encodeURIComponent(period.decisionId)}`}
                    className="text-sm text-accent hover:underline focus-ring"
                  >
                    Ver decisión
                  </Link>
                ) : null}
              </li>
            ))}
          </ul>
          <p className="mt-4 text-sm text-ink-muted">
            Total pagado: {state.calendar.totalPaid} {state.calendar.currency} de{" "}
            {state.calendar.totalCap ?? "sin tope"}
          </p>
        </Section>
      )}
    </div>
  );
}
