import { NextRequest, NextResponse } from "next/server";

import { fetchUpstreamText } from "@/lib/upstream-error";
import { upstreamInitFromRequest } from "@/lib/upstream-request";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const formData = await request.formData();
  const result = await fetchUpstreamText(
    `${API_URL}/invoices`,
    upstreamInitFromRequest(request, {
      method: "POST",
      body: formData,
      cache: "no-store",
    }),
  );
  if (!result.ok) {
    return result.errorResponse;
  }
  const contentType = result.response.headers.get("Content-Type") ?? "application/json";
  return new NextResponse(result.text, {
    status: result.response.status,
    headers: { "Content-Type": contentType },
  });
}
