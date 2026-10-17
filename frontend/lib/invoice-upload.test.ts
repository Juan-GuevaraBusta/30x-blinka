import { describe, expect, it } from "vitest";

import {
  isAcceptableFileSize,
  isValidUploadSuccessBody,
  MAX_INVOICE_BYTES,
  parseUploadResponse,
  shouldSendUpload,
  validateInvoiceFile,
} from "./invoice-upload";

describe("isAcceptableFileSize", () => {
  it("rejects 0 bytes and above max", () => {
    expect(isAcceptableFileSize(0)).toBe(false);
    expect(isAcceptableFileSize(2_000_001)).toBe(false);
  });

  it("accepts 1 byte and exactly max", () => {
    expect(isAcceptableFileSize(1)).toBe(true);
    expect(isAcceptableFileSize(2_000_000)).toBe(true);
  });
});

describe("validateInvoiceFile", () => {
  it("rejects missing, empty, and oversized files", () => {
    expect(validateInvoiceFile(null).ok).toBe(false);
    expect(validateInvoiceFile(new File([], "empty.pdf")).ok).toBe(false);
    const big = new File([new Uint8Array(2_000_001)], "big.pdf");
    expect(validateInvoiceFile(big).ok).toBe(false);
  });
});

describe("shouldSendUpload", () => {
  const okMeta = {
    invoiceId: "dev-001",
    channel: "pdf_text",
    receivedAt: "2025-12-22T10:00:00Z",
  };

  it("does not send without file, empty file, or oversize", () => {
    expect(shouldSendUpload({ file: null, ...okMeta })).toBe(false);
    expect(
      shouldSendUpload({ file: new File([], "x.pdf"), ...okMeta }),
    ).toBe(false);
    expect(
      shouldSendUpload({
        file: new File([new Uint8Array(2_000_001)], "x.pdf"),
        ...okMeta,
      }),
    ).toBe(false);
  });

  it("sends when file size is in range and metadata valid", () => {
    const file = new File([new Uint8Array(1)], "a.pdf");
    expect(shouldSendUpload({ file, ...okMeta })).toBe(true);
    const maxFile = new File([new Uint8Array(MAX_INVOICE_BYTES)], "max.pdf");
    expect(shouldSendUpload({ file: maxFile, ...okMeta })).toBe(true);
  });
});

describe("parseUploadResponse", () => {
  const body = {
    id: "dec_0042",
    invoice_id: "dev-001",
    decision: "ESCALAR",
    summary: "Escalada de prueba",
    received_at: "2025-12-22T10:00:00Z",
    severity: 1,
    extracted: {},
    checks: [],
    jev_signals: [],
    verifier: { consistent: true, issues: [] },
    next_step: "x",
    trace: {},
    versions: {},
    human_events: [],
  };

  it("accepts only 201 with id, decision and summary", () => {
    const ok = parseUploadResponse(201, body);
    expect(ok.ok).toBe(true);
    if (ok.ok) {
      expect(ok.data.id).toBe("dec_0042");
      expect(ok.data.decision).toBe("ESCALAR");
      expect(ok.data.summary).toBe("Escalada de prueba");
    }
    expect(parseUploadResponse(200, body).ok).toBe(false);
    expect(parseUploadResponse(201, { ...body, decision: "INVALID" }).ok).toBe(false);
    expect(parseUploadResponse(201, { id: "x" }).ok).toBe(false);
  });

  it("maps 409 duplicate and 429 rate limit", () => {
    expect(
      parseUploadResponse(409, { detail: "duplicate_invoice" }).ok,
    ).toBe(false);
    const dup = parseUploadResponse(409, { detail: "duplicate_invoice" });
    if (!dup.ok) {
      expect(dup.message).toMatch(/registrada/);
    }
    const limited = parseUploadResponse(429, { detail: "rate_limited" });
    if (!limited.ok) {
      expect(limited.message).toMatch(/Demasiados/);
    }
  });
});

describe("isValidUploadSuccessBody", () => {
  it("requires decision enum", () => {
    expect(
      isValidUploadSuccessBody({
        id: "a",
        decision: "PAGAR",
        summary: "s",
      }),
    ).toBe(true);
    expect(
      isValidUploadSuccessBody({
        id: "a",
        decision: "MAYBE",
        summary: "s",
      }),
    ).toBe(false);
  });
});
