import { NextRequest, NextResponse } from "next/server";

import { upstreamUnreachableResponse } from "@/lib/upstream-error";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

export async function POST(request: NextRequest): Promise<NextResponse> {
  const formData = await request.formData();
  let upstream: Response;
  try {
    upstream = await fetch(`${API_URL}/invoices`, {
      method: "POST",
      body: formData,
      cache: "no-store",
    });
  } catch {
    return upstreamUnreachableResponse();
  }
  const text = await upstream.text();
  const contentType = upstream.headers.get("Content-Type") ?? "application/json";
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": contentType },
  });
}
