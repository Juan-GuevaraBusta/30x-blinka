import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "./route";

describe("GET /api/agreements/[vendorKey]", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("forwards the user identity so the API can resolve the company", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("{}", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const request = new NextRequest("http://localhost/api/agreements/globex", {
      headers: { "X-User-Id": "user-1", "X-User-Email": "a@b.test" },
    });

    const response = await GET(request, { params: Promise.resolve({ vendorKey: "globex" }) });

    expect(response.status).toBe(200);
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/agreements\/globex$/);
    const headers = new Headers(init.headers);
    expect(headers.get("X-User-Id")).toBe("user-1");
  });
});
