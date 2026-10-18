import { NextRequest, NextResponse } from "next/server";

import { isValidDecisionId } from "@/lib/decision-present";
import { upstreamUnreachableResponse } from "@/lib/upstream-error";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await context.params;
  if (!isValidDecisionId(id)) {
    return NextResponse.json({ detail: "not_found" }, { status: 404 });
  }

  let upstream: Response;
  try {
    upstream = await fetch(`${API_URL}/decisions/${encodeURIComponent(id)}`, {
      method: "GET",
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
