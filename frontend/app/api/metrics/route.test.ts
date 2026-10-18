import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const ORIGINAL_ENV = { ...process.env };

function fetchMockReturning(body: string, status = 200) {
  return vi.fn(async (_url: string, _init?: RequestInit) => new Response(body, { status }));
}

describe("proxy /api/metrics (T6.7, D057)", () => {
  beforeEach(() => {
    vi.resetModules();
    process.env = { ...ORIGINAL_ENV };
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
    vi.unstubAllGlobals();
  });

  it("passes through the upstream body/status", async () => {
    const fetchMock = fetchMockReturning('{"unsafe_pay":0,"autonomy_pct":80,"source":"report"}');
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const response = await GET();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/metrics");
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ unsafe_pay: 0, autonomy_pct: 80, source: "report" });
  });

  it("returns 502 upstream_unreachable when the upstream fetch throws", async () => {
    const fetchMock = vi.fn(async () => {
      throw new Error("ECONNREFUSED");
    });
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const response = await GET();

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

    const response = await GET();

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ detail: "upstream_unreachable" });
  });
});
