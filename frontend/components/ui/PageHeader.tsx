"use client";

import type { LucideIcon } from "lucide-react";

import { cn } from "@/lib/cn";
import { useMe } from "@/lib/me";

export const WORKSPACE_EYEBROW = "Puesto de control";

export function PageHeader({
  title,
  description,
  children,
  bordered = true,
  icon: Icon,
  actions,
  eyebrow,
}: {
  title: string;
  description?: React.ReactNode;
  children?: React.ReactNode;
  bordered?: boolean;
  icon?: LucideIcon;
  actions?: React.ReactNode;
  eyebrow?: string;
}) {
  const companyName = useMe()?.company?.name;
  const base = eyebrow ?? WORKSPACE_EYEBROW;
  return (
    <header className={cn("animate-fade-up", bordered ? "border-b border-line pb-6" : "pb-2")}>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-4">
          {Icon ? (
            <span
              className="hidden h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-night text-signal shadow-md sm:inline-flex"
              aria-hidden="true"
            >
              <Icon className="h-6 w-6" />
            </span>
          ) : null}
          <div className="min-w-0">
            <p className="text-eyebrow uppercase text-brand-700">
              {companyName ? `${base} · ${companyName}` : base}
            </p>
            <h1 className="mt-1.5 text-h1 text-ink">{title}</h1>
          </div>
        </div>
        {actions ? <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div> : null}
      </div>
      {description ? (
        <div className="mt-3 max-w-prose space-y-2 text-sm leading-relaxed text-ink-muted">{description}</div>
      ) : null}
      {children ? <div className="mt-4">{children}</div> : null}
    </header>
  );
}
