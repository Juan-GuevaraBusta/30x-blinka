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
