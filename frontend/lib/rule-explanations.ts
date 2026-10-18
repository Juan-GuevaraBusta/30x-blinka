/**
 * Plain-Spanish, one-sentence gloss for the rules added by T7.1/T7.2 (R14-R18,
 * D059), shown under a check's own `detail` in the decision detail screen.
 * The backend already writes `detail` in plain Spanish (`RULE_NAMES`,
 * `backend/app/rules/checks.py`); this only adds a short "what this rule is
 * for" sentence for a non-technical reader, it never replaces that text.
 */
export const RULE_PLAIN_EXPLANATIONS: Partial<Record<string, string>> = {
  R14: "Aplica la política de aprobación propia de la empresa: puede exigir más firmas, nunca menos.",
  R15: "Confirma que el pago cae dentro del calendario pactado con el proveedor (fecha y monto esperados).",
  R16: "Evita pagar dos veces el mismo periodo de una serie, aunque llegue con otro número de factura.",
  R17: "Vigila que la suma de pagos de la serie no supere el tope total pactado con el proveedor.",
  R18: "Solo informa: avisa si quedó algún periodo anterior de la serie sin su factura, sin frenar este pago.",
};

export function rulePlainExplanation(rule: string): string | null {
  return RULE_PLAIN_EXPLANATIONS[rule] ?? null;
}
