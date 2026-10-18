import type { LucideIcon } from "lucide-react";

export function Section({
  title,
  description,
  children,
  id,
  icon: Icon,
  action,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  id?: string;
  icon?: LucideIcon;
  action?: React.ReactNode;
}) {
  return (
    <section id={id} className="panel p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          {Icon ? (
            <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-100 text-brand-700" aria-hidden="true">
              <Icon className="h-5 w-5" />
            </span>
          ) : null}
          <div>
            <h2 className="text-h3 text-ink">{title}</h2>
            {description ? <p className="mt-1 text-sm text-ink-muted">{description}</p> : null}
          </div>
        </div>
        {action ? <div className="shrink-0">{action}</div> : null}
      </div>
      <div className="mt-4 space-y-4">{children}</div>
    </section>
  );
}
