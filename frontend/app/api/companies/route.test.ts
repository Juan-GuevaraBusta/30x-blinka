import { NextRequest } from "next/server";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

describe("proxy /api/companies and /api/me (T9.8)", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("forwards X-User-Id and X-User-Email on POST /companies", async () => {
    const fetchMock = vi.fn(async () => new Response('{"company":null}', { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await import("./route");

    const request = new NextRequest("http://localhost/api/companies", {
      method: "POST",
      headers: { "X-User-Id": "uuid-1", "X-User-Email": "ana@beta.test" },
      body: JSON.stringify({ name: "Beta", base_currency: "EUR", is_demo: false }),
    });
    const response = await POST(request);

    expect(response.status).toBe(201);
    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url.endsWith("/companies")).toBe(true);
    const headers = init.headers as Headers;
    expect(headers.get("X-User-Id")).toBe("uuid-1");
    expect(headers.get("X-User-Email")).toBe("ana@beta.test");
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("forwards identity on GET /me", async () => {
    const fetchMock = vi.fn(async () => new Response("{}"));
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("../me/route");

    await GET(new NextRequest("http://localhost/api/me", { headers: { "X-User-Id": "uuid-2" } }));

    const [url, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect(url.endsWith("/me")).toBe(true);
    expect((init.headers as Headers).get("X-User-Id")).toBe("uuid-2");
  });

  it("forwards identity on GET /rules alongside no admin key", async () => {
    const fetchMock = vi.fn(async () => new Response("{}"));
    vi.stubGlobal("fetch", fetchMock);
    const { GET } = await import("../rules/route");

    await GET(new NextRequest("http://localhost/api/rules", { headers: { "X-User-Id": "uuid-3" } }));

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    const headers = init.headers as Record<string, string>;
    expect(headers["X-User-Id"]).toBe("uuid-3");
    expect(headers["X-Admin-Key"]).toBeUndefined();
  });
});
