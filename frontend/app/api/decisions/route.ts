import { NextRequest, NextResponse } from "next/server";

import { fetchUpstreamText } from "@/lib/upstream-error";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export async function GET(request: NextRequest): Promise<NextResponse> {
  const decision = request.nextUrl.searchParams.get("decision");
  const query = decision ? `?decision=${encodeURIComponent(decision)}` : "";
  const result = await fetchUpstreamText(`${API_URL}/decisions${query}`, {
    method: "GET",
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
