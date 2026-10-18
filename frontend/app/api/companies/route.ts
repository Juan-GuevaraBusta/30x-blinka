import { NextRequest, NextResponse } from "next/server";

import { fetchUpstreamText } from "@/lib/upstream-error";
import { upstreamInitFromRequest } from "@/lib/upstream-request";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

async function relay(request: NextRequest, init: RequestInit): Promise<NextResponse> {
  const result = await fetchUpstreamText(
    `${API_URL}/companies`,
    upstreamInitFromRequest(request, { ...init, cache: "no-store" }),
  );
  if (!result.ok) {
    return result.errorResponse;
  }
  return new NextResponse(result.text, {
    status: result.response.status,
    headers: { "Content-Type": "application/json" },
  });
}

/** GET /companies (T9.8, D067): companies to pick from during onboarding. */
export async function GET(request: NextRequest): Promise<NextResponse> {
  return relay(request, { method: "GET" });
}

/** POST /companies (T9.8): create a company; the caller becomes its admin. */
export async function POST(request: NextRequest): Promise<NextResponse> {
  const body = await request.text();
  return relay(request, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
  });
}
