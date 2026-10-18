import { AlertTriangle, CheckCircle2, Info, OctagonAlert, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";

export type AlertTone = "danger" | "neutral" | "success" | "warning" | "info";

const TONES: Record<AlertTone, { box: string; icon: LucideIcon; iconColor: string }> = {
  danger: { box: "border-stop-200 bg-stop-50 text-stop-800", icon: OctagonAlert, iconColor: "text-stop-600" },
  warning: { box: "border-escalate-200 bg-escalate-50 text-escalate-800", icon: AlertTriangle, iconColor: "text-escalate-600" },
  success: { box: "border-pay-200 bg-pay-50 text-pay-800", icon: CheckCircle2, iconColor: "text-pay-600" },
  info: { box: "border-info-200 bg-info-50 text-info-800", icon: Info, iconColor: "text-info-600" },
  neutral: { box: "border-line bg-surface-sunken text-ink", icon: Info, iconColor: "text-ink-muted" },
};

/** Alert with icon + text. `role="alert"` only for problems; informational tones use `status`. */
export function AlertPanel({
  children,
  tone = "danger",
  title,
  className,
}: {
  children: React.ReactNode;
  tone?: AlertTone;
  title?: React.ReactNode;
  className?: string;
}) {
  const t = TONES[tone];
  const Icon = t.icon;
  return (
    <div
      className={cn("flex gap-3 rounded-lg border px-4 py-3 text-sm animate-fade-up", t.box, className)}
      role={tone === "danger" || tone === "warning" ? "alert" : "status"}
    >
      <Icon className={cn("mt-0.5 h-4 w-4 shrink-0", t.iconColor)} aria-hidden="true" />
      <div className="min-w-0 flex-1">
        {title ? <p className="font-semibold">{title}</p> : null}
        <div className={title ? "mt-0.5" : undefined}>{children}</div>
      </div>
    </div>
  );
}

export { AlertPanel as Alert };
