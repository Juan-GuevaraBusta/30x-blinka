import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const ORIGINAL_ENV = { ...process.env };

function fetchMockReturning(body: string, status = 200) {
  return vi.fn(
    async (_url: string, _init?: RequestInit) =>
      new Response(body, { status, headers: { "Content-Type": "application/json" } }),
  );
}

function uploadRequest(): NextRequest {
  const formData = new FormData();
  formData.append("file", new File(["contenido"], "correo.eml", { type: "message/rfc822" }));
  return new NextRequest("http://localhost/api/inbox", { method: "POST", body: formData });
}

describe("proxy /api/inbox (T9.2, D061)", () => {
  beforeEach(() => {
    vi.resetModules();
    process.env = { ...ORIGINAL_ENV };
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
    vi.unstubAllGlobals();
  });

  it("GET forwards and passes through the upstream body/status", async () => {
    const fetchMock = fetchMockReturning("[]");
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const response = await GET(new NextRequest("http://localhost/api/inbox"));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/inbox");
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual([]);
  });

  it("POST forwards the multipart form body and passes through the upstream body/status", async () => {
    const fetchMock = fetchMockReturning('{"id":"inbox_000001","classification":"es_factura"}', 201);
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await import("./route");

    const response = await POST(uploadRequest());

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/inbox");
    expect(init.body).toBeInstanceOf(FormData);
    expect(response.status).toBe(201);
    expect(await response.json()).toEqual({ id: "inbox_000001", classification: "es_factura" });
  });

  it("returns 502 upstream_unreachable when the upstream fetch throws", async () => {
    const fetchMock = vi.fn(async () => {
      throw new Error("ECONNREFUSED");
    });
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await import("./route");

    const response = await POST(uploadRequest());

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ detail: "upstream_unreachable" });
  });
});
