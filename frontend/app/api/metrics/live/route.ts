import { NextRequest, NextResponse } from "next/server";

import { fetchUpstreamText } from "@/lib/upstream-error";
import { upstreamInitFromRequest } from "@/lib/upstream-request";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

/** Company-scoped live metrics. Forwards X-User-Id like /api/decisions. */
export async function GET(request: NextRequest): Promise<NextResponse> {
  const result = await fetchUpstreamText(
    `${API_URL}/metrics/live`,
    upstreamInitFromRequest(request, {
      method: "GET",
      cache: "no-store",
    }),
  );
  if (!result.ok) {
    return result.errorResponse;
  }
  return new NextResponse(result.text, {
    status: result.response.status,
    headers: { "Content-Type": "application/json" },
  });
}
