"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { getStoredUserId } from "@/lib/session";

const PUBLIC_PATHS = new Set(["/entrar"]);

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const path = pathname ?? "/";
    if (PUBLIC_PATHS.has(path)) {
      setReady(true);
      return;
    }
    if (!getStoredUserId()) {
      router.replace("/entrar");
      return;
    }
    setReady(true);
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
