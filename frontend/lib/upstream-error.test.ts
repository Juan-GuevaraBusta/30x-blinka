import { afterEach, describe, expect, it, vi } from "vitest";

import {
  UPSTREAM_UNREACHABLE_DETAIL,
  UPSTREAM_UNREACHABLE_STATUS,
  fetchUpstreamText,
  upstreamUnreachableResponse,
} from "./upstream-error";

describe("upstreamUnreachableResponse", () => {
  it("returns a 502 with the upstream_unreachable detail", async () => {
    const res = upstreamUnreachableResponse();
    expect(res.status).toBe(UPSTREAM_UNREACHABLE_STATUS);
    expect(res.status).toBe(502);
    const body = (await res.json()) as { detail: string };
    expect(body.detail).toBe(UPSTREAM_UNREACHABLE_DETAIL);
    expect(body.detail).toBe("upstream_unreachable");
  });
});

describe("fetchUpstreamText (R4)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("returns the upstream response and its body text on success", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => new Response('{"ok":true}', { status: 201 })),
    );

    const result = await fetchUpstreamText("http://upstream.test/x");

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.text).toBe('{"ok":true}');
      expect(result.response.status).toBe(201);
    }
  });

  it("returns upstream_unreachable when fetch itself throws", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("ECONNREFUSED");
      }),
    );

    const result = await fetchUpstreamText("http://upstream.test/x");

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errorResponse.status).toBe(502);
      expect(await result.errorResponse.json()).toEqual({ detail: "upstream_unreachable" });
    }
  });

  it("returns upstream_unreachable when fetch resolves but response.text() rejects (connection reset after headers)", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        const rejecting = {
          status: 200,
          headers: new Headers({ "Content-Type": "application/json" }),
          text: () => Promise.reject(new Error("ECONNRESET")),
        };
        return rejecting as unknown as Response;
      }),
    );

    const result = await fetchUpstreamText("http://upstream.test/x");

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errorResponse.status).toBe(502);
      expect(await result.errorResponse.json()).toEqual({ detail: "upstream_unreachable" });
    }
  });
});
