import { NextResponse } from "next/server";

import { upstreamUnreachableResponse } from "@/lib/upstream-error";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export async function GET(): Promise<NextResponse> {
  let upstream: Response;
  try {
    upstream = await fetch(`${API_URL}/metrics`, {
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
