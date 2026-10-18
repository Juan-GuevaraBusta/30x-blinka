import type { ComponentProps, ReactNode } from "react";

import { cn } from "@/lib/cn";

export function Field({
  label,
  htmlFor,
  hint,
  error,
  children,
  className,
}: {
  label: ReactNode;
  htmlFor?: string;
  hint?: ReactNode;
  error?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("space-y-1.5", className)}>
      <label htmlFor={htmlFor} className="block text-sm font-semibold text-ink">
        {label}
      </label>
      {children}
      {error ? (
        <p className="text-xs font-medium text-stop-700" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p className="text-xs text-ink-muted">{hint}</p>
      ) : null}
    </div>
  );
}

export function Input({ className, ...rest }: ComponentProps<"input">) {
  return <input className={cn("input-field", className)} {...rest} />;
}

export function Select({ className, ...rest }: ComponentProps<"select">) {
  return <select className={cn("input-field pr-8", className)} {...rest} />;
}

export function Textarea({ className, ...rest }: ComponentProps<"textarea">) {
  return <textarea className={cn("input-field", className)} {...rest} />;
}
