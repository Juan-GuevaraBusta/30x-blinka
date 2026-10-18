"use client";

import { useEffect, useState } from "react";

import { CheckCircle2, FileSearch, FileUp, Inbox, OctagonX, ScrollText, Sparkles, type LucideIcon, Hourglass } from "lucide-react";

import { DECISION_META, DecisionBadge, PulseDot } from "@/components/ui/Badge";
import { ButtonLink } from "@/components/ui/Button";
import { WORKSPACE_EYEBROW } from "@/components/ui/PageHeader";
import { StatCard, type StatTone } from "@/components/ui/StatCard";
import type { Decision } from "@/lib/decision-types";
import { useMe } from "@/lib/me";
import { HOW_IT_WORKS_STEPS, OVERVIEW_CARDS, OVERVIEW_EXPLANATION, parseDecisionCount } from "@/lib/overview";
import { apiFetch } from "@/lib/session";

const CARD_TONES: Record<Decision, { tone: StatTone; icon: LucideIcon; hint: string }> = {
  ESCALAR: { tone: "escalate", icon: Hourglass, hint: "Esperan una persona aprobadora" },
  FRENAR: { tone: "stop", icon: OctagonX, hint: "Bloqueadas por una regla" },
  PAGAR: { tone: "pay", icon: CheckCircle2, hint: "Cumplen todas las reglas" },
};

const HERO_BARS: Record<Decision, string> = { PAGAR: "bg-pay-500", ESCALAR: "bg-escalate-500", FRENAR: "bg-stop-500" };

const STEP_ICONS: LucideIcon[] = [Inbox, FileSearch, ScrollText, CheckCircle2];
const STEP_TONES = [
  "bg-info-100 text-info-700",
  "bg-brand-100 text-brand-700",
  "bg-escalate-100 text-escalate-700",
  "bg-pay-100 text-pay-700",
];

type CardState = Record<string, { status: "loading" | "ready" | "error"; count: number | null }>;

function initialCardState(): CardState {
  const state: CardState = {};
  for (const card of OVERVIEW_CARDS) {
    state[card.key] = { status: "loading", count: null };
  }
  return state;
}

async function fetchCount(decision: string): Promise<number> {
  const res = await apiFetch(`/api/decisions?decision=${decision}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(`HTTP_${res.status}`);
  }
  const body: unknown = await res.json();
  return parseDecisionCount(body);
}

export default function OverviewScreen() {
  const [cards, setCards] = useState<CardState>(initialCardState);
  const companyName = useMe()?.company?.name;

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
      <section
        className="relative overflow-hidden rounded-2xl bg-night px-6 py-8 text-white shadow-lg animate-fade-up sm:px-10 sm:py-10"
        aria-labelledby="overview-hero-heading"
      >
        <div className="pointer-events-none absolute inset-0 bg-grid-night opacity-40" aria-hidden="true" />
        <div
          className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-brand-500/40 blur-3xl"
          aria-hidden="true"
        />
        <div
          className="pointer-events-none absolute -bottom-28 right-40 h-56 w-56 rounded-full bg-signal/20 blur-3xl"
          aria-hidden="true"
        />
        <div className="relative grid gap-8 lg:grid-cols-[1.4fr_1fr] lg:items-center">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-night-line bg-night-soft px-3 py-1 text-xs font-semibold text-brand-100">
              <PulseDot tone="signal" />
              {companyName ? `${WORKSPACE_EYEBROW} · ${companyName}` : WORKSPACE_EYEBROW}
            </p>
            <h1 id="overview-hero-heading" className="mt-4 text-display text-white">
              Agente de pagos
            </h1>
            <p className="mt-4 max-w-prose text-sm leading-relaxed text-brand-100">{OVERVIEW_EXPLANATION}</p>
            <div className="mt-6 flex flex-wrap gap-3">
              <ButtonLink href="/subir" variant="signal" icon={<FileUp className="h-4 w-4" aria-hidden="true" />}>
                Subir factura
              </ButtonLink>
              <ButtonLink
                href="/decisiones"
                variant="ghost"
                className="border border-night-line text-brand-100 hover:bg-white/10 hover:text-white"
                icon={<ScrollText className="h-4 w-4" aria-hidden="true" />}
              >
                Ver decisiones
              </ButtonLink>
            </div>
          </div>
          <ul className="grid gap-2.5" aria-hidden="true">
            {(["PAGAR", "ESCALAR", "FRENAR"] as const).map((decision, index) => (
              <li
                key={decision}
                className="flex items-center justify-between gap-3 rounded-xl border border-night-line bg-night-soft/80 px-4 py-3 backdrop-blur animate-fade-up"
                style={{ animationDelay: `${120 + index * 90}ms` }}
              >
                <span className="flex items-center gap-3">
                  <span className={`h-8 w-1 rounded-full ${HERO_BARS[decision]}`} />
                  <span>
                    <span className="block font-mono text-xs text-brand-200">factura · {DECISION_META[decision].verb.toLowerCase()}</span>
                  </span>
                </span>
                <DecisionBadge decision={decision} size="sm" />
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section aria-labelledby="overview-counts-heading" className="space-y-4">
        <div className="flex items-end justify-between gap-4">
          <h2 id="overview-counts-heading" className="text-h2 text-ink">
            Decisiones registradas
          </h2>
          <span className="text-xs text-ink-muted">Total histórico de la empresa</span>
        </div>
        <div className="grid gap-4 sm:grid-cols-3">
          {OVERVIEW_CARDS.map((card) => {
            const state = cards[card.key];
            const tone = CARD_TONES[card.decision];
            return (
              <StatCard
                key={card.key}
                href={card.href}
                label={card.label}
                tone={tone.tone}
                icon={tone.icon}
                tag={<DecisionBadge decision={card.decision} size="sm" />}
                value={
                  state.status === "loading" ? (
                    <span className="skeleton block h-10 w-16" role="status" aria-label="Cargando…" />
                  ) : state.status === "error" ? (
                    <span className="block font-sans text-sm font-medium text-stop-700" role="alert">
                      No se pudo cargar.
                    </span>
                  ) : state.count === 0 ? (
                    <span className="block font-sans text-sm font-medium text-ink-muted" role="status">
                      Sin registros.
                    </span>
                  ) : (
                    state.count
                  )
                }
                hint={tone.hint}
              />
            );
          })}
        </div>
      </section>

      <section aria-labelledby="how-it-works-heading" className="space-y-4">
        <h2 id="how-it-works-heading" className="text-h2 text-ink">
          Cómo funciona
        </h2>
        <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {HOW_IT_WORKS_STEPS.map((step, index) => {
            const Icon = STEP_ICONS[index] ?? Sparkles;
            return (
              <li
                key={step.title}
                className="group relative rounded-xl border border-line bg-surface p-5 text-sm shadow-sm transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-200 hover:shadow-md"
              >
                <div className="flex items-center justify-between">
                  <span
                    className={`inline-flex h-10 w-10 items-center justify-center rounded-xl ${STEP_TONES[index] ?? STEP_TONES[0]}`}
                    aria-hidden="true"
                  >
                    <Icon className="h-5 w-5" />
                  </span>
                  <span className="font-mono text-2xs font-semibold text-ink-subtle" aria-hidden="true">
                    0{index + 1}
                  </span>
                </div>
                <p className="mt-4 font-semibold text-ink">{step.title}</p>
                <p className="mt-1 leading-relaxed text-ink-muted">{step.description}</p>
              </li>
            );
          })}
        </ol>
      </section>
    </div>
  );
}
