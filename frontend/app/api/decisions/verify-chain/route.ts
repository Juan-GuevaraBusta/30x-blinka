import { NextResponse } from "next/server";

import { fetchUpstreamText } from "@/lib/upstream-error";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

/** Proxy for GET /decisions/verify-chain (T5.10, D055). Public, read-only: no admin key. */
export async function GET(): Promise<NextResponse> {
  const result = await fetchUpstreamText(`${API_URL}/decisions/verify-chain`, {
    method: "GET",
    cache: "no-store",
  });
  if (!result.ok) {
    return result.errorResponse;
  }
  return new NextResponse(result.text, {
    status: result.response.status,
    headers: { "Content-Type": "application/json" },
  });
}
