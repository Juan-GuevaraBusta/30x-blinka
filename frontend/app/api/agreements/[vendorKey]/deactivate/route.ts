import { NextRequest, NextResponse } from "next/server";

import { fetchUpstreamText } from "@/lib/upstream-error";
import { upstreamInitFromRequest } from "@/lib/upstream-request";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY;

/** POST /agreements/{vendor_key}/deactivate (T9.1, D061 §3). */
export async function POST(
  request: NextRequest,
  context: { params: Promise<{ vendorKey: string }> },
): Promise<NextResponse> {
  const { vendorKey } = await context.params;
  const body = await request.text();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (ADMIN_API_KEY) {
    headers["X-Admin-Key"] = ADMIN_API_KEY;
  }
  const result = await fetchUpstreamText(
    `${API_URL}/agreements/${encodeURIComponent(vendorKey)}/deactivate`,
    upstreamInitFromRequest(request, {
      method: "POST",
      headers,
      body,
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
