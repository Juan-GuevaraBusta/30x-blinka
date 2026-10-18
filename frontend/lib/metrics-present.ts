export type MetricsSource = "none" | "report";

export type MetricsBody = {
  unsafe_pay: number | null;
  autonomy_pct: number | null;
  source: MetricsSource;
};

export type MetricsPresentation =
  | { kind: "error"; message: string }
  | { kind: "empty"; message: string }
  | {
      kind: "report";
      unsafe_pay: number;
      autonomy_pct: number;
      blocked: boolean;
      blockMessage: string;
    };

export const METRICS_EMPTY_MESSAGE =
  "No hay reporte de evaluación. Los pagos indebidos y la autonomía no están medidos en este momento.";

export const METRICS_FETCH_ERROR_MESSAGE =
  "No se pudo leer las métricas. Compruebe que el API esté en marcha e intente recargar la página.";

export const METRICS_INVALID_BODY_MESSAGE =
  "La respuesta del servidor no tiene el formato esperado. No se muestran cifras.";

export const METRICS_RATE_LIMIT_MESSAGE =
  "Demasiadas solicitudes en poco tiempo. Espere un momento y recargue la página.";

export const METRICS_BLOCK_MESSAGE =
  "Este conteo bloquea el despliegue según la regla I9. Esta pantalla solo muestra la lectura; no inicia ni detiene un despliegue.";

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

export function isMetricsBody(value: unknown): value is MetricsBody {
  if (value === null || typeof value !== "object") return false;
  const record = value as Record<string, unknown>;
  if (!("unsafe_pay" in record) || !("autonomy_pct" in record) || !("source" in record)) {
    return false;
  }
  const { unsafe_pay, autonomy_pct, source } = record;
  if (source !== "none" && source !== "report") return false;
  if (unsafe_pay !== null && !isFiniteNumber(unsafe_pay)) return false;
  if (autonomy_pct !== null && !isFiniteNumber(autonomy_pct)) return false;
  return true;
}

/** Classifies a parsed MetricsBody (§6 of T4.7). */
export function classifyMetricsBody(body: MetricsBody): MetricsPresentation {
  if (body.source === "none" || body.unsafe_pay === null || body.autonomy_pct === null) {
    return { kind: "empty", message: METRICS_EMPTY_MESSAGE };
  }
  if (body.source !== "report") {
    return { kind: "error", message: METRICS_INVALID_BODY_MESSAGE };
  }
  const blocked = body.unsafe_pay !== 0;
  return {
    kind: "report",
    unsafe_pay: body.unsafe_pay,
    autonomy_pct: body.autonomy_pct,
    blocked,
    blockMessage: METRICS_BLOCK_MESSAGE,
  };
}

export function presentMetricsFromResponse(status: number, body: unknown): MetricsPresentation {
  if (status === 429) {
    return { kind: "error", message: METRICS_RATE_LIMIT_MESSAGE };
  }
  if (status !== 200) {
    return {
      kind: "error",
      message: `${METRICS_FETCH_ERROR_MESSAGE} (HTTP ${status}).`,
    };
  }
  if (!isMetricsBody(body)) {
    return { kind: "error", message: METRICS_INVALID_BODY_MESSAGE };
  }
  return classifyMetricsBody(body);
}

/** Display string without rounding away fractional autonomy (e.g. 15.5). */
export function formatMetricNumber(value: number): string {
  if (Number.isInteger(value)) return String(value);
  return String(value);
}

// --- Live company metrics (GET /api/metrics/live) ---------------------------

export type LiveMetricsBody = {
  total: number;
  pagar: number;
  frenar: number;
  escalar: number;
  auto_decided_pct: number | null;
  pending_approvals: number;
  approved_by_humans: number;
};

export type LiveMetricsPresentation =
  | { kind: "error"; message: string }
  | { kind: "empty"; message: string }
  | { kind: "data"; metrics: LiveMetricsBody };

export const LIVE_METRICS_EMPTY_MESSAGE =
  "Todavía no hay decisiones registradas para tu empresa.";

export const LIVE_METRICS_FETCH_ERROR_MESSAGE =
  "No se pudieron leer las métricas en vivo. Compruebe que el API esté en marcha e intente recargar la página.";

export const LIVE_METRICS_INVALID_BODY_MESSAGE =
  "La respuesta del servidor no tiene el formato esperado para las métricas en vivo.";

export function isLiveMetricsBody(value: unknown): value is LiveMetricsBody {
  if (value === null || typeof value !== "object") return false;
  const r = value as Record<string, unknown>;
  const requiredInts = ["total", "pagar", "frenar", "escalar", "pending_approvals", "approved_by_humans"];
  if (!requiredInts.every((key) => isFiniteNumber(r[key]))) return false;
  if (!("auto_decided_pct" in r)) return false;
  if (r.auto_decided_pct !== null && !isFiniteNumber(r.auto_decided_pct)) return false;
  return true;
}

export function presentLiveMetricsFromResponse(
  status: number,
  body: unknown,
): LiveMetricsPresentation {
  if (status !== 200) {
    return { kind: "error", message: `${LIVE_METRICS_FETCH_ERROR_MESSAGE} (HTTP ${status}).` };
  }
  if (!isLiveMetricsBody(body)) {
    return { kind: "error", message: LIVE_METRICS_INVALID_BODY_MESSAGE };
  }
  if (body.total === 0) {
    return { kind: "empty", message: LIVE_METRICS_EMPTY_MESSAGE };
  }
  return { kind: "data", metrics: body };
}

// --- Versioned evaluation evidence (GET /api/metrics/evaluation) -----------

export type MetricsEvidenceEntry = {
  id: string;
  label: string;
  value: number | string;
  source: string;
};

export type MetricsEvaluationBody = {
  entries: MetricsEvidenceEntry[];
  generated_at: string | null;
  source: MetricsSource;
};

export type EvaluationPresentation =
  | { kind: "error"; message: string }
  | { kind: "empty"; message: string }
  | { kind: "data"; entries: MetricsEvidenceEntry[]; generated_at: string | null };

export const EVALUATION_EMPTY_MESSAGE =
  "No hay evidencia de evaluación versionada. Ejecute eval/build_metrics_summary.py para generar eval/reports/metrics_summary.json.";

export const EVALUATION_FETCH_ERROR_MESSAGE =
  "No se pudo leer la evidencia de evaluación. Compruebe que el API esté en marcha e intente recargar la página.";

export const EVALUATION_INVALID_BODY_MESSAGE =
  "La respuesta del servidor no tiene el formato esperado para la evidencia de evaluación.";

function isMetricsEvidenceEntry(value: unknown): value is MetricsEvidenceEntry {
  if (value === null || typeof value !== "object") return false;
  const r = value as Record<string, unknown>;
  if (typeof r.id !== "string" || typeof r.label !== "string" || typeof r.source !== "string") {
    return false;
  }
  return typeof r.value === "number" || typeof r.value === "string";
}

export function isMetricsEvaluationBody(value: unknown): value is MetricsEvaluationBody {
  if (value === null || typeof value !== "object") return false;
  const r = value as Record<string, unknown>;
  if (!Array.isArray(r.entries) || !r.entries.every(isMetricsEvidenceEntry)) return false;
  if (r.generated_at !== null && typeof r.generated_at !== "string") return false;
  return r.source === "none" || r.source === "report";
}

export function presentEvaluationFromResponse(
  status: number,
  body: unknown,
): EvaluationPresentation {
  if (status !== 200) {
    return { kind: "error", message: `${EVALUATION_FETCH_ERROR_MESSAGE} (HTTP ${status}).` };
  }
  if (!isMetricsEvaluationBody(body)) {
    return { kind: "error", message: EVALUATION_INVALID_BODY_MESSAGE };
  }
  if (body.entries.length === 0) {
    return { kind: "empty", message: EVALUATION_EMPTY_MESSAGE };
  }
  return { kind: "data", entries: body.entries, generated_at: body.generated_at };
}
