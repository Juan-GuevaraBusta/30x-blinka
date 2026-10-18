import type { NextRequest } from "next/server";

const FORWARDED = ["X-User-Id", "X-User-Email"] as const;

/** Forward demo user identity to FastAPI (hackathon: no JWT verification, T9.8). */
export function upstreamInitFromRequest(
  request: NextRequest,
  init?: RequestInit,
): RequestInit {
  const headers = new Headers(init?.headers);
  for (const name of FORWARDED) {
    const value = request.headers.get(name);
    if (value && value.trim()) {
      headers.set(name, value.trim());
    }
  }
  return { ...init, headers };
}

/** Same identity headers as a plain record (for proxies that build their own headers). */
export function identityFromRequest(request: NextRequest): Record<string, string> {
  const out: Record<string, string> = {};
  for (const name of FORWARDED) {
    const value = request.headers.get(name);
    if (value && value.trim()) {
      out[name] = value.trim();
    }
  }
  return out;
}
