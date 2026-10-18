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

describe("proxy /api/decisions/[id]/add-beneficiary (T7.4)", () => {
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

    const request = new NextRequest("http://localhost/api/decisions/dec_r01/add-beneficiary", {
      method: "POST",
      body: JSON.stringify({ author: "cfo@demo.test", reason: "ok" }),
    });
    await POST(request, contextFor("dec_r01"));

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toContain("/decisions/dec_r01/add-beneficiary");
    const headers = new Headers(init.headers);
    expect(headers.get("X-Admin-Key")).toBe("server-secret");
  });

  it("rejects invalid decision ids without calling upstream", async () => {
    const fetchMock = fetchMockReturning("{}");
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await import("./route");

    const request = new NextRequest("http://localhost/api/decisions/../evil/add-beneficiary", {
      method: "POST",
      body: "{}",
    });
    const response = await POST(request, contextFor("../evil"));

    expect(response.status).toBe(404);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("route source matches approve proxy pattern", () => {
    const source = readFileSync(ROUTE_FILE, "utf8");
    expect(source).toContain("ADMIN_API_KEY");
    expect(source).toContain("add-beneficiary");
  });
});
