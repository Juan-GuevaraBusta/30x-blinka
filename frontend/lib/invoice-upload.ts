import type { Decision } from "@/lib/decision-types";

export const MAX_INVOICE_BYTES = 2_000_000;

export const INVOICE_CHANNELS = ["pdf_text", "image", "email", "chat"] as const;
export type InvoiceChannel = (typeof INVOICE_CHANNELS)[number];

const DECISIONS: readonly Decision[] = ["PAGAR", "ESCALAR", "FRENAR"];

export const MSG_FILE_MISSING = "Elija un archivo de factura antes de enviar.";
export const MSG_FILE_EMPTY = "El archivo está vacío. Elija otro archivo.";
export const MSG_FILE_TOO_LARGE = `El archivo supera el límite de ${MAX_INVOICE_BYTES.toLocaleString("es")} bytes.`;
export const MSG_INVOICE_ID_INVALID =
  "El identificador de factura debe tener entre 1 y 64 caracteres sin espacios.";
export const MSG_CHANNEL_INVALID = "Elija un canal válido (pdf_text, image, email o chat).";
export const MSG_RECEIVED_AT_INVALID =
  "La fecha de recepción debe ser ISO-8601 con zona horaria (por ejemplo 2025-12-22T10:00:00Z).";
export const MSG_METADATA_INCOMPLETE = "Complete el identificador, el canal y la fecha de recepción.";
export const MSG_NETWORK =
  "El API no respondió. Compruebe que el servidor esté en marcha e intente de nuevo.";
export const MSG_BODY_INCOMPLETE =
  "La respuesta del servidor no incluye un registro de decisión válido; no se muestra ninguna decisión.";
export const MSG_RATE_LIMITED =
  "Demasiados envíos seguidos. Espere un momento e intente de nuevo.";
export const MSG_DUPLICATE =
  "Esa factura ya está registrada con el mismo identificador.";
export const MSG_SERVER_REJECTED =
  "El servidor rechazó los datos del envío. Revise archivo y metadatos.";
export const MSG_FILE_REJECTED_SERVER =
  "El servidor rechazó el archivo por tamaño o contenido inválido.";

export function isAcceptableFileSize(bytes: number): boolean {
  return bytes >= 1 && bytes <= MAX_INVOICE_BYTES;
}

export function validateInvoiceId(id: string): boolean {
  return id.length >= 1 && id.length <= 64 && /^\S+$/.test(id);
}

export function isInvoiceChannel(value: string): value is InvoiceChannel {
  return (INVOICE_CHANNELS as readonly string[]).includes(value);
}

/** ISO-8601 with explicit timezone (Z or ±HH:MM). */
export function validateReceivedAt(value: string): boolean {
  const trimmed = value.trim();
  if (trimmed.length === 0) {
    return false;
  }
  if (!/Z$|[+-]\d{2}:\d{2}$/.test(trimmed)) {
    return false;
  }
  return !Number.isNaN(Date.parse(trimmed));
}

export type FileValidation =
  | { ok: true }
  | { ok: false; message: string };

export function validateInvoiceFile(file: File | null): FileValidation {
  if (!file) {
    return { ok: false, message: MSG_FILE_MISSING };
  }
  if (file.size === 0) {
    return { ok: false, message: MSG_FILE_EMPTY };
  }
  if (file.size > MAX_INVOICE_BYTES) {
    return { ok: false, message: MSG_FILE_TOO_LARGE };
  }
  return { ok: true };
}

export function shouldSendUpload(params: {
  file: File | null;
  invoiceId: string;
  channel: string;
  receivedAt: string;
}): boolean {
  const fileCheck = validateInvoiceFile(params.file);
  if (!fileCheck.ok) {
    return false;
  }
  const invoiceId = params.invoiceId.trim();
  if (!validateInvoiceId(invoiceId)) {
    return false;
  }
  if (!isInvoiceChannel(params.channel)) {
    return false;
  }
  if (!validateReceivedAt(params.receivedAt)) {
    return false;
  }
  return true;
}

export function validateUploadForm(params: {
  file: File | null;
  invoiceId: string;
  channel: string;
  receivedAt: string;
}): FileValidation {
  const fileCheck = validateInvoiceFile(params.file);
  if (!fileCheck.ok) {
    return fileCheck;
  }
  if (!validateInvoiceId(params.invoiceId.trim())) {
    return { ok: false, message: MSG_INVOICE_ID_INVALID };
  }
  if (!isInvoiceChannel(params.channel)) {
    return { ok: false, message: MSG_CHANNEL_INVALID };
  }
  if (!validateReceivedAt(params.receivedAt)) {
    return { ok: false, message: MSG_RECEIVED_AT_INVALID };
  }
  return { ok: true };
}

function isDecision(value: unknown): value is Decision {
  return typeof value === "string" && (DECISIONS as readonly string[]).includes(value);
}

export function isValidUploadSuccessBody(body: unknown): boolean {
  if (!body || typeof body !== "object") {
    return false;
  }
  const record = body as Record<string, unknown>;
  return (
    typeof record.id === "string" &&
    record.id.length > 0 &&
    isDecision(record.decision) &&
    typeof record.summary === "string" &&
    record.summary.length > 0
  );
}

export type UploadSuccessPayload = {
  id: string;
  decision: Decision;
  summary: string;
  fullRecord: unknown;
};

export type UploadParseResult =
  | { ok: true; data: UploadSuccessPayload }
  | { ok: false; message: string };

export function parseUploadResponse(status: number, body: unknown): UploadParseResult {
  if (status !== 201) {
    const detail =
      body && typeof body === "object" && typeof (body as { detail?: unknown }).detail === "string"
        ? (body as { detail: string }).detail
        : undefined;
    return { ok: false, message: uploadHttpErrorMessage(status, detail) };
  }
  if (!isValidUploadSuccessBody(body)) {
    return { ok: false, message: MSG_BODY_INCOMPLETE };
  }
  const record = body as Record<string, unknown>;
  return {
    ok: true,
    data: {
      id: record.id as string,
      decision: record.decision as Decision,
      summary: record.summary as string,
      fullRecord: body,
    },
  };
}

export function uploadHttpErrorMessage(status: number, detail?: string): string {
  if (status === 422) {
    if (detail === "invalid_file_size") {
      return MSG_FILE_REJECTED_SERVER;
    }
    return MSG_SERVER_REJECTED;
  }
  if (status === 409) {
    if (detail === "duplicate_invoice") {
      return MSG_DUPLICATE;
    }
    return MSG_DUPLICATE;
  }
  if (status === 429) {
    return MSG_RATE_LIMITED;
  }
  if (status >= 500) {
    return MSG_NETWORK;
  }
  return `No se pudo registrar la factura (HTTP ${status}).`;
}
