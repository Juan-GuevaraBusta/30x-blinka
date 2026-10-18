// T5.10 (D055): badge data for GET /decisions/verify-chain. Pure helpers only
// (no fetch here) so they are testable without a DOM or a network mock.

export type ChainVerification = {
  ok: boolean;
  length: number;
  first_broken_id: string | null;
};

export function isChainVerification(value: unknown): value is ChainVerification {
  if (!value || typeof value !== "object") return false;
  const v = value as Partial<ChainVerification>;
  return (
    typeof v.ok === "boolean" &&
    typeof v.length === "number" &&
    (v.first_broken_id === null || typeof v.first_broken_id === "string")
  );
}

/** "Registro íntegro ✓" or "Registro alterado en <id>" (spec §2, badge wording). */
export function chainBadgeLabel(result: ChainVerification): string {
  if (result.ok) {
    return "Registro íntegro ✓";
  }
  return `Registro alterado en ${result.first_broken_id ?? "posición desconocida"}`;
}

export function chainBadgeToneClass(result: ChainVerification): string {
  return result.ok ? "text-success" : "text-danger";
}
