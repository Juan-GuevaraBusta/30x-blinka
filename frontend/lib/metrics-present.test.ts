import { describe, expect, it } from "vitest";

import {
  classifyMetricsBody,
  METRICS_EMPTY_MESSAGE,
  METRICS_INVALID_BODY_MESSAGE,
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
