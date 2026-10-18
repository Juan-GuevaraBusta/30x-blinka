import type { ApprovalPolicy, ApprovalRoute, RouteRequire } from "./approval-policy-types";
import { catchAllRoute, isEmptyMatch } from "./approval-policy-types";

export type ApprovalPolicyValidation =
  | { ok: true; policy: ApprovalPolicy }
  | { ok: false; errors: string[] };

/**
 * Client-side gate before `PUT /rules`; mirrors
 * `backend/app/models/rules_config.py` (`ApprovalPolicy`, `RouteRequire`) so the
 * editor rejects most mistakes before the server does (T7.5 §2).
 */
export function validateApprovalPolicyDraft(routes: ApprovalRoute[]): ApprovalPolicyValidation {
  const errors: string[] = [];

  if (routes.length === 0) {
    return { ok: false, errors: ["La política debe tener al menos una ruta."] };
  }

  const ids = routes.map((route) => route.id.trim());
  ids.forEach((id, index) => {
    if (!id) {
      errors.push(`Ruta ${index + 1}: el nombre no puede quedar vacío.`);
    }
  });
  const seen = new Set<string>();
  ids.forEach((id, index) => {
    if (!id) return;
    if (seen.has(id)) {
      errors.push(`Ruta ${index + 1}: el nombre «${id}» ya se usa en otra ruta.`);
    }
    seen.add(id);
  });

  const last = routes[routes.length - 1];
  if (!isEmptyMatch(last.match)) {
    errors.push('La última ruta debe ser «Todo lo demás», sin condiciones.');
  }

  routes.forEach((route, index) => {
    errors.push(...validateRequire(route.require, index + 1));
  });

  if (errors.length > 0) {
    return { ok: false, errors };
  }
  return { ok: true, policy: { routes } };
}

function validateRequire(require: RouteRequire, position: number): string[] {
  const errors: string[] = [];
  if (require.mode === "auto") {
    if (require.min_approvals !== null && require.min_approvals !== undefined) {
      errors.push(`Ruta ${position}: el modo automático no debe fijar un número de aprobaciones.`);
    }
    if (require.from_groups.length > 0) {
      errors.push(`Ruta ${position}: el modo automático no debe fijar grupos.`);
    }
    return errors;
  }
  if (require.min_approvals === null || require.min_approvals === undefined || require.min_approvals < 1) {
    errors.push(`Ruta ${position}: el número de aprobaciones debe ser 1 o más.`);
  }
  if (require.from_groups.length === 0) {
    errors.push(`Ruta ${position}: indique al menos un grupo que pueda aprobar.`);
  }
  const blankIndex = require.from_groups.findIndex((group) => !group.trim());
  if (blankIndex !== -1) {
    errors.push(`Ruta ${position}: los nombres de grupo no pueden quedar en blanco.`);
  }
  const unique = new Set(require.from_groups.map((group) => group.trim()));
  if (unique.size !== require.from_groups.length) {
    errors.push(`Ruta ${position}: los grupos no pueden repetirse.`);
  }
  return errors;
}

/** New blank "approvals" route inserted right before the fixed catch-all row. */
export function newRouteTemplate(existingIds: string[]): ApprovalRoute {
  let n = 1;
  let id = `ruta-nueva-${n}`;
  while (existingIds.includes(id)) {
    n += 1;
    id = `ruta-nueva-${n}`;
  }
  return {
    id,
    match: {},
    require: { mode: "approvals", min_approvals: 1, from_groups: [] },
  };
}

export function addRoute(routes: ApprovalRoute[]): ApprovalRoute[] {
  const existingIds = routes.map((route) => route.id);
  const next = [...routes];
  next.splice(next.length - 1, 0, newRouteTemplate(existingIds));
  return next;
}

export type RemoveRouteResult = { ok: true; routes: ApprovalRoute[] } | { ok: false; error: string };

/** The last row ("Todo lo demás") can never be removed (T7.5 §2). */
export function removeRoute(routes: ApprovalRoute[], index: number): RemoveRouteResult {
  if (index === routes.length - 1) {
    return { ok: false, error: 'No se puede borrar la ruta «Todo lo demás».' };
  }
  if (index < 0 || index >= routes.length) {
    return { ok: false, error: "Posición de ruta inválida." };
  }
  const next = [...routes];
  next.splice(index, 1);
  return { ok: true, routes: next };
}

/** The catch-all row at the end is pinned; only the rows before it can reorder. */
function isMovable(routes: ApprovalRoute[], index: number): boolean {
  return index >= 0 && index < routes.length - 1;
}

export function moveRouteUp(routes: ApprovalRoute[], index: number): ApprovalRoute[] {
  if (!isMovable(routes, index) || index === 0) return routes;
  const next = [...routes];
  [next[index - 1], next[index]] = [next[index], next[index - 1]];
  return next;
}

export function moveRouteDown(routes: ApprovalRoute[], index: number): ApprovalRoute[] {
  if (!isMovable(routes, index) || index >= routes.length - 2) return routes;
  const next = [...routes];
  [next[index + 1], next[index]] = [next[index], next[index + 1]];
  return next;
}

/** `require.from_groups` <-> the comma-separated text shown in the "Quién aprueba" field. */
export function groupsToText(groups: string[]): string {
  return groups.join(", ");
}

export function textToGroups(text: string): string[] {
  const seen = new Set<string>();
  const groups: string[] = [];
  for (const raw of text.split(",")) {
    const group = raw.trim();
    if (!group || seen.has(group)) continue;
    seen.add(group);
    groups.push(group);
  }
  return groups;
}

/** "Cuándo aplica" summary cell, in plain Spanish, from a route's `match`. */
export function matchSummaryLabel(route: ApprovalRoute): string {
  const { match } = route;
  if (isEmptyMatch(match)) return "Todo lo demás";
  const parts: string[] = [];
  if (match.amount_base_gte !== null && match.amount_base_gte !== undefined) {
    parts.push(`Monto ≥ ${match.amount_base_gte}`);
  }
  if (match.amount_base_lt !== null && match.amount_base_lt !== undefined) {
    parts.push(`Monto < ${match.amount_base_lt}`);
  }
  if (match.department) {
    parts.push(`Departamento: ${match.department}`);
  }
  if (match.beneficiary) {
    parts.push(`Proveedor: ${match.beneficiary}`);
  }
  if (match.invoice_type) {
    parts.push(`Tipo de factura: ${match.invoice_type}`);
  }
  return parts.join(" y ");
}

/** "Aprobaciones" summary cell, in plain Spanish, from a route's `require`. */
export function requireSummaryLabel(require: RouteRequire): string {
  if (require.mode === "auto") {
    return "Automático (sin aprobación adicional)";
  }
  const groups = require.from_groups.join(" o ");
  return `${require.min_approvals ?? 0} de ${groups || "ningún grupo"}`;
}

export { catchAllRoute };
