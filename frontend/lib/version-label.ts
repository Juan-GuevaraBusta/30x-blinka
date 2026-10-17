import type { RulesConfig } from "./rules-types";
import { canonicalJson } from "./canonical-json";

export async function versionLabel(document: RulesConfig): Promise<string> {
  const data = new TextEncoder().encode(canonicalJson(document));
  const digest = await crypto.subtle.digest("SHA-256", data);
  const hex = Array.from(new Uint8Array(digest))
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
  return hex.slice(0, 12);
}
