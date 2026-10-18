"use client";

import { useEffect, useState } from "react";

import {
  type ChainVerification,
  chainBadgeLabel,
  chainBadgeToneClass,
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
    <p
      className={`mt-2 text-xs font-medium ${chainBadgeToneClass(result)}`}
      role="status"
      data-testid="chain-integrity-badge"
    >
      {chainBadgeLabel(result)}
    </p>
  );
}
