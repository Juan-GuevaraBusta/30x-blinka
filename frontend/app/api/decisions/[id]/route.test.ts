import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const ORIGINAL_ENV = { ...process.env };

function fetchMockReturning(body: string, status = 200) {
  return vi.fn(async (_url: string, _init?: RequestInit) => new Response(body, { status }));
}

function contextFor(id: string) {
  return { params: Promise.resolve({ id }) };
}

describe("proxy /api/decisions/[id] (T6.7, D057)", () => {
  beforeEach(() => {
    vi.resetModules();
    process.env = { ...ORIGINAL_ENV };
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
    vi.unstubAllGlobals();
  });

  it("forwards the id and passes through the upstream body/status", async () => {
    const fetchMock = fetchMockReturning('{"id":"dec_0042"}');
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const request = new NextRequest("http://localhost/api/decisions/dec_0042");
    const response = await GET(request, contextFor("dec_0042"));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/decisions/dec_0042");
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ id: "dec_0042" });
  });

  it("returns 404 not_found for an invalid id without calling the upstream", async () => {
    const fetchMock = fetchMockReturning("{}");
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const request = new NextRequest("http://localhost/api/decisions/..%2Fetc");
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

    const request = new NextRequest("http://localhost/api/decisions/dec_0042");
    const response = await GET(request, contextFor("dec_0042"));

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ detail: "upstream_unreachable" });
  });
});
