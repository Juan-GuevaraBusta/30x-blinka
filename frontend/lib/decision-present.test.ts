import { describe, expect, it } from "vitest";

import {
  EVIDENCE_NULL_LABEL,
  formatNullable,
  formatOnFail,
  hasCheckEvidence,
  NULL_LABEL,
  ON_FAIL_NULL_LABEL,
  severityLabel,
  tracePresentation,
  TRACE_NONE_LABEL,
} from "./decision-present";

describe("severityLabel", () => {
  it("matches backend SEVERITY (0 PAGAR, 1 ESCALAR, 2 FRENAR)", () => {
    expect(severityLabel(0)).toBe("OK");
    expect(severityLabel(1)).toBe("Advertencia (Escalar)");
    expect(severityLabel(2)).toBe("Bloqueo (Frenar)");
  });
});

describe("formatNullable", () => {
  it("maps null to no consta", () => {
    expect(formatNullable(null)).toBe(NULL_LABEL);
    expect(formatNullable(undefined)).toBe(NULL_LABEL);
  });

  it("keeps non-empty strings and numbers", () => {
    expect(formatNullable("Globex LLC")).toBe("Globex LLC");
    expect(formatNullable(4200)).toBe("4200");
  });
});

describe("formatOnFail", () => {
  it("keeps FRENAR and ESCALAR", () => {
    expect(formatOnFail("FRENAR")).toBe("FRENAR");
    expect(formatOnFail("ESCALAR")).toBe("ESCALAR");
  });

  it("uses registry phrase when on_fail is null", () => {
    expect(formatOnFail(null)).toBe(ON_FAIL_NULL_LABEL);
    expect(formatOnFail(undefined)).toBe(ON_FAIL_NULL_LABEL);
  });
});

describe("hasCheckEvidence", () => {
  it("is false when evidence is null or both texts are null", () => {
    expect(hasCheckEvidence(null)).toBe(false);
    expect(hasCheckEvidence({ clause: null, quote: null })).toBe(false);
    expect(hasCheckEvidence({ clause: "  ", quote: null })).toBe(false);
  });

  it("is true when clause or quote is present", () => {
    expect(hasCheckEvidence({ clause: "§4.2", quote: null })).toBe(true);
    expect(hasCheckEvidence({ clause: null, quote: "texto" })).toBe(true);
  });

  it("evidence null label is the spec phrase", () => {
    expect(EVIDENCE_NULL_LABEL).toBe("sin cita de cláusula en el registro");
  });
});

describe("tracePresentation", () => {
  it("returns link for https url", () => {
    const url = "https://example.test/trace/run-abc";
    const view = tracePresentation({ url, langsmith_run_id: null });
    expect(view.kind).toBe("link");
    if (view.kind === "link") {
      expect(view.href).toBe(url);
    }
  });

  it("returns sin traza when url is null but langsmith_run_id is set", () => {
    const view = tracePresentation({
      url: null,
      langsmith_run_id: "0192abc-def",
    });
    expect(view).toEqual({ kind: "text", text: TRACE_NONE_LABEL });
  });

  it("rejects javascript and relative urls", () => {
    expect(tracePresentation({ url: "javascript:alert(1)" }).kind).toBe("text");
    expect(tracePresentation({ url: "/runs/1" }).kind).toBe("text");
    expect(tracePresentation({ url: "   " }).kind).toBe("text");
  });
});
