/**
 * Mirrors `backend/app/models/rules_config.py` `ApprovalPolicy` (T7.1, D059).
 * Read-only contract shape — this file never implements rule logic, only the
 * document shape the `/reglas/politica` editor reads from and writes back to
 * `approval_policy` inside the `RulesConfig` document returned by `GET /rules`.
 */

export type RouteApprovalMode = "auto" | "approvals";

export interface RouteMatch {
  amount_base_gte?: number | null;
  amount_base_lt?: number | null;
  beneficiary?: string | null;
  department?: string | null;
  invoice_type?: string | null;
}

export interface RouteRequire {
  mode: RouteApprovalMode;
  min_approvals?: number | null;
  from_groups: string[];
}

export interface ApprovalRoute {
  id: string;
  match: RouteMatch;
  require: RouteRequire;
}

export interface ApprovalPolicy {
  routes: ApprovalRoute[];
}

export function emptyRouteMatch(): RouteMatch {
  return {};
}

/** True when every `match` field is unset (the backend's catch-all shape, T7.1 §2). */
export function isEmptyMatch(match: RouteMatch): boolean {
  return (
    (match.amount_base_gte ?? null) === null &&
    (match.amount_base_lt ?? null) === null &&
    (match.beneficiary ?? null) === null &&
    (match.department ?? null) === null &&
    (match.invoice_type ?? null) === null
  );
}

export const CATCH_ALL_ROUTE_ID = "todo-lo-demas";

/** The fixed, non-removable last row: "Todo lo demás" (T7.5 §2). */
export function catchAllRoute(): ApprovalRoute {
  return {
    id: CATCH_ALL_ROUTE_ID,
    match: emptyRouteMatch(),
    require: { mode: "auto", min_approvals: null, from_groups: [] },
  };
}

export function emptyApprovalPolicy(): ApprovalPolicy {
  return { routes: [catchAllRoute()] };
}
