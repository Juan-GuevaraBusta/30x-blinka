import { NextRequest, NextResponse } from "next/server";

import { fetchUpstreamText } from "@/lib/upstream-error";
import { upstreamInitFromRequest } from "@/lib/upstream-request";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
// T5.9 (D055) pattern: server-side only, injected here, never sent by the browser.
const ADMIN_API_KEY = process.env.ADMIN_API_KEY;

/**
 * POST /agreements/draft (T9.1, D061 §3): text or an uploaded `.txt`/`.pdf`
 * file. "La IA solo propone. Nada se aplica hasta que usted confirme."
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  const formData = await request.formData();
  const headers: Record<string, string> = {};
  if (ADMIN_API_KEY) {
    headers["X-Admin-Key"] = ADMIN_API_KEY;
  }
  const result = await fetchUpstreamText(
    `${API_URL}/agreements/draft`,
    upstreamInitFromRequest(request, {
      method: "POST",
      headers,
      body: formData,
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
