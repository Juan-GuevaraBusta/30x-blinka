import { NextResponse } from "next/server";

export const UPSTREAM_UNREACHABLE_STATUS = 502;
export const UPSTREAM_UNREACHABLE_DETAIL = "upstream_unreachable";

/** Shared 502 body for every /api/** proxy when the upstream `fetch` throws (T6.7, D057). */
export function upstreamUnreachableResponse(): NextResponse {
  return NextResponse.json(
    { detail: UPSTREAM_UNREACHABLE_DETAIL },
    { status: UPSTREAM_UNREACHABLE_STATUS },
  );
}
