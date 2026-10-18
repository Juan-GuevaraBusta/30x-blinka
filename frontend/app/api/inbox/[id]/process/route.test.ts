import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const ORIGINAL_ENV = { ...process.env };

function fetchMockReturning(body: string, status = 200) {
  return vi.fn(async (_url: string, _init?: RequestInit) => new Response(body, { status }));
}

function contextFor(id: string) {
  return { params: Promise.resolve({ id }) };
}

function processRequest(id: string, author: string): NextRequest {
  return new NextRequest(`http://localhost/api/inbox/${id}/process`, {
    method: "POST",
    body: JSON.stringify({ author }),
  });
}

describe("proxy /api/inbox/[id]/process (T9.2, D061)", () => {
  beforeEach(() => {
    vi.resetModules();
    process.env = { ...ORIGINAL_ENV };
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
    vi.unstubAllGlobals();
  });

  it("forwards the JSON body and passes through the upstream body/status", async () => {
    const fetchMock = fetchMockReturning('{"id":"inbox_000001","decision_id":"dec_0001"}');
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await import("./route");

    const response = await POST(
      processRequest("inbox_000001", "cfo@demo.test"),
      contextFor("inbox_000001"),
    );

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/inbox/inbox_000001/process");
    expect(init.body).toContain("cfo@demo.test");
    expect(response.status).toBe(200);
    expect(await response.json()).toEqual({ id: "inbox_000001", decision_id: "dec_0001" });
  });

  it("returns 404 not_found for an invalid id without calling the upstream", async () => {
    const fetchMock = fetchMockReturning("{}");
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await import("./route");

    const response = await POST(processRequest("../etc", "cfo@demo.test"), contextFor("../etc"));

    expect(response.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("returns 502 upstream_unreachable when the upstream fetch throws", async () => {
    const fetchMock = vi.fn(async () => {
      throw new Error("ECONNREFUSED");
    });
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await import("./route");

    const response = await POST(
      processRequest("inbox_000001", "cfo@demo.test"),
      contextFor("inbox_000001"),
    );

    expect(response.status).toBe(502);
    expect(await response.json()).toEqual({ detail: "upstream_unreachable" });
  });
});
