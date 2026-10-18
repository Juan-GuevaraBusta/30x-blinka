import { NextRequest, NextResponse } from "next/server";

import { fetchUpstreamText } from "@/lib/upstream-error";
import { upstreamInitFromRequest } from "@/lib/upstream-request";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
const ADMIN_API_KEY = process.env.ADMIN_API_KEY;

/** GET /agreements/{vendor_key} (T9.1, D061 §3): current version + full history. */
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ vendorKey: string }> },
): Promise<NextResponse> {
  const { vendorKey } = await context.params;
  // T9.8 (D067): agreements are per company; the API resolves it from X-User-Id.
  const result = await fetchUpstreamText(
    `${API_URL}/agreements/${encodeURIComponent(vendorKey)}`,
    upstreamInitFromRequest(request, { cache: "no-store" }),
  );
  if (!result.ok) {
    return result.errorResponse;
  }
  return new NextResponse(result.text, {
    status: result.response.status,
    headers: { "Content-Type": "application/json" },
  });
}

/** PUT /agreements/{vendor_key} (T9.1, D061 §3): a human confirms the draft. */
export async function PUT(
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
    `${API_URL}/agreements/${encodeURIComponent(vendorKey)}`,
    upstreamInitFromRequest(request, {
      method: "PUT",
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
