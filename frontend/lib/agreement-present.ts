import type { VendorAgreement } from "@/lib/agreement-types";

const PERIODICITY_LABELS: Record<string, string> = {
  monthly: "Mensual",
  biweekly: "Quincenal",
  quarterly: "Trimestral",
};

/**
 * es-style grouping (dot thousands, comma decimals) without depending on the
 * runtime's ICU locale data -- Node's default "small-icu" build has no "es"
 * data and silently falls back to no grouping at all (`Intl.NumberFormat`
 * would print "9600" instead of "9.600"), which made this environment-
 * dependent in tests. A hand-rolled formatter keeps the output deterministic
 * everywhere, browser or Node.
 */
function formatEsNumber(amount: number): string {
  const rounded = Math.round(amount * 100) / 100;
  const [intPart, decPart] = Math.abs(rounded).toFixed(2).split(".");
  const grouped = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const sign = rounded < 0 ? "-" : "";
  return decPart === "00" ? `${sign}${grouped}` : `${sign}${grouped},${decPart}`;
}

function money(currency: string, amount: number): string {
  return `${currency} ${formatEsNumber(amount)}`;
}

function capSuffix(currency: string, cap: number | null | undefined): string {
  return cap != null ? `, tope ${money(currency, cap)}` : "";
}

/**
 * «Cómo lo aplica el agente» (T9.1, D061 §5): a plain-Spanish, one-line
 * summary of the compiled effect of a confirmed agreement, e.g. "Mensual,
 * USD 800, de 2026-01-01 a 2026-12-31, tope USD 9.600".
 */
export function describeAgreement(agreement: VendorAgreement): string {
  const { currency, valid_from: validFrom, valid_to: validTo } = agreement;
  const window = `de ${validFrom} a ${validTo ?? "sin fin"}`;

  if (agreement.kind === "retainer") {
    const { min, max } = agreement.amount;
    const amountLabel = min === max ? money(currency, min) : `${money(currency, min)} a ${money(currency, max)}`;
    const periodicity = PERIODICITY_LABELS[agreement.periodicity] ?? agreement.periodicity;
    return `${periodicity}, ${amountLabel}, ${window}${capSuffix(currency, agreement.total_cap)}`;
  }

  if (agreement.kind === "hourly") {
    const base = `Por hora, ${money(currency, agreement.rate)}`;
    const included =
      agreement.included_hours != null ? `, ${agreement.included_hours} h incluidas` : "";
    const overtime = agreement.overtime
      ? `, extras ×${agreement.overtime.multiplier}` +
        (agreement.overtime.max_hours != null ? ` hasta ${agreement.overtime.max_hours} h` : "")
      : "";
    return `${base}${included}${overtime}, ${window}${capSuffix(currency, agreement.period_cap)}`;
  }

  if (agreement.kind !== "unit_pricing") {
    // Only "installments" | "milestones" remains here.
    const label = agreement.kind === "installments" ? "Cuotas" : "Hitos";
    const amounts = agreement.items.map((item) => item.amount);
    const allEqual = amounts.every((amount) => amount === amounts[0]);
    const amountLabel = allEqual
      ? `${agreement.items.length} de ${money(currency, amounts[0])}`
      : amounts.map((amount) => money(currency, amount)).join(", ");
    return `${label}: ${amountLabel}, ${window}${capSuffix(currency, agreement.total_cap)}`;
  }

  const { formula } = agreement;
  const rateLabel =
    formula.kind === "unit_rate"
      ? `${money(currency, formula.rate)} por ${formula.unit}`
      : `tramos por ${formula.unit} (${formula.tiers
          .map((tier) =>
            tier.up_to != null
              ? `hasta ${tier.up_to}: ${money(currency, tier.rate)}`
              : `resto: ${money(currency, tier.rate)}`,
          )
          .join("; ")})`;
  return `${rateLabel}, ${window}${capSuffix(currency, agreement.period_cap)}`;
}
