import Link from "next/link";
import type { ComponentProps, ReactNode } from "react";

import { cn } from "@/lib/cn";

export type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "success" | "signal";
export type ButtonSize = "sm" | "md" | "lg";

const BASE =
  "inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-all duration-150 focus-ring disabled:cursor-not-allowed disabled:opacity-50 active:translate-y-0";

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    "bg-brand-600 text-white shadow-sm hover:-translate-y-px hover:bg-brand-700 hover:shadow-glow disabled:hover:translate-y-0",
  secondary:
    "border border-line-strong bg-surface text-ink shadow-xs hover:border-brand-300 hover:bg-brand-50",
  ghost: "text-ink-muted hover:bg-brand-50 hover:text-brand-700",
  danger: "bg-stop-600 text-white shadow-sm hover:-translate-y-px hover:bg-stop-700",
  success: "bg-pay-600 text-white shadow-sm hover:-translate-y-px hover:bg-pay-700",
  signal: "bg-signal text-night shadow-sm hover:-translate-y-px hover:bg-signal/90",
};

const SIZES: Record<ButtonSize, string> = {
  sm: "h-8 px-3 text-xs",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
};

export function buttonClass(variant: ButtonVariant = "primary", size: ButtonSize = "md", className?: string) {
  return cn(BASE, VARIANTS[variant], SIZES[size], className);
}

type ButtonProps = ComponentProps<"button"> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
};

export function Button({ variant, size, icon, className, children, type = "button", ...rest }: ButtonProps) {
  return (
    <button type={type} className={buttonClass(variant, size, className)} {...rest}>
      {icon}
      {children}
    </button>
  );
}

type ButtonLinkProps = ComponentProps<typeof Link> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  icon?: ReactNode;
};

export function ButtonLink({ variant, size, icon, className, children, ...rest }: ButtonLinkProps) {
  return (
    <Link className={buttonClass(variant, size, className)} {...rest}>
      {icon}
      {children}
    </Link>
  );
}
