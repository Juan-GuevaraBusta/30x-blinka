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
      <p className="text-sm text-ink-muted" role="status">
        Cargando…
      </p>
    );
  }

  return children;
}
