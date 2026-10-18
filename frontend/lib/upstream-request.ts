import type { NextRequest } from "next/server";

/** Forward demo user scope to FastAPI (hackathon: no JWT verification). */
export function upstreamInitFromRequest(
  request: NextRequest,
  init?: RequestInit,
): RequestInit {
  const userId = request.headers.get("x-user-id");
  const headers = new Headers(init?.headers);
  if (userId) {
    headers.set("X-User-Id", userId);
  }
  return { ...init, headers };
}
