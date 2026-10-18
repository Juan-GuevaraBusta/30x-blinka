import { NextResponse } from "next/server";

import { fetchUpstreamText } from "@/lib/upstream-error";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

/** GET /agreements (T9.1, D061): public, read-only list. No admin key needed. */
export async function GET(): Promise<NextResponse> {
  const result = await fetchUpstreamText(`${API_URL}/agreements`, { cache: "no-store" });
  if (!result.ok) {
    return result.errorResponse;
  }
  return new NextResponse(result.text, {
    status: result.response.status,
    headers: { "Content-Type": "application/json" },
  });
}
