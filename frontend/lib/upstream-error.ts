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

export type UpstreamFetchResult =
  | { ok: true; response: Response; text: string }
  | { ok: false; errorResponse: NextResponse };

/**
 * Shared fetch+read for every /api/** proxy (R4). Guards both failure points: the initial
 * `fetch` throwing (upstream unreachable) and `response.text()` rejecting (connection reset
 * after headers arrive). Either one now yields the same 502 upstream_unreachable body instead
 * of an unhandled rejection.
 */
export async function fetchUpstreamText(
  url: string,
  init?: RequestInit,
): Promise<UpstreamFetchResult> {
  try {
    const response = await fetch(url, init);
    const text = await response.text();
    return { ok: true, response, text };
  } catch {
    return { ok: false, errorResponse: upstreamUnreachableResponse() };
  }
}
