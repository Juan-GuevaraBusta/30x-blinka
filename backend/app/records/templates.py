"""Literal explanation templates from docs/04 §6 (Spanish, no LLM)."""

from __future__ import annotations

# §6 — decision and rule failures
TEMPLATE_PAGAR = (
    "Pagada: cumple todas las reglas ({n} chequeos). Monto USD {monto_base}, vence {fecha}."
)
TEMPLATE_R01_FAIL = (
    "Frenada: {beneficiario} no está en la lista de beneficiarios permitidos (regla R01)."
)
TEMPLATE_R02_FAIL = (
    "Escalada: USD {monto_base} supera el límite por pago de USD {limite} (regla R02)."
)
TEMPLATE_R03_FAIL = (
    "Escalada: con este pago el acumulado del mes sería USD {acum}, "
    "sobre el límite de USD {limite} (regla R03)."
)
TEMPLATE_R04_FAIL = (
    "Escalada: USD {monto_base} llega al umbral de aprobación humana de USD {umbral} (regla R04)."
)
TEMPLATE_R05_EXACT_FAIL = (
    "Frenada: ya existe una factura {numero} de {beneficiario} "
    "registrada el {fecha} (regla R05)."
)
TEMPLATE_R05_PROBABLE_FAIL = (
    "Escalada: posible duplicado del mismo beneficiario, monto y moneda en 30 días (regla R05)."
)
TEMPLATE_R06_FAIL = (
    "Escalada: el contrato (cláusula {clausula}) fija {pactado}, "
    "pero la factura cobra {cobrado} (regla R06)."
)
TEMPLATE_R07_FAIL = (
    "Frenada: el presupuesto restante de {depto} es USD {saldo}, "
    "menor al monto USD {monto_base} (regla R07)."
)
TEMPLATE_TECHNICAL_ERROR = (
    "Escalada: no fue posible verificar la factura de forma confiable ({motivo}). "
    "Requiere revisión humana."
)
TEMPLATE_VERIFIER_VIOLATION = (
    "Frenada por el verificador: {issue}. Se notificó al administrador."
)
TEMPLATE_VERIFIER_UNCERTAINTY = (
    "Escalada: el verificador no pudo confirmar {issue}. Requiere revisión humana."
)
TEMPLATE_ADMIN_NOTICE = (
    "Se frenó la factura {id} de {beneficiario}: {motivo}. Evidencia: {cita_o_regla}."
)

# R08–R13 and indeterminate (ready for T3; cite rule in summary)
TEMPLATE_R08_FAIL = (
    "Escalada: el destinatario de la factura no coincide con la empresa configurada (regla R08)."
)
TEMPLATE_R09_FAIL = (
    "Escalada: la extracción no alcanza el umbral de confianza o faltan datos (regla R09)."
)
TEMPLATE_R10_FAIL = (
    "Escalada: la moneda no tiene tasa de cambio configurada (regla R10)."
)
TEMPLATE_R11_FAIL = (
    "Escalada: falta o no se lee la fecha de vencimiento (regla R11)."
)
TEMPLATE_R12_FAIL = "Frenada: el beneficiario tiene un bloqueo manual activo (regla R12)."
TEMPLATE_R13_FAIL = (
    "Escalada: el documento contiene instrucciones embebidas sospechosas (regla R13)."
)
TEMPLATE_RULE_INDETERMINATE = (
    "Escalada: no se pudo completar la verificación de {nombre} ({motivo}). (regla {rule})."
)

# T7.1 (D059) §3 — company approval policy (R14). Can only ADD approvals, never PAGAR.
TEMPLATE_R14_FAIL = (
    "Escalada: la política de la empresa (ruta {ruta}) exige {n} aprobaciones "
    "de {grupos} (regla R14)."
)

# T7.2 (D059) §3 — payment series per vendor (R15-R18). Only ADD severity, never PAGAR.
TEMPLATE_R15_FAIL = (
    "Escalada: la fecha de la factura ({fecha}) no cumple la serie pactada {serie} "
    "({ventana}) (regla R15)."
)
TEMPLATE_R16_FAIL = (
    "Frenada: el periodo {periodo} de la serie {serie} ya se pagó con la "
    "factura {numero} (regla R16)."
)
TEMPLATE_R17_FAIL = (
    "Frenada: la serie {serie} acumulada (USD {acumulado}) más este pago supera "
    "el tope de USD {tope} (regla R17)."
)
