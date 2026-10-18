import type { ComponentProps } from "react";

import { cn } from "@/lib/cn";

export function TableWrap({ className, ...rest }: ComponentProps<"div">) {
  return <div className={cn("overflow-x-auto rounded-xl border border-line bg-surface shadow-sm", className)} {...rest} />;
}

export function Table({ className, ...rest }: ComponentProps<"table">) {
  return <table className={cn("w-full min-w-[36rem] border-collapse text-left text-sm", className)} {...rest} />;
}

export function THead({ className, ...rest }: ComponentProps<"thead">) {
  return <thead className={cn("bg-surface-sunken text-eyebrow uppercase text-ink-muted", className)} {...rest} />;
}

export function Th({ className, ...rest }: ComponentProps<"th">) {
  return <th scope="col" className={cn("border-b border-line px-4 py-3 font-semibold", className)} {...rest} />;
}

export function Tr({ className, ...rest }: ComponentProps<"tr">) {
  return <tr className={cn("border-b border-line transition-colors last:border-b-0 hover:bg-brand-50/60", className)} {...rest} />;
}

export function Td({ className, ...rest }: ComponentProps<"td">) {
  return <td className={cn("px-4 py-3 align-middle text-ink", className)} {...rest} />;
}
