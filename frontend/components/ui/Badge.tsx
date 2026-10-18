import { AlertTriangle, CheckCircle2, CircleDashed, CircleSlash, Info, OctagonX, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import type { CheckResultKind, Decision } from "@/lib/decision-types";

export type BadgeTone = "neutral" | "brand" | "pay" | "stop" | "escalate" | "info" | "signal" | "night";

const TONES: Record<BadgeTone, string> = {
  neutral: "border-line-strong bg-surface-sunken text-ink-muted",
  brand: "border-brand-200 bg-brand-50 text-brand-700",
  pay: "border-pay-200 bg-pay-50 text-pay-800",
  stop: "border-stop-200 bg-stop-50 text-stop-800",
  escalate: "border-escalate-200 bg-escalate-50 text-escalate-800",
  info: "border-info-200 bg-info-50 text-info-800",
  signal: "border-signal bg-signal-soft text-signal-ink",
  night: "border-night-line bg-night text-white",
};

const SIZES = {
  sm: "gap-1 px-2 py-0.5 text-2xs",
  md: "gap-1.5 px-2.5 py-1 text-xs",
  lg: "gap-2 px-3 py-1.5 text-sm",
};

export function Badge({
  tone = "neutral",
  size = "md",
  icon,
  children,
  className,
  ...rest
}: {
  tone?: BadgeTone;
  size?: keyof typeof SIZES;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
} & React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center whitespace-nowrap rounded-full border font-semibold",
        TONES[tone],
        SIZES[size],
        className,
      )}
      {...rest}
    >
      {icon}
      {children}
    </span>
  );
}

export const DECISION_META: Record<Decision, { tone: BadgeTone; icon: LucideIcon; label: string; verb: string }> = {
  PAGAR: { tone: "pay", icon: CheckCircle2, label: "PAGAR", verb: "Lista para pagar" },
  FRENAR: { tone: "stop", icon: OctagonX, label: "FRENAR", verb: "Pago frenado" },
  ESCALAR: { tone: "escalate", icon: AlertTriangle, label: "ESCALAR", verb: "Requiere revisión humana" },
};

/** Decision chip: color + icon + text, never color alone. */
export function DecisionBadge({
  decision,
  size = "md",
  className,
}: {
  decision: Decision | string | null | undefined;
  size?: keyof typeof SIZES;
  className?: string;
}) {
  const meta = decision && decision in DECISION_META ? DECISION_META[decision as Decision] : null;
  if (!meta) {
    return (
      <Badge tone="neutral" size={size} icon={<CircleDashed className="h-3.5 w-3.5" aria-hidden="true" />} className={className}>
        {decision ? String(decision) : "Sin decisión"}
      </Badge>
    );
  }
  const Icon = meta.icon;
  const iconSize = size === "lg" ? "h-4 w-4" : "h-3.5 w-3.5";
  return (
    <Badge tone={meta.tone} size={size} icon={<Icon className={iconSize} aria-hidden="true" />} className={cn("tracking-wide", className)}>
      {meta.label}
    </Badge>
  );
}

export const CHECK_META: Record<CheckResultKind, { tone: BadgeTone; icon: LucideIcon; label: string }> = {
  OK: { tone: "pay", icon: CheckCircle2, label: "OK" },
  FALLA: { tone: "stop", icon: CircleSlash, label: "FALLA" },
  INDETERMINADO: { tone: "escalate", icon: Info, label: "INDETERMINADO" },
};

export function CheckBadge({ result, size = "sm" }: { result: CheckResultKind | string; size?: keyof typeof SIZES }) {
  const meta = result in CHECK_META ? CHECK_META[result as CheckResultKind] : null;
  const Icon = meta?.icon ?? CircleDashed;
  return (
    <Badge tone={meta?.tone ?? "neutral"} size={size} icon={<Icon className="h-3.5 w-3.5" aria-hidden="true" />}>
      {meta?.label ?? result}
    </Badge>
  );
}

/** Live "pulse" dot for lightweight activity cues. */
export function PulseDot({ tone = "pay" }: { tone?: "pay" | "stop" | "escalate" | "info" | "signal" | "brand" }) {
  const color = {
    pay: "bg-pay-500",
    stop: "bg-stop-500",
    escalate: "bg-escalate-500",
    info: "bg-info-500",
    signal: "bg-signal",
    brand: "bg-brand-500",
  }[tone];
  return <span className={cn("inline-block h-2 w-2 animate-pulse-dot rounded-full", color)} aria-hidden="true" />;
}
