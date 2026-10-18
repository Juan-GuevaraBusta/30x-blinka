"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/ui/PageHeader";
import { HOW_IT_WORKS_STEPS, OVERVIEW_CARDS, OVERVIEW_EXPLANATION, parseDecisionCount } from "@/lib/overview";

type CardState = Record<string, { status: "loading" | "ready" | "error"; count: number | null }>;

function initialCardState(): CardState {
  const state: CardState = {};
  for (const card of OVERVIEW_CARDS) {
    state[card.key] = { status: "loading", count: null };
  }
  return state;
}

async function fetchCount(decision: string): Promise<number> {
  const res = await fetch(`/api/decisions?decision=${decision}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`HTTP_${res.status}`);
  }
  const body: unknown = await res.json();
  return parseDecisionCount(body);
}

export default function OverviewScreen() {
  const [cards, setCards] = useState<CardState>(initialCardState);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const results = await Promise.allSettled(
        OVERVIEW_CARDS.map(async (card) => {
          const count = await fetchCount(card.decision);
          return [card.key, count] as const;
        }),
      );
      if (cancelled) return;
      setCards((prev) => {
        const next = { ...prev };
        for (let i = 0; i < OVERVIEW_CARDS.length; i += 1) {
          const key = OVERVIEW_CARDS[i].key;
          const outcome = results[i];
          next[key] =
            outcome.status === "fulfilled"
              ? { status: "ready", count: outcome.value[1] }
              : { status: "error", count: null };
        }
        return next;
      });
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-10">
      <PageHeader title="Agente de pagos" description={<p>{OVERVIEW_EXPLANATION}</p>} />

      <section aria-labelledby="overview-counts-heading" className="space-y-4">
        <h2 id="overview-counts-heading" className="text-base font-semibold text-ink">
          Decisiones registradas
        </h2>
        <div className="grid gap-3 sm:grid-cols-3">
          {OVERVIEW_CARDS.map((card) => {
            const state = cards[card.key];
            return (
              <Link
                key={card.key}
                href={card.href}
                className="panel px-4 py-5 transition-colors hover:border-accent/30 focus-ring"
              >
                <p className="text-sm font-medium text-ink-muted">{card.label}</p>
                {state.status === "loading" ? (
                  <p className="mt-2 text-sm text-ink-muted" role="status">
                    Cargando…
                  </p>
                ) : state.status === "error" ? (
                  <p className="mt-2 text-sm text-danger" role="alert">
                    No se pudo cargar.
                  </p>
                ) : state.count === 0 ? (
                  <p className="mt-2 text-sm text-ink-muted" role="status">
                    Sin registros.
                  </p>
                ) : (
                  <p className="mt-2 font-mono text-3xl font-medium text-ink">{state.count}</p>
                )}
              </Link>
            );
          })}
        </div>
      </section>

      <section aria-labelledby="how-it-works-heading" className="space-y-4">
        <h2 id="how-it-works-heading" className="text-base font-semibold text-ink">
          Cómo funciona
        </h2>
        <ol className="grid gap-3 sm:grid-cols-2">
          {HOW_IT_WORKS_STEPS.map((step) => (
            <li key={step.title} className="rounded-xl border border-line bg-paper px-4 py-4 text-sm">
              <p className="font-medium text-ink">{step.title}</p>
              <p className="mt-1 text-ink-muted">{step.description}</p>
            </li>
          ))}
        </ol>
      </section>
    </div>
  );
}
