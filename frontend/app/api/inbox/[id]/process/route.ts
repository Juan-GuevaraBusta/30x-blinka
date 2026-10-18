import { NextRequest, NextResponse } from "next/server";

import { isValidInboxId } from "@/lib/inbox-types";
import { fetchUpstreamText } from "@/lib/upstream-error";
import { upstreamInitFromRequest } from "@/lib/upstream-request";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export async function POST(
  request: NextRequest,
  context: { params: Promise<{ id: string }> },
): Promise<NextResponse> {
  const { id } = await context.params;
  if (!isValidInboxId(id)) {
    return NextResponse.json({ detail: "not_found" }, { status: 404 });
  }

  const body = await request.text();
  const result = await fetchUpstreamText(
    `${API_URL}/inbox/${encodeURIComponent(id)}/process`,
    upstreamInitFromRequest(request, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
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
