import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";

export type CardTone = "default" | "brand" | "night" | "pay" | "stop" | "escalate" | "info" | "sunken";

const TONES: Record<CardTone, string> = {
  default: "border-line bg-surface shadow-sm",
  sunken: "border-line bg-surface-sunken",
  brand: "border-brand-200 bg-brand-50",
  night: "border-night-line bg-night text-white shadow-lg",
  pay: "border-pay-200 bg-pay-50",
  stop: "border-stop-200 bg-stop-50",
  escalate: "border-escalate-200 bg-escalate-50",
  info: "border-info-200 bg-info-50",
};

type CardProps = ComponentProps<"div"> & { tone?: CardTone; padded?: boolean; interactive?: boolean };

export function Card({ tone = "default", padded = true, interactive = false, className, ...rest }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border",
        TONES[tone],
        padded && "p-5 sm:p-6",
        interactive && "transition-all duration-200 hover:-translate-y-0.5 hover:border-brand-300 hover:shadow-md",
        className,
      )}
      {...rest}
    />
  );
}

export function CardHeader({
  title,
  description,
  icon,
  action,
}: {
  title: React.ReactNode;
  description?: React.ReactNode;
  icon?: React.ReactNode;
  action?: React.ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        {icon ? (
          <span className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700" aria-hidden="true">
            {icon}
          </span>
        ) : null}
        <div>
          <h2 className="text-h3 text-ink">{title}</h2>
          {description ? <p className="mt-1 text-sm text-ink-muted">{description}</p> : null}
        </div>
      </div>
      {action ? <div className="shrink-0">{action}</div> : null}
    </div>
  );
}
