import { describe, expect, it } from "vitest";
import type { ApprovalRoute } from "./approval-policy-types";
import { catchAllRoute } from "./approval-policy-types";
import {
  addRoute,
  groupsToText,
  matchSummaryLabel,
  moveRouteDown,
  moveRouteUp,
  removeRoute,
  requireSummaryLabel,
  textToGroups,
  validateApprovalPolicyDraft,
} from "./approval-policy-form";

function altoMontoRoute(): ApprovalRoute {
  return {
    id: "alto-monto",
    match: { amount_base_gte: 3000 },
    require: { mode: "approvals", min_approvals: 2, from_groups: ["finanzas", "cfo"] },
  };
}

function marketingRoute(): ApprovalRoute {
  return {
    id: "marketing-cfo",
    match: { department: "Marketing" },
    require: { mode: "approvals", min_approvals: 1, from_groups: ["cfo"] },
  };
}

describe("validateApprovalPolicyDraft", () => {
  it("accepts a valid ordered policy ending in the catch-all", () => {
    const result = validateApprovalPolicyDraft([marketingRoute(), altoMontoRoute(), catchAllRoute()]);
    expect(result.ok).toBe(true);
  });

  it("rejects an empty route list", () => {
    const result = validateApprovalPolicyDraft([]);
    expect(result.ok).toBe(false);
  });

  it("requires the last route to be the empty-match catch-all", () => {
    const result = validateApprovalPolicyDraft([altoMontoRoute()]);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.some((error) => error.includes("Todo lo demás"))).toBe(true);
    }
  });

  it("rejects duplicate route ids", () => {
    const result = validateApprovalPolicyDraft([altoMontoRoute(), { ...altoMontoRoute(), match: {} }]);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.some((error) => error.includes("ya se usa"))).toBe(true);
    }
  });

  it("rejects an approvals route with no groups", () => {
    const route: ApprovalRoute = {
      id: "sin-grupo",
      match: {},
      require: { mode: "approvals", min_approvals: 1, from_groups: [] },
    };
    const result = validateApprovalPolicyDraft([route, catchAllRoute()]);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.some((error) => error.includes("al menos un grupo"))).toBe(true);
    }
  });

  it("rejects an approvals route with min_approvals below 1", () => {
    const route: ApprovalRoute = {
      id: "cero",
      match: {},
      require: { mode: "approvals", min_approvals: 0, from_groups: ["cfo"] },
    };
    const result = validateApprovalPolicyDraft([route, catchAllRoute()]);
    expect(result.ok).toBe(false);
  });

  it("rejects an auto route that still sets min_approvals or groups", () => {
    const route: ApprovalRoute = {
      id: "auto-con-grupo",
      match: {},
      require: { mode: "auto", min_approvals: 1, from_groups: ["cfo"] },
    };
    const result = validateApprovalPolicyDraft([route, catchAllRoute()]);
    expect(result.ok).toBe(false);
  });
});

describe("route table editing", () => {
  it("adds a new route right before the catch-all", () => {
    const routes = [altoMontoRoute(), catchAllRoute()];
    const next = addRoute(routes);
    expect(next).toHaveLength(3);
    expect(next[next.length - 1].id).toBe("todo-lo-demas");
    expect(next[1].id).not.toBe("todo-lo-demas");
  });

  it("never removes the catch-all row", () => {
    const routes = [altoMontoRoute(), catchAllRoute()];
    const result = removeRoute(routes, 1);
    expect(result.ok).toBe(false);
  });

  it("removes a non-catch-all row", () => {
    const routes = [altoMontoRoute(), marketingRoute(), catchAllRoute()];
    const result = removeRoute(routes, 0);
    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.routes).toHaveLength(2);
      expect(result.routes[0].id).toBe("marketing-cfo");
    }
  });

  it("reorders movable rows but keeps the catch-all pinned last", () => {
    const routes = [marketingRoute(), altoMontoRoute(), catchAllRoute()];
    const movedDown = moveRouteDown(routes, 0);
    expect(movedDown[0].id).toBe("alto-monto");
    expect(movedDown[2].id).toBe("todo-lo-demas");

    const unchanged = moveRouteDown(movedDown, 1); // would swap with the catch-all
    expect(unchanged[2].id).toBe("todo-lo-demas");
    expect(unchanged[1].id).toBe("marketing-cfo");

    const movedUp = moveRouteUp(movedDown, 1);
    expect(movedUp[0].id).toBe("marketing-cfo");
  });
});

describe("group text helpers", () => {
  it("round-trips a comma-separated group list", () => {
    const text = groupsToText(["finanzas", "cfo"]);
    expect(text).toBe("finanzas, cfo");
    expect(textToGroups(text)).toEqual(["finanzas", "cfo"]);
  });

  it("drops blanks and duplicates when parsing", () => {
    expect(textToGroups("finanzas, , finanzas,cfo")).toEqual(["finanzas", "cfo"]);
  });
});

describe("summary labels", () => {
  it("summarizes the catch-all match as Todo lo demás", () => {
    expect(matchSummaryLabel(catchAllRoute())).toBe("Todo lo demás");
  });

  it("summarizes an amount-based match", () => {
    expect(matchSummaryLabel(altoMontoRoute())).toBe("Monto ≥ 3000");
  });

  it("summarizes an auto require as automático", () => {
    expect(requireSummaryLabel(catchAllRoute().require)).toBe("Automático (sin aprobación adicional)");
  });

  it("summarizes an approvals require as N de groups", () => {
    expect(requireSummaryLabel(altoMontoRoute().require)).toBe("2 de finanzas o cfo");
  });
});
