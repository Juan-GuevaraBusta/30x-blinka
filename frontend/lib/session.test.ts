import { afterEach, describe, expect, it, vi } from "vitest";

function stubStorage(values: Record<string, string>) {
  const store = new Map(Object.entries(values));
  vi.stubGlobal("window", {
    localStorage: {
      getItem: (k: string) => store.get(k) ?? null,
      setItem: (k: string, v: string) => store.set(k, v),
      removeItem: (k: string) => store.delete(k),
    },
  });
}

describe("apiFetch identity forwarding (T9.8)", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    vi.resetModules();
  });

  it("sends the stored user id and email", async () => {
    stubStorage({ blinka_user_id: "uuid-1", blinka_user_email: "ana@beta.test" });
    const fetchMock = vi.fn(async () => new Response("{}"));
    vi.stubGlobal("fetch", fetchMock);
    const { apiFetch } = await import("@/lib/session");

    await apiFetch("/api/me", { headers: { Accept: "application/json" } });

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    const headers = init.headers as Headers;
    expect(headers.get("X-User-Id")).toBe("uuid-1");
    expect(headers.get("X-User-Email")).toBe("ana@beta.test");
    expect(headers.get("Accept")).toBe("application/json");
  });

  it("sends nothing when signed out", async () => {
    stubStorage({});
    const fetchMock = vi.fn(async () => new Response("{}"));
    vi.stubGlobal("fetch", fetchMock);
    const { apiFetch } = await import("@/lib/session");

    await apiFetch("/api/me");

    const [, init] = fetchMock.mock.calls[0] as unknown as [string, RequestInit];
    expect((init.headers as Headers).get("X-User-Id")).toBeNull();
  });
});
