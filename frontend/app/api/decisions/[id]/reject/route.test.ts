import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const ROUTE_FILE = fileURLToPath(new URL("./route.ts", import.meta.url));
const ORIGINAL_ENV = { ...process.env };

function fetchMockReturning(body: string, status = 200) {
  return vi.fn(async (_url: string, _init?: RequestInit) => new Response(body, { status }));
}

function contextFor(id: string) {
  return { params: Promise.resolve({ id }) };
}

describe("proxy /api/decisions/[id]/reject (T5.9, D055)", () => {
  beforeEach(() => {
    vi.resetModules();
    process.env = { ...ORIGINAL_ENV };
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
    vi.unstubAllGlobals();
  });

  it("injects X-Admin-Key from the server-side env var", async () => {
    process.env.ADMIN_API_KEY = "server-secret";
    const fetchMock = fetchMockReturning("{}");
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await import("./route");

    const request = new NextRequest("http://localhost/api/decisions/dec_0042/reject", {
      method: "POST",
      body: JSON.stringify({ author: "cfo@demo.test", reason: "ok" }),
    });
    await POST(request, contextFor("dec_0042"));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers["X-Admin-Key"]).toBe("server-secret");
  });

  it("omits the header when ADMIN_API_KEY is unset (backend fails closed)", async () => {
    delete process.env.ADMIN_API_KEY;
    const fetchMock = fetchMockReturning('{"detail":"admin_key_not_configured"}', 503);
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await import("./route");

    const request = new NextRequest("http://localhost/api/decisions/dec_0042/reject", {
      method: "POST",
      body: JSON.stringify({ author: "cfo@demo.test", reason: "ok" }),
    });
    const response = await POST(request, contextFor("dec_0042"));

    expect(response.status).toBe(503);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit | undefined];
    const headers = (init?.headers ?? {}) as Record<string, string>;
    expect(headers["X-Admin-Key"]).toBeUndefined();
  });

  it("never reads the admin key from a NEXT_PUBLIC_* env var", () => {
    const source = readFileSync(ROUTE_FILE, "utf8");
    expect(source).not.toMatch(/NEXT_PUBLIC_ADMIN_API_KEY/);
  });
});
