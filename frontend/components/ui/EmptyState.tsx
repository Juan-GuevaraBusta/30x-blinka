import { Inbox, type LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";

/** Empty state: illustration-like stacked icon, why it is empty, and the obvious next action. */
export function EmptyState({
  title,
  description,
  icon: Icon = Inbox,
  action,
  className,
}: {
  title: string;
  description?: React.ReactNode;
  icon?: LucideIcon;
  action?: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "flex flex-col items-center rounded-xl border border-dashed border-line-strong bg-surface/70 px-6 py-12 text-center animate-fade-up",
        className,
      )}
      role="status"
    >
      <div className="relative mb-5 h-20 w-20" aria-hidden="true">
        <span className="absolute inset-0 rotate-6 rounded-2xl bg-brand-100" />
        <span className="absolute inset-0 -rotate-6 rounded-2xl bg-signal-soft" />
        <span className="absolute inset-0 flex items-center justify-center rounded-2xl border border-line bg-surface shadow-md">
          <Icon className="h-8 w-8 text-brand-600" />
        </span>
      </div>
      <p className="text-h3 text-ink">{title}</p>
      {description ? <div className="mt-1.5 max-w-sm text-sm text-ink-muted">{description}</div> : null}
      {action ? <div className="mt-5">{action}</div> : null}
    </div>
  );
}
