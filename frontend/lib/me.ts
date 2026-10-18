import { useSyncExternalStore } from "react";

import { apiFetch } from "@/lib/session";

/** `GET /me` (T9.8, D067). */
export type MeCompany = {
  id: string;
  name: string;
  base_currency: string;
  is_demo: boolean;
  configured: boolean;
};

export type MeMember = {
  user_id: string;
  email: string;
  role: "admin" | "member" | string;
  approver_groups: string[];
  is_approver: boolean;
};

export type Me = {
  user_id: string;
  email: string | null;
  company: MeCompany | null;
  member: MeMember | null;
};

let cached: Me | null = null;
const listeners = new Set<() => void>();

export function setMe(me: Me | null): void {
  cached = me;
  for (const listener of listeners) listener();
}

export function getMe(): Me | null {
  return cached;
}

/** Fetch and cache `/api/me`. `null` when the call fails (UI stays usable; the API still enforces). */
export async function fetchMe(): Promise<Me | null> {
  try {
    const res = await apiFetch("/api/me", { cache: "no-store" });
    if (!res.ok) return null;
    const me = (await res.json()) as Me;
    setMe(me);
    return me;
  } catch {
    return null;
  }
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useMe(): Me | null {
  return useSyncExternalStore(subscribe, getMe, () => null);
}

export function roleLabel(role: string | undefined): string {
  if (role === "admin") return "Administrador";
  if (role === "member") return "Miembro";
  return "";
}
