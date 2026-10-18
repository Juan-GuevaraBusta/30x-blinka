import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const ROUTE_FILE = fileURLToPath(new URL("./route.ts", import.meta.url));
const ORIGINAL_ENV = { ...process.env };

function fetchMockReturning(body: string, status = 200) {
  return vi.fn(async (_url: string, _init?: RequestInit) => new Response(body, { status }));
}

describe("proxy /api/rules (T5.9, D055)", () => {
  beforeEach(() => {
    vi.resetModules();
    process.env = { ...ORIGINAL_ENV };
  });

  afterEach(() => {
    process.env = { ...ORIGINAL_ENV };
    vi.unstubAllGlobals();
  });

  it("injects X-Admin-Key on PUT from the server-side env var", async () => {
    process.env.ADMIN_API_KEY = "server-secret";
    const fetchMock = fetchMockReturning("{}");
    vi.stubGlobal("fetch", fetchMock);
    const { PUT } = await import("./route");

    const request = new NextRequest("http://localhost/api/rules", {
      method: "PUT",
      body: JSON.stringify({ human_approval_threshold: 2500 }),
    });
    await PUT(request);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers["X-Admin-Key"]).toBe("server-secret");
  });

  it("never sends X-Admin-Key on GET, even when the key is configured", async () => {
    process.env.ADMIN_API_KEY = "server-secret";
    const fetchMock = fetchMockReturning("{}");
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("./route");

    await GET();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [, init] = fetchMock.mock.calls[0] as [string, RequestInit | undefined];
    const headers = (init?.headers ?? {}) as Record<string, string>;
    expect(headers["X-Admin-Key"]).toBeUndefined();
  });

  it("omits the header on PUT when ADMIN_API_KEY is unset (backend fails closed)", async () => {
    delete process.env.ADMIN_API_KEY;
    const fetchMock = fetchMockReturning('{"detail":"admin_key_not_configured"}', 503);
    vi.stubGlobal("fetch", fetchMock);
    const { PUT } = await import("./route");

    const request = new NextRequest("http://localhost/api/rules", {
      method: "PUT",
      body: JSON.stringify({}),
    });
    const response = await PUT(request);

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
