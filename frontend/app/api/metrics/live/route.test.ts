import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("proxy /api/metrics/live (company-scoped)", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("forwards X-User-Id and passes through the upstream body/status", async () => {
    const body =
      '{"total":2,"pagar":1,"frenar":0,"escalar":1,"auto_decided_pct":50,"pending_approvals":1,"approved_by_humans":0}';
    const fetchMock = vi.fn(async () => new Response(body, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const request = new NextRequest("http://localhost/api/metrics/live", {
      headers: { "X-User-Id": "uuid-1" },
    });
    const response = await GET(request);

    expect(response.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url.endsWith("/metrics/live")).toBe(true);
    expect((init.headers as Headers).get("X-User-Id")).toBe("uuid-1");
    expect(await response.json()).toEqual(JSON.parse(body));
  });

  it("returns 502 upstream_unreachable when the upstream fetch throws", async () => {
    const fetchMock = vi.fn(async () => {
      throw new Error("ECONNREFUSED");
    });
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const response = await GET(new NextRequest("http://localhost/api/metrics/live"));

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ detail: "upstream_unreachable" });
  });
});
