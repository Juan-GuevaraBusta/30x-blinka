import { NextRequest, NextResponse } from "next/server";

import { isValidDecisionId } from "@/lib/decision-present";
import { upstreamUnreachableResponse } from "@/lib/upstream-error";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
// T5.9 (D055): server-side only. Never read as NEXT_PUBLIC_*; the browser never sees it.
const ADMIN_API_KEY = process.env.ADMIN_API_KEY;

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await context.params;
  if (!isValidDecisionId(id)) {
    return NextResponse.json({ detail: "not_found" }, { status: 404 });
  }

  const body = await request.text();
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (ADMIN_API_KEY) {
    headers["X-Admin-Key"] = ADMIN_API_KEY;
  }
  let upstream: Response;
  try {
    upstream = await fetch(`${API_URL}/decisions/${encodeURIComponent(id)}/approve`, {
      method: "POST",
      headers,
      body,
      cache: "no-store",
    });
  } catch {
    return upstreamUnreachableResponse();
  }
  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
