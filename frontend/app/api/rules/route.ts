import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";
// T5.9 (D055): server-side only. Never read as NEXT_PUBLIC_*; the browser never sees it.
const ADMIN_API_KEY = process.env.ADMIN_API_KEY;

async function proxy(method: "GET" | "PUT", body?: string): Promise<NextResponse> {
  const headers: Record<string, string> = {};
  if (body) {
    headers["Content-Type"] = "application/json";
  }
  if (method === "PUT" && ADMIN_API_KEY) {
    headers["X-Admin-Key"] = ADMIN_API_KEY;
  }
  const upstream = await fetch(`${API_URL}/rules`, {
    method,
    headers: Object.keys(headers).length > 0 ? headers : undefined,
    body,
    cache: "no-store",
  });
  const text = await upstream.text();
  return new NextResponse(text, {
    status: upstream.status,
    headers: { "Content-Type": "application/json" },
  });
}

export async function GET(): Promise<NextResponse> {
  return proxy("GET");
}

export async function PUT(request: NextRequest): Promise<NextResponse> {
  const body = await request.text();
  return proxy("PUT", body);
}
