import type { CheckEvidence, TraceRef } from "@/lib/decision-types";

export const NULL_LABEL = "no consta";
export const ON_FAIL_NULL_LABEL = "sin acción de fallo en el registro";
export const EVIDENCE_NULL_LABEL = "sin cita de cláusula en el registro";
export const TRACE_NONE_LABEL = "sin traza";
export const TRACE_LINK_LABEL = "Traza guardada en el registro (abre en pestaña nueva)";

// T6.7 (D057): mirrors backend/app/models/domain.py SEVERITY (0 PAGAR, 1 ESCALAR, 2 FRENAR).
export const SEVERITY_LABELS: Record<0 | 1 | 2, string> = {
  0: "OK",
  1: "Advertencia (Escalar)",
  2: "Bloqueo (Frenar)",
};

export function severityLabel(severity: 0 | 1 | 2): string {
  return SEVERITY_LABELS[severity];
}

export function isValidDecisionId(id: string): boolean {
  const trimmed = id.trim();
  if (trimmed.length === 0) return false;
  if (trimmed.includes("/") || trimmed.includes("..")) return false;
  return true;
}

export function formatNullable(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return NULL_LABEL;
  if (typeof value === "number") {
    if (Number.isNaN(value)) return NULL_LABEL;
    return String(value);
  }
  const text = value.trim();
  return text.length === 0 ? NULL_LABEL : value;
}

export function formatOnFail(onFail: string | null | undefined): string {
  if (onFail === "FRENAR" || onFail === "ESCALAR") return onFail;
  return ON_FAIL_NULL_LABEL;
}

export function hasCheckEvidence(evidence: CheckEvidence | null | undefined): boolean {
  if (!evidence) return false;
  const clause = evidence.clause?.trim() ?? "";
  const quote = evidence.quote?.trim() ?? "";
  return clause.length > 0 || quote.length > 0;
}

export type TracePresentation =
  | { kind: "link"; href: string; label: string }
  | { kind: "text"; text: string };

export function tracePresentation(trace: TraceRef | null | undefined): TracePresentation {
  const raw = trace?.url;
  if (raw === null || raw === undefined) {
    return { kind: "text", text: TRACE_NONE_LABEL };
  }
  const url = raw.trim();
  if (url.length === 0) {
    return { kind: "text", text: TRACE_NONE_LABEL };
  }
  let parsed: URL;
  try {
    parsed = new URL(url);
  } catch {
    return { kind: "text", text: TRACE_NONE_LABEL };
  }
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    return { kind: "text", text: TRACE_NONE_LABEL };
  }
  return { kind: "link", href: url, label: TRACE_LINK_LABEL };
}
