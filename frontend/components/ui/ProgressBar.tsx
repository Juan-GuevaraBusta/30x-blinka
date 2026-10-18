import { cn } from "@/lib/cn";

const TONES = { brand: "bg-brand-600", pay: "bg-pay-500", stop: "bg-stop-500", escalate: "bg-escalate-500", info: "bg-info-500" };

export function ProgressBar({
  value,
  max,
  label,
  tone = "brand",
  className,
}: {
  value: number;
  max: number;
  label: string;
  tone?: keyof typeof TONES;
  className?: string;
}) {
  const safeMax = max > 0 ? max : 1;
  const pct = Math.max(0, Math.min(100, (value / safeMax) * 100));
  return (
    <div
      className={cn("h-2.5 w-full overflow-hidden rounded-full bg-surface-sunken ring-1 ring-inset ring-line", className)}
      role="progressbar"
      aria-label={label}
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={value}
    >
      <div className={cn("h-full rounded-full transition-all duration-500 ease-out", TONES[tone])} style={{ width: `${pct}%` }} />
    </div>
  );
}
