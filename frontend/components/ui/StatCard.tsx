import Link from "next/link";
import type { LucideIcon } from "lucide-react";
import { ArrowUpRight } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

export type StatTone = "pay" | "stop" | "escalate" | "info" | "brand";

const TONES: Record<StatTone, { card: string; icon: string; bar: string; value: string }> = {
  pay: { card: "hover:border-pay-200", icon: "bg-pay-100 text-pay-700", bar: "bg-pay-500", value: "text-pay-800" },
  stop: { card: "hover:border-stop-200", icon: "bg-stop-100 text-stop-700", bar: "bg-stop-500", value: "text-stop-800" },
  escalate: {
    card: "hover:border-escalate-200",
    icon: "bg-escalate-100 text-escalate-700",
    bar: "bg-escalate-500",
    value: "text-escalate-800",
  },
  info: { card: "hover:border-info-200", icon: "bg-info-100 text-info-700", bar: "bg-info-500", value: "text-info-800" },
  brand: { card: "hover:border-brand-200", icon: "bg-brand-100 text-brand-700", bar: "bg-brand-500", value: "text-brand-800" },
};

/** KPI card: label + big number + context line. Optional href makes the whole card a link. */
export function StatCard({
  label,
  value,
  hint,
  icon: Icon,
  tone = "brand",
  href,
  tag,
  className,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  icon?: LucideIcon;
  tone?: StatTone;
  href?: string;
  tag?: ReactNode;
  className?: string;
}) {
  const t = TONES[tone];
  const body = (
    <>
      <span className={cn("absolute inset-x-0 top-0 h-1 rounded-t-xl", t.bar)} aria-hidden="true" />
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          {Icon ? (
            <span className={cn("inline-flex h-9 w-9 items-center justify-center rounded-lg", t.icon)} aria-hidden="true">
              <Icon className="h-5 w-5" />
            </span>
          ) : null}
          <p className="text-sm font-semibold text-ink">{label}</p>
        </div>
        {tag ?? (href ? <ArrowUpRight className="h-4 w-4 text-ink-subtle transition-transform duration-200 group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-ink" aria-hidden="true" /> : null)}
      </div>
      <div className={cn("mt-4 font-mono text-4xl font-semibold tracking-tight", t.value)}>{value}</div>
      {hint ? <div className="mt-1 text-xs text-ink-muted">{hint}</div> : null}
    </>
  );
  const classes = cn(
    "group relative block overflow-hidden rounded-xl border border-line bg-surface p-5 shadow-sm transition-all duration-200",
    href && "hover:-translate-y-0.5 hover:shadow-md focus-ring",
    t.card,
    className,
  );
  return href ? (
    <Link href={href} className={classes}>
      {body}
    </Link>
  ) : (
    <div className={classes}>{body}</div>
  );
}
