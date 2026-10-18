import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("proxy /api/metrics/evaluation", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("passes through the upstream body/status", async () => {
    const body =
      '{"entries":[{"id":"holdout","label":"Holdout","value":"pendiente T5.1","source":"eval/reports/latest.md (no generado)"}],"generated_at":null,"source":"report"}';
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => new Response(body, { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const response = await GET();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url.endsWith("/metrics/evaluation")).toBe(true);
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual(JSON.parse(body));
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
});
