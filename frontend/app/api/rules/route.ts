import { NextRequest, NextResponse } from "next/server";

import { fetchUpstreamText } from "@/lib/upstream-error";
import { identityFromRequest } from "@/lib/upstream-request";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
// T5.9 (D055): server-side only. Never read as NEXT_PUBLIC_*; the browser never sees it.
const ADMIN_API_KEY = process.env.ADMIN_API_KEY;

async function proxy(
  method: "GET" | "PUT",
  request: NextRequest,
  body?: string,
): Promise<NextResponse> {
  // T9.8 (D067): rules are per company; the API resolves it from X-User-Id.
  const headers: Record<string, string> = identityFromRequest(request);
  if (body) {
    headers["Content-Type"] = "application/json";
  }
  if (method === "PUT" && ADMIN_API_KEY) {
    headers["X-Admin-Key"] = ADMIN_API_KEY;
  }
  const result = await fetchUpstreamText(`${API_URL}/rules`, {
    method,
    headers: Object.keys(headers).length > 0 ? headers : undefined,
    body,
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

export async function GET(request: NextRequest): Promise<NextResponse> {
  return proxy("GET", request);
}

export async function PUT(request: NextRequest): Promise<NextResponse> {
  const body = await request.text();
  return proxy("PUT", request, body);
}
