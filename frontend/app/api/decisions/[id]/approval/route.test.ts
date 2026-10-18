import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const ORIGINAL_ENV = { ...process.env };

function fetchMockReturning(body: string, status = 200) {
  return vi.fn(async (_url: string, _init?: RequestInit) => new Response(body, { status }));
}

function contextFor(id: string) {
  return { params: Promise.resolve({ id }) };
}

describe("proxy /api/decisions/[id]/approval (T7.1/T7.5, D059)", () => {
  beforeEach(() => {
    vi.resetModules();
    process.env = { ...ORIGINAL_ENV };
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
    vi.unstubAllGlobals();
  });

  it("forwards the id and passes through the upstream body/status", async () => {
    const fetchMock = fetchMockReturning(
      '{"route_id":"alto-monto","required":2,"collected":1,"approvers":["finanzas@demo.test"],"satisfied":false,"rejected":false,"payment_ready":false,"pending_checks":[]}',
    );
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const request = new NextRequest("http://localhost/api/decisions/dec_0042/approval");
    const response = await GET(request, contextFor("dec_0042"));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/decisions/dec_0042/approval");
    expect(response.status).toBe(200);
    const body = await response.json();
    expect(body.required).toBe(2);
    expect(body.collected).toBe(1);
  });

  it("returns 404 not_found for an invalid id without calling the upstream", async () => {
    const fetchMock = fetchMockReturning("{}");
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const request = new NextRequest("http://localhost/api/decisions/..%2Fetc/approval");
    const response = await GET(request, contextFor("../etc"));

    expect(response.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns 502 upstream_unreachable when the upstream fetch throws", async () => {
    const fetchMock = vi.fn(async () => {
      throw new Error("ECONNREFUSED");
    });
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const request = new NextRequest("http://localhost/api/decisions/dec_0042/approval");
    const response = await GET(request, contextFor("dec_0042"));

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ detail: "upstream_unreachable" });
  });

  it("returns 502 upstream_unreachable when the upstream connection resets after headers (R4)", async () => {
    const fetchMock = vi.fn(async () => ({
      status: 200,
      headers: new Headers({ "Content-Type": "application/json" }),
      text: () => Promise.reject(new Error("ECONNRESET")),
    })) as unknown as typeof fetch;
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const request = new NextRequest("http://localhost/api/decisions/dec_0042/approval");
    const response = await GET(request, contextFor("dec_0042"));

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ detail: "upstream_unreachable" });
  });
});
