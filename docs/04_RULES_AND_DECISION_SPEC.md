# 04 — Especificación de reglas, decisiones y registro

## 1. Estados de decisión y precedencia
| Decisión | Significado |
|---|---|
| `PAGAR` | Autorizado (simulado) sin intervención humana. Solo si **todas** las reglas pasan y las señales superan umbral |
| `ESCALAR` | Pendiente de aprobación humana |
| `FRENAR` | No procede por una regla dura; se informa y queda registrado |

Severidad: `PAGAR < ESCALAR < FRENAR`. **Gana la más severa** entre las reglas que fallan. Un resultado **indeterminado** cuenta como `ESCALAR`. El verificador solo puede mover hacia la derecha.

Estados posteriores de una factura: `recibida → extraída → decidida → (pendiente | frenada | pagada_simulada) → aprobada_humano | rechazada_humano`.
La aprobación humana es un **evento nuevo** con autor y motivo; nunca reescribe la decisión del agente.

## 2. Esquema de reglas (editable en la UI)
```json
{
  "company": {"name": "Acme Demo Inc.", "base_currency": "USD"},
  "limits": {
    "per_payment": 3000,
    "per_period": {"type": "calendar_month", "amount": 20000}
  },
  "human_approval_threshold": 3000,
  "allowed_beneficiaries": ["Globex LLC", "Initech SAS"],
  "department_budgets": {"Ingenieria": 8000, "Marketing": 5000},
  "approvers": {"Ingenieria": "finanzas@demo.test", "default": "cfo@demo.test"},
  "manual_blocks": [],
  "on_fail": {
    "R01": "FRENAR", "R02": "ESCALAR", "R03": "ESCALAR", "R04": "ESCALAR",
    "R05": "FRENAR", "R06": "ESCALAR", "R07": "FRENAR", "R08": "ESCALAR"
  },
  "jev_thresholds": {"J1": 0.9, "J2": 0.9, "J3": 0.85, "J4": 0.85, "J6": 0.85, "J7": 0.5}
}
```
- Se valida con JSON Schema/Pydantic. Una regla mal formada **no se guarda**.
- Los `on_fail` por defecto son una decisión de producto abierta (ver `08`). Son configurables.

## 3. Catálogo de reglas
| Código | Regla | Entrada | Falla si… | Default |
|---|---|---|---|---|
| R01 | Beneficiario permitido | beneficiario normalizado | no está en la lista | FRENAR |
| R02 | Límite por pago | monto en moneda base | monto > límite | ESCALAR |
| R03 | Límite por periodo | monto + ledger del periodo | acumulado + monto > límite | ESCALAR |
| R04 | Aprobación humana por monto | monto en moneda base | monto ≥ umbral | ESCALAR |
| R05 | Duplicado | beneficiario + nº factura (+ monto/fecha) | exacto → ya existe; probable → misma combinación con nº distinto en ventana | exacto FRENAR / probable ESCALAR |
| R06 | Cuadra con lo acordado | términos del contrato confirmados | tarifa/monto/moneda fuera de lo pactado, o contrato ausente/no confirmado | ESCALAR |
| R07 | Presupuesto del departamento | depto + ledger | saldo restante < monto | FRENAR |
| R08 | Destinatario es la empresa | nombre en factura vs configurado | no coincide | ESCALAR |
| R09 | Extracción fiable | señales JEV J1–J4 | prob < umbral o campo obligatorio ausente | ESCALAR |
| R10 | Moneda convertible | `fx.json` | moneda sin tasa | ESCALAR |
| R11 | Fecha de pago definida | vencimiento | ausente o ilegible | ESCALAR |
| R12 | Bloqueo manual | `manual_blocks` | beneficiario bloqueado | FRENAR |
| R13 | Sin instrucciones embebidas | J7 + heurística | el documento intenta dar órdenes al sistema | ESCALAR |

R12 y R13 son el recorte de v1 para "compromisos bancarios / pendientes de stakeholders" y para inyección. Fuera de v1: validación de identidad, fraude, cumplimiento.

## 4. Semántica de datos
- **Normalización de beneficiario:** minúsculas, sin acentos/puntuación, sin sufijos societarios comunes; coincidencia exacta tras normalizar (sin fuzzy salvo para "probable duplicado").
- **Conversión:** monto original + moneda + tasa usada + fecha de tasa, desde `data/fx.json` (tabla fija, reproducible). Se registran ambos valores.
- **Periodo:** mes calendario. El ledger suma decisiones `PAGAR` y aprobaciones humanas; las pendientes **no** reservan saldo en v1 (documentado).
- **Orden de proceso:** por fecha de recepción, desempate por ID.
- **Duplicado exacto:** mismo beneficiario normalizado + mismo número de factura. **Probable:** mismo beneficiario + mismo monto y moneda + fecha dentro de 30 días + número distinto.
- **Fecha de pago:** se programa en la fecha de vencimiento; si falta, R11.

## 5. Registro de decisión (`DecisionRecord`)
```json
{
  "id": "dec_0042",
  "invoice_id": "INV-0042",
  "received_at": "2026-03-04T10:15:00Z",
  "decision": "ESCALAR",
  "severity": 1,
  "summary": "Requiere aprobación humana: el monto supera el límite por pago.",
  "extracted": {
    "beneficiary": "Globex LLC",
    "amount": 4200.0, "currency": "USD", "amount_base": 4200.0,
    "fx": {"rate": 1.0, "date": "2026-03-01"},
    "due_date": "2026-03-20", "invoice_number": "GX-2231", "recipient": "Acme Demo Inc.",
    "source_spans": {"amount": "Total a pagar: USD 4.200,00"}
  },
  "checks": [
    {"rule": "R01", "name": "Beneficiario permitido", "result": "OK", "detail": "Globex LLC está en la lista."},
    {"rule": "R02", "name": "Límite por pago", "result": "FALLA", "detail": "USD 4.200 supera el límite de USD 3.000.", "on_fail": "ESCALAR"},
    {"rule": "R06", "name": "Cuadra con contrato", "result": "OK", "detail": "Tarifa pactada USD 4.200", "evidence": {"clause": "4.2", "quote": "..."}}
  ],
  "jev_signals": [{"id": "J2", "answer": true, "probability": 0.97}],
  "verifier": {"consistent": true, "issues": []},
  "next_step": "Pendiente de aprobación de finanzas@demo.test.",
  "trace": {"langsmith_run_id": "...", "url": "..."},
  "versions": {"rules_version": "v3", "model_extractor": "...", "model_verifier": "...", "jev": "jev-1.13.0"},
  "human_events": []
}
```
Reglas del registro:
- Es **inmutable**; los eventos humanos se agregan a `human_events`.
- Guarda la versión de reglas y de modelos usada (reproducibilidad).
- La `summary` y los `detail` salen de **plantillas**, no de texto libre del LLM.

## 6. Plantillas de explicación (español)
| Caso | Plantilla |
|---|---|
| PAGAR | "Pagada: cumple todas las reglas ({n} chequeos). Monto USD {monto_base}, vence {fecha}." |
| R01 falla | "Frenada: {beneficiario} no está en la lista de beneficiarios permitidos (regla R01)." |
| R02 falla | "Escalada: USD {monto_base} supera el límite por pago de USD {limite} (regla R02)." |
| R03 falla | "Escalada: con este pago el acumulado del mes sería USD {acum}, sobre el límite de USD {limite} (regla R03)." |
| R05 exacto | "Frenada: ya existe una factura {numero} de {beneficiario} registrada el {fecha} (regla R05)." |
| R06 falla | "Escalada: el contrato (cláusula {clausula}) fija {pactado}, pero la factura cobra {cobrado} (regla R06)." |
| R07 falla | "Frenada: el presupuesto restante de {depto} es USD {saldo}, menor al monto USD {monto_base} (regla R07)." |
| Error técnico | "Escalada: no fue posible verificar la factura de forma confiable ({motivo}). Requiere revisión humana." |
| Verificador | "Escalada por el verificador: {issue}." |
Una persona no técnica debe entender cada plantilla sin glosario.

## 7. Invariant checker (gate final, en código)
Antes de entregar la decisión final:
- si `decision == PAGAR`: todo chequeo `OK`, ningún `indeterminado`, señales ≥ umbral, `verifier.consistent`, registro completo;
- la decisión final nunca es menos severa que la propuesta;
- la explicación referencia al menos una regla por cada chequeo no-OK.
Si algo falla → `ESCALAR` con motivo `invariante_violado` y alerta en el registro.
