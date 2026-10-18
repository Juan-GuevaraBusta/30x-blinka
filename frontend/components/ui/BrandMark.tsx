import { Activity } from "lucide-react";

import { cn } from "@/lib/cn";

/** Product mark: an abstract "pulse" glyph on the night surface (not a third-party logo). */
export function BrandMark({ size = "md" }: { size?: "sm" | "md" }) {
  return (
    <span
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center rounded-lg bg-signal text-night shadow-sm",
        size === "sm" ? "h-8 w-8" : "h-10 w-10",
      )}
      aria-hidden="true"
    >
      <Activity className={size === "sm" ? "h-4 w-4" : "h-5 w-5"} strokeWidth={2.5} />
    </span>
  );
}
