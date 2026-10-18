// T9.2 (D061) §5 — types and pure helpers for the `/bandeja` screen and its proxies.

export type InboxClassification = "es_factura" | "no_es_factura" | "revision";
export type InboxClassifiedBy = "rules" | "llm" | "human";
export type InboxEventAction = "procesada_humano" | "descartada_humano";

export type InboxSignal = {
  id: string;
  points: number;
  evidence: string;
};

export type InboxEvent = {
  author: string;
  at: string;
  action: InboxEventAction;
  reason: string;
};

export type InboxMessage = {
  id: string;
  owner_id: string;
  message_id: string;
  from_addr: string;
  subject: string;
  received_at: string;
  classification: InboxClassification;
  score: number;
  signals: InboxSignal[];
  reason: string;
  classified_by: InboxClassifiedBy;
  decision_id: string | null;
  events: InboxEvent[];
};

export const CLASSIFICATION_LABELS: Record<InboxClassification, string> = {
  es_factura: "Factura",
  no_es_factura: "No es factura",
  revision: "Revisión humana",
};

export function classificationLabel(classification: InboxClassification): string {
  return CLASSIFICATION_LABELS[classification];
}

export function classificationToneClass(classification: InboxClassification): string {
  if (classification === "es_factura") return "text-success";
  if (classification === "revision") return "text-accent";
  return "text-ink-muted";
}

/** Mirrors `lib/decision-present.ts::isValidDecisionId`: no path traversal. */
export function isValidInboxId(id: string): boolean {
  const trimmed = id.trim();
  if (trimmed.length === 0) return false;
  if (trimmed.includes("/") || trimmed.includes("..")) return false;
  return true;
}

function isInboxSignal(value: unknown): value is InboxSignal {
  if (!value || typeof value !== "object") return false;
  const s = value as Partial<InboxSignal>;
  return typeof s.id === "string" && typeof s.points === "number" && typeof s.evidence === "string";
}

function isInboxEvent(value: unknown): value is InboxEvent {
  if (!value || typeof value !== "object") return false;
  const e = value as Partial<InboxEvent>;
  return (
    typeof e.author === "string" &&
    typeof e.at === "string" &&
    (e.action === "procesada_humano" || e.action === "descartada_humano") &&
    typeof e.reason === "string"
  );
}

export function isInboxMessage(value: unknown): value is InboxMessage {
  if (!value || typeof value !== "object") return false;
  const m = value as Partial<InboxMessage>;
  return (
    typeof m.id === "string" &&
    m.id.length > 0 &&
    typeof m.message_id === "string" &&
    typeof m.from_addr === "string" &&
    typeof m.subject === "string" &&
    typeof m.received_at === "string" &&
    (m.classification === "es_factura" ||
      m.classification === "no_es_factura" ||
      m.classification === "revision") &&
    typeof m.score === "number" &&
    Array.isArray(m.signals) &&
    m.signals.every(isInboxSignal) &&
    typeof m.reason === "string" &&
    (m.classified_by === "rules" || m.classified_by === "llm" || m.classified_by === "human") &&
    (m.decision_id === null || typeof m.decision_id === "string") &&
    Array.isArray(m.events) &&
    m.events.every(isInboxEvent)
  );
}

export function parseInboxList(payload: unknown): InboxMessage[] {
  if (!Array.isArray(payload)) {
    throw new Error("INVALID_BODY");
  }
  for (const item of payload) {
    if (!isInboxMessage(item)) {
      throw new Error("INVALID_BODY");
    }
  }
  return payload;
}
