"use client";

import { ShieldAlert, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/Badge";

import {
  type ChainVerification,
  chainBadgeLabel,
  isChainVerification,
} from "@/lib/chain-integrity";

/**
 * Small "Registro íntegro ✓ / Registro alterado en <id>" badge for
 * /decisiones (T5.10, D055, spec §2, optional sub-item). Calls the public,
 * read-only GET /decisions/verify-chain proxy. This is an auxiliary
 * integrity indicator, not a blocking check: a failed or unparsable
 * response just renders nothing instead of an error banner.
 */
export default function ChainIntegrityBadge() {
  const [result, setResult] = useState<ChainVerification | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch("/api/decisions/verify-chain", { cache: "no-store" });
        if (!res.ok) return;
        const body: unknown = await res.json();
        if (!cancelled && isChainVerification(body)) {
          setResult(body);
        }
      } catch {
        // Silently show nothing; this badge never blocks the decisions list.
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (result === null) {
    return null;
  }

  return (
    <Badge
      tone={result.ok ? "pay" : "stop"}
      className="animate-fade-up"
      role="status"
      data-testid="chain-integrity-badge"
      icon={
        result.ok ? (
          <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
        ) : (
          <ShieldAlert className="h-3.5 w-3.5" aria-hidden="true" />
        )
      }
    >
      {chainBadgeLabel(result)}
    </Badge>
  );
}
