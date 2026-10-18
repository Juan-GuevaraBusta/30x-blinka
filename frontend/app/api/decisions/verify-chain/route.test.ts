import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const ORIGINAL_ENV = { ...process.env };

function fetchMockReturning(body: string, status = 200) {
  return vi.fn(async (_url: string, _init?: RequestInit) => new Response(body, { status }));
}

describe("proxy /api/decisions/verify-chain (T5.10, D055)", () => {
  beforeEach(() => {
    vi.resetModules();
    process.env = { ...ORIGINAL_ENV };
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
    vi.unstubAllGlobals();
  });

  it("passes through the upstream ok/length/first_broken_id body", async () => {
    const fetchMock = fetchMockReturning('{"ok":true,"length":3,"first_broken_id":null}');
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const response = await GET();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url] = fetchMock.mock.calls[0] as [string];
    expect(url).toContain("/decisions/verify-chain");
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ ok: true, length: 3, first_broken_id: null });
  });

  it("passes through a broken-chain body unchanged", async () => {
    const fetchMock = fetchMockReturning(
      '{"ok":false,"length":3,"first_broken_id":"dec_0002"}',
    );
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    const response = await GET();

    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({
      ok: false,
      length: 3,
      first_broken_id: "dec_0002",
    });
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
