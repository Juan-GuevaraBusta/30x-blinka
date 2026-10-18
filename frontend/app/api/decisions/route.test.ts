import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const ORIGINAL_ENV = { ...process.env };

function fetchMockReturning(body: string, status = 200) {
  return vi.fn(async (_url: string, _init?: RequestInit) => new Response(body, { status }));
}

describe("proxy /api/decisions (T6.7, D057)", () => {
  beforeEach(() => {
    vi.resetModules();
    process.env = { ...ORIGINAL_ENV };
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
    vi.unstubAllGlobals();
  });

  it("forwards the decision query param and passes through the upstream body/status", async () => {
    const fetchMock = fetchMockReturning('[{"invoice_id":"inv_1"}]');
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const request = new NextRequest("http://localhost/api/decisions?decision=ESCALAR");
    const response = await GET(request);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/decisions?decision=ESCALAR");
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual([{ invoice_id: "inv_1" }]);
  });

  it("omits the query string when decision is absent", async () => {
    const fetchMock = fetchMockReturning("[]");
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const request = new NextRequest("http://localhost/api/decisions");
    await GET(request);

    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url.endsWith("/decisions")).toBe(true);
  });

  it("returns 502 upstream_unreachable when the upstream fetch throws", async () => {
    const fetchMock = vi.fn(async () => {
      throw new Error("ECONNREFUSED");
    });
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const request = new NextRequest("http://localhost/api/decisions");
    const response = await GET(request);

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ detail: "upstream_unreachable" });
  });
});
