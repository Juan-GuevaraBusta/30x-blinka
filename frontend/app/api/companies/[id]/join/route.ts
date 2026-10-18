import { NextRequest, NextResponse } from "next/server";

import { fetchUpstreamText } from "@/lib/upstream-error";
import { upstreamInitFromRequest } from "@/lib/upstream-request";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
const SAFE_ID = /^[A-Za-z0-9-]{1,64}$/;

/** POST /companies/{id}/join (T9.8, D067): join an existing company as member. */
export async function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await context.params;
  if (!SAFE_ID.test(id)) {
    return NextResponse.json({ detail: "not_found" }, { status: 404 });
  }
  const result = await fetchUpstreamText(
    `${API_URL}/companies/${encodeURIComponent(id)}/join`,
    upstreamInitFromRequest(request, { method: "POST", cache: "no-store" }),
  );
  if (!result.ok) {
    return result.errorResponse;
  }
  return new NextResponse(result.text, {
    status: result.response.status,
    headers: { "Content-Type": "application/json" },
  });
}
