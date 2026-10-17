import type { DecisionRecord } from "@/lib/decision-types";

export const DEFAULT_APPROVAL_AUTHOR = "cfo@demo.test";
export const MAX_HUMAN_FIELD_LENGTH = 500;

export const MSG_REASON_REQUIRED = "Hace falta un motivo.";
export const MSG_AUTHOR_REQUIRED = "Hace falta un autor.";
export const MSG_FIELD_TOO_LONG = "Autor y motivo admiten hasta 500 caracteres.";
export const MSG_SERVER_422 =
  "El servidor no registró el evento. Revise autor y motivo e inténtelo de nuevo.";
export const MSG_NOT_FOUND = "No hay una decisión con ese identificador.";
export const MSG_NOT_ESCALATED =
  "Esta decisión ya no está en cola de aprobación (no es ESCALAR).";
export const MSG_UNEXPECTED_SUCCESS =
  "La respuesta del servidor no coincide con la decisión del agente; no se actualizó la tarjeta.";

export type HumanDecisionBody = {
  author: string;
  reason: string;
};

export function trimHumanField(value: string): string {
  return value.trim();
}

export type ValidatedHumanInput =
  | { ok: true; body: HumanDecisionBody }
  | { ok: false; message: string };

export function validateHumanDecisionInput(
  authorRaw: string,
  reasonRaw: string,
): ValidatedHumanInput {
  const author = trimHumanField(authorRaw);
  const reason = trimHumanField(reasonRaw);
  if (author.length === 0) {
    return { ok: false, message: MSG_AUTHOR_REQUIRED };
  }
  if (reason.length === 0) {
    return { ok: false, message: MSG_REASON_REQUIRED };
  }
  if (author.length > MAX_HUMAN_FIELD_LENGTH || reason.length > MAX_HUMAN_FIELD_LENGTH) {
    return { ok: false, message: MSG_FIELD_TOO_LONG };
  }
  return { ok: true, body: { author, reason } };
}

export function buildHumanDecisionBody(author: string, reason: string): HumanDecisionBody {
  const validated = validateHumanDecisionInput(author, reason);
  if (!validated.ok) {
    throw new Error(validated.message);
  }
  return validated.body;
}

export function isPendingEscalar(record: DecisionRecord): boolean {
  return record.decision === "ESCALAR" && record.human_events.length === 0;
}

export function partitionEscalarQueue(records: DecisionRecord[]): {
  pending: DecisionRecord[];
  withEvents: DecisionRecord[];
} {
  const pending: DecisionRecord[] = [];
  const withEvents: DecisionRecord[] = [];
  for (const record of records) {
    if (record.decision !== "ESCALAR") continue;
    if (record.human_events.length === 0) {
      pending.push(record);
    } else {
      withEvents.push(record);
    }
  }
  return { pending, withEvents };
}

export type HumanActionSuccess =
  | { ok: true; record: DecisionRecord }
  | { ok: false; message: string };

export function mergeHumanActionSuccess(
  previous: DecisionRecord,
  response: DecisionRecord,
): HumanActionSuccess {
  if (response.decision !== "ESCALAR" || response.severity !== 1) {
    return { ok: false, message: MSG_UNEXPECTED_SUCCESS };
  }
  if (previous.decision !== "ESCALAR" || previous.severity !== 1) {
    return { ok: false, message: MSG_UNEXPECTED_SUCCESS };
  }
  if (response.human_events.length !== previous.human_events.length + 1) {
    return { ok: false, message: MSG_UNEXPECTED_SUCCESS };
  }
  return { ok: true, record: response };
}

export function humanActionHttpErrorMessage(
  status: number,
  detail?: string | unknown,
): string {
  if (status === 422) {
    return MSG_SERVER_422;
  }
  if (status === 404 && detail === "not_found") {
    return MSG_NOT_FOUND;
  }
  if (status === 409 && detail === "not_escalated") {
    return MSG_NOT_ESCALATED;
  }
  if (status === 404) {
    return MSG_NOT_FOUND;
  }
  if (status === 409) {
    return MSG_NOT_ESCALATED;
  }
  return `No se pudo registrar el evento (HTTP ${status}).`;
}

export async function parseErrorDetail(res: Response): Promise<string | undefined> {
  try {
    const body = (await res.json()) as { detail?: string | unknown };
    if (typeof body.detail === "string") {
      return body.detail;
    }
    return undefined;
  } catch {
    return undefined;
  }
}
