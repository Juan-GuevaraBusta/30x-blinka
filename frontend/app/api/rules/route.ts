import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

async function proxy(method: "GET" | "PUT", body?: string): Promise<NextResponse> {
  const upstream = await fetch(`${API_URL}/rules`, {
    method,
    headers: body ? { "Content-Type": "application/json" } : undefined,
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
