import { NextResponse } from "next/server";

import { fetchUpstreamText } from "@/lib/upstream-error";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

/** GET /rules/effective (T9.1, D061 §3): compiled rules + provenance. Public, read-only. */
export async function GET(): Promise<NextResponse> {
  const result = await fetchUpstreamText(`${API_URL}/rules/effective`, { cache: "no-store" });
  if (!result.ok) {
    return result.errorResponse;
  }
  return new NextResponse(result.text, {
    status: result.response.status,
    headers: { "Content-Type": "application/json" },
  });
}
