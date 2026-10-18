import { describe, expect, it } from "vitest";

import {
  classifyMetricsBody,
  EVALUATION_EMPTY_MESSAGE,
  EVALUATION_INVALID_BODY_MESSAGE,
  LIVE_METRICS_EMPTY_MESSAGE,
  LIVE_METRICS_INVALID_BODY_MESSAGE,
  METRICS_EMPTY_MESSAGE,
  METRICS_INVALID_BODY_MESSAGE,
  presentEvaluationFromResponse,
  presentLiveMetricsFromResponse,
  presentMetricsFromResponse,
} from "./metrics-present";

describe("classifyMetricsBody", () => {
  it("returns empty when source is none", () => {
    const view = classifyMetricsBody({
      source: "none",
      unsafe_pay: 2,
      autonomy_pct: 15.5,
    });
    expect(view.kind).toBe("empty");
    if (view.kind === "empty") {
      expect(view.message).toBe(METRICS_EMPTY_MESSAGE);
    }
  });

  it("returns empty when either metric is null", () => {
    expect(
      classifyMetricsBody({ source: "report", unsafe_pay: null, autonomy_pct: 10 }).kind,
    ).toBe("empty");
    expect(
      classifyMetricsBody({ source: "report", unsafe_pay: 0, autonomy_pct: null }).kind,
    ).toBe("empty");
  });

  it("shows report with zero unsafe_pay and no block", () => {
    const view = classifyMetricsBody({
      source: "report",
      unsafe_pay: 0,
      autonomy_pct: 42,
    });
    expect(view).toMatchObject({
      kind: "report",
      unsafe_pay: 0,
      autonomy_pct: 42,
      blocked: false,
    });
  });

  it("treats 0.0 as zero without block", () => {
    const view = classifyMetricsBody({
      source: "report",
      unsafe_pay: 0.0,
      autonomy_pct: 1,
    });
    expect(view.kind).toBe("report");
    if (view.kind === "report") {
      expect(view.blocked).toBe(false);
    }
  });

  it("shows block for synthetic report 2 / 15.5", () => {
    const view = classifyMetricsBody({
      source: "report",
      unsafe_pay: 2,
      autonomy_pct: 15.5,
    });
    expect(view).toMatchObject({
      kind: "report",
      unsafe_pay: 2,
      autonomy_pct: 15.5,
      blocked: true,
    });
  });

  it("blocks any non-zero unsafe_pay including negatives", () => {
    const view = classifyMetricsBody({
      source: "report",
      unsafe_pay: -1,
      autonomy_pct: 5,
    });
    expect(view.kind).toBe("report");
    if (view.kind === "report") {
      expect(view.blocked).toBe(true);
    }
  });
});

describe("presentMetricsFromResponse", () => {
  it("returns error on non-200 without inventing zeros", () => {
    const view = presentMetricsFromResponse(500, {
      unsafe_pay: 0,
      autonomy_pct: 0,
      source: "report",
    });
    expect(view.kind).toBe("error");
  });

  it("returns error for invalid body on 200", () => {
    const view = presentMetricsFromResponse(200, { source: "report" });
    expect(view.kind).toBe("error");
    if (view.kind === "error") {
      expect(view.message).toBe(METRICS_INVALID_BODY_MESSAGE);
    }
  });

  it("maps API empty payload", () => {
    const view = presentMetricsFromResponse(200, {
      unsafe_pay: null,
      autonomy_pct: null,
      source: "none",
    });
    expect(view.kind).toBe("empty");
  });
});

describe("presentLiveMetricsFromResponse", () => {
  it("returns empty when total is zero", () => {
    const view = presentLiveMetricsFromResponse(200, {
      total: 0,
      pagar: 0,
      frenar: 0,
      escalar: 0,
      auto_decided_pct: null,
      pending_approvals: 0,
      approved_by_humans: 0,
    });
    expect(view.kind).toBe("empty");
    if (view.kind === "empty") {
      expect(view.message).toBe(LIVE_METRICS_EMPTY_MESSAGE);
    }
  });

  it("returns data with the counters when total is positive", () => {
    const body = {
      total: 5,
      pagar: 2,
      frenar: 1,
      escalar: 2,
      auto_decided_pct: 60,
      pending_approvals: 1,
      approved_by_humans: 1,
    };
    const view = presentLiveMetricsFromResponse(200, body);
    expect(view).toEqual({ kind: "data", metrics: body });
  });

  it("returns error on non-200", () => {
    const view = presentLiveMetricsFromResponse(500, { detail: "boom" });
    expect(view.kind).toBe("error");
  });

  it("returns error for an invalid body on 200", () => {
    const view = presentLiveMetricsFromResponse(200, { total: 1 });
    expect(view.kind).toBe("error");
    if (view.kind === "error") {
      expect(view.message).toBe(LIVE_METRICS_INVALID_BODY_MESSAGE);
    }
  });
});

describe("presentEvaluationFromResponse", () => {
  it("returns empty when entries is empty", () => {
    const view = presentEvaluationFromResponse(200, {
      entries: [],
      generated_at: null,
      source: "none",
    });
    expect(view.kind).toBe("empty");
    if (view.kind === "empty") {
      expect(view.message).toBe(EVALUATION_EMPTY_MESSAGE);
    }
  });

  it("returns data with entries and their source", () => {
    const entries = [
      { id: "holdout", label: "Holdout", value: "pendiente T5.1", source: "eval/reports/latest.md" },
      { id: "e2e_dev_unsafe_pay", label: "unsafe_pay", value: 0, source: "eval/reports/verifier_tuning.md" },
    ];
    const view = presentEvaluationFromResponse(200, {
      entries,
      generated_at: "2026-10-18T00:00:00Z",
      source: "report",
    });
    expect(view).toEqual({ kind: "data", entries, generated_at: "2026-10-18T00:00:00Z" });
  });

  it("returns error on non-200", () => {
    const view = presentEvaluationFromResponse(500, {});
    expect(view.kind).toBe("error");
  });

  it("returns error for an invalid body on 200", () => {
    const view = presentEvaluationFromResponse(200, { entries: [{ id: "x" }] });
    expect(view.kind).toBe("error");
    if (view.kind === "error") {
      expect(view.message).toBe(EVALUATION_INVALID_BODY_MESSAGE);
    }
  });
});
