const STORAGE_KEY = "blinka_user_id";

export function getStoredUserId(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  const value = window.localStorage.getItem(STORAGE_KEY);
  return value && value.trim() ? value.trim() : null;
}

export function setStoredUserId(userId: string): void {
  window.localStorage.setItem(STORAGE_KEY, userId);
}

export function clearStoredUserId(): void {
  window.localStorage.removeItem(STORAGE_KEY);
}

/** Client fetch to Next `/api/*` with the demo user header. */
export function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  const userId = getStoredUserId();
  if (userId) {
    headers.set("X-User-Id", userId);
  }
  return fetch(input, { ...init, headers });
}
