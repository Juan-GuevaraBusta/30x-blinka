"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { fetchMe } from "@/lib/me";
import { onboardingRedirect } from "@/lib/onboarding";
import { getStoredUserId } from "@/lib/session";

const PUBLIC_PATHS = new Set(["/entrar"]);

/** Signed out → /entrar; signed in without company → /onboarding (T9.8, D067). */
export default function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const path = pathname ?? "/";
    setReady(false);
    if (PUBLIC_PATHS.has(path)) {
      setReady(true);
      return;
    }
    if (!getStoredUserId()) {
      router.replace("/entrar");
      return;
    }
    void fetchMe().then((me) => {
      if (cancelled) return;
      const target = onboardingRedirect(path, me);
      if (target) {
        router.replace(target);
        return;
      }
      setReady(true);
    });
    return () => {
      cancelled = true;
    };
  }, [pathname, router]);

  if (!ready) {
    return (
      <div className="space-y-4" role="status" aria-live="polite">
        <span className="sr-only">Cargando…</span>
        <div className="skeleton h-4 w-40" aria-hidden="true" />
        <div className="skeleton h-9 w-72" aria-hidden="true" />
        <div className="grid gap-4 sm:grid-cols-3" aria-hidden="true">
          <div className="skeleton h-32" />
          <div className="skeleton h-32" />
          <div className="skeleton h-32" />
        </div>
      </div>
    );
  }

  return children;
}
