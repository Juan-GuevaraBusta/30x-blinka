import { NextRequest, NextResponse } from "next/server";

import { fetchUpstreamText } from "@/lib/upstream-error";
import { upstreamInitFromRequest } from "@/lib/upstream-request";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

/** GET /agreements (T9.1, D061): the caller's company agreements (T9.8). */
export async function GET(request: NextRequest): Promise<NextResponse> {
  const result = await fetchUpstreamText(
    `${API_URL}/agreements`,
    upstreamInitFromRequest(request, { method: "GET", cache: "no-store" }),
  );
  if (!result.ok) {
    return result.errorResponse;
  }
  return new NextResponse(result.text, {
    status: result.response.status,
    headers: { "Content-Type": "application/json" },
  });
}
