import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const ORIGINAL_ENV = { ...process.env };

function fetchMockReturning(body: string, status = 201) {
  return vi.fn(
    async (_url: string, _init?: RequestInit) =>
      new Response(body, { status, headers: { "Content-Type": "application/json" } }),
  );
}

function invoiceRequest(): NextRequest {
  const formData = new FormData();
  formData.append("file", new File(["contenido"], "factura.txt", { type: "text/plain" }));
  formData.append("invoice_id", "inv_1");
  formData.append("channel", "pdf_text");
  formData.append("received_at", "2025-12-22T10:00:00Z");
  return new NextRequest("http://localhost/api/invoices", {
    method: "POST",
    body: formData,
  });
}

describe("proxy /api/invoices (T6.7, D057)", () => {
  beforeEach(() => {
    vi.resetModules();
    process.env = { ...ORIGINAL_ENV };
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
    vi.unstubAllGlobals();
  });

  it("forwards the multipart form body and passes through the upstream body/status", async () => {
    const fetchMock = fetchMockReturning('{"id":"dec_0001","decision":"ESCALAR"}');
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await import("./route");

    const response = await POST(invoiceRequest());

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/invoices");
    expect(init.body).toBeInstanceOf(FormData);
    expect(response.status).toBe(201);
    expect(await response.json()).toEqual({ id: "dec_0001", decision: "ESCALAR" });
  });

  it("returns 502 upstream_unreachable when the upstream fetch throws", async () => {
    const fetchMock = vi.fn(async () => {
      throw new Error("ECONNREFUSED");
    });
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await import("./route");

    const response = await POST(invoiceRequest());

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ detail: "upstream_unreachable" });
  });

  it("returns 502 upstream_unreachable when the upstream connection resets after headers (R4)", async () => {
    const fetchMock = vi.fn(async () => ({
      status: 201,
      headers: new Headers({ "Content-Type": "application/json" }),
      text: () => Promise.reject(new Error("ECONNRESET")),
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await import("./route");

    const response = await POST(invoiceRequest());

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ detail: "upstream_unreachable" });
  });
});
