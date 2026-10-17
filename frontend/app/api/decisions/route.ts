import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export async function GET(request: NextRequest): Promise<NextResponse> {
  const decision = request.nextUrl.searchParams.get("decision");
  const query = decision ? `?decision=${encodeURIComponent(decision)}` : "";
  const upstream = await fetch(`${API_URL}/decisions${query}`, {
    method: "GET",
    cache: "no-store",
  });
  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}
