"use client";

import { useMe } from "@/lib/me";

export const WORKSPACE_EYEBROW = "Puesto de control";

export function PageHeader({
  title,
  description,
  children,
  bordered = true,
}: {
  title: string;
  description?: React.ReactNode;
  children?: React.ReactNode;
  bordered?: boolean;
}) {
  const companyName = useMe()?.company?.name;
  return (
    <header className={bordered ? "border-b border-line pb-6" : "pb-2"}>
      <p className="text-sm text-ink-muted">
        {companyName ? `${WORKSPACE_EYEBROW} · ${companyName}` : WORKSPACE_EYEBROW}
      </p>
      <h1 className="mt-1 text-2xl font-semibold tracking-tight text-ink sm:text-3xl">{title}</h1>
      {description ? (
        <div className="mt-3 max-w-prose space-y-2 text-sm leading-relaxed text-ink-muted">
          {description}
        </div>
      ) : null}
      {children ? <div className="mt-4">{children}</div> : null}
    </header>
  );
}
