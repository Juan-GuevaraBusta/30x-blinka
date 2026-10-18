const STORAGE_KEY = "blinka_user_id";
const EMAIL_KEY = "blinka_user_email";

/**
 * Hackathon identity (T9.8, D067): the Supabase user id and email are stored at
 * login and sent as `X-User-Id` / `X-User-Email`. The API does not verify the
 * Supabase JWT yet — see docs/T9_8_SPEC.md §5.
 */
function read(key: string): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  const value = window.localStorage.getItem(key);
  return value && value.trim() ? value.trim() : null;
}

export function getStoredUserId(): string | null {
  return read(STORAGE_KEY);
}

export function getStoredUserEmail(): string | null {
  return read(EMAIL_KEY);
}

export function setStoredUserId(userId: string): void {
  window.localStorage.setItem(STORAGE_KEY, userId);
}

export function setStoredUser(userId: string, email: string | null | undefined): void {
  window.localStorage.setItem(STORAGE_KEY, userId);
  if (email && email.trim()) {
    window.localStorage.setItem(EMAIL_KEY, email.trim().toLowerCase());
  } else {
    window.localStorage.removeItem(EMAIL_KEY);
  }
}

export function clearStoredUserId(): void {
  window.localStorage.removeItem(STORAGE_KEY);
  window.localStorage.removeItem(EMAIL_KEY);
}

/** Identity headers for a client fetch to Next `/api/*`. */
export function identityHeaders(init?: HeadersInit): Headers {
  const headers = new Headers(init);
  const userId = getStoredUserId();
  if (userId) {
    headers.set("X-User-Id", userId);
  }
  const email = getStoredUserEmail();
  if (email) {
    headers.set("X-User-Email", email);
  }
  return headers;
}

/** Client fetch to Next `/api/*` with the demo user headers. */
export function apiFetch(input: string, init?: RequestInit): Promise<Response> {
  return fetch(input, { ...init, headers: identityHeaders(init?.headers) });
}
