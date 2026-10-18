import Link from "next/link";

import { cn } from "@/lib/cn";

export type TabItem = { key: string; label: React.ReactNode; href?: string; count?: number };

/** Pill tabs. Link-based when items carry `href`, button-based otherwise. */
export function Tabs({
  items,
  activeKey,
  onSelect,
  label,
  className,
}: {
  items: TabItem[];
  activeKey: string;
  onSelect?: (key: string) => void;
  label: string;
  className?: string;
}) {
  return (
    <nav aria-label={label} className={cn("overflow-x-auto", className)}>
      <ul className="inline-flex gap-1 rounded-xl border border-line bg-surface-sunken p-1">
        {items.map((item) => {
          const active = item.key === activeKey;
          const cls = cn(
            "inline-flex items-center gap-2 whitespace-nowrap rounded-lg px-3.5 py-1.5 text-sm font-semibold transition-all duration-150 focus-ring",
            active ? "bg-surface text-brand-700 shadow-sm" : "text-ink-muted hover:bg-surface/70 hover:text-ink",
          );
          const count =
            item.count !== undefined ? (
              <span
                className={cn(
                  "rounded-full px-1.5 py-0.5 font-mono text-2xs",
                  active ? "bg-brand-100 text-brand-700" : "bg-line text-ink-muted",
                )}
              >
                {item.count}
              </span>
            ) : null;
          return (
            <li key={item.key}>
              {item.href ? (
                <Link href={item.href} aria-current={active ? "page" : undefined} className={cls}>
                  {item.label}
                  {count}
                </Link>
              ) : (
                <button type="button" aria-pressed={active} className={cls} onClick={() => onSelect?.(item.key)}>
                  {item.label}
                  {count}
                </button>
              )}
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
