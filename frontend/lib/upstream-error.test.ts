import { describe, expect, it } from "vitest";

import {
  UPSTREAM_UNREACHABLE_DETAIL,
  UPSTREAM_UNREACHABLE_STATUS,
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
