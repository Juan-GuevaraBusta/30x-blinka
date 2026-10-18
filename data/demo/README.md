# Paquete de demo (3 casos)

Empresa: **P.J Gorman** (USD), con acuerdo mensual fijo de **Globex LLC** (1200 USD) y acuerdo por horas de **Andesbyte SAS** (45 USD/hora, 160 h incluidas, recargo 1,5×).

| Archivo | Qué muestra | Resultado esperado |
|---|---|---|
| `01-globex-mensualidad-octubre.txt` | Factura que cuadra con el acuerdo | **PAGAR** |
| `02-globex-mensualidad-octubre-REENVIO.txt` | La misma factura otra vez (ya se pagó) | **FRENAR** (R05, duplicado) |
| `03-andesbyte-horas-octubre.txt` | Pago variable por horas | **ESCALAR** (R19: requiere aprobación humana) |
| `04-cuotasur-cuota-q4.txt` | Cuota Q4 (2500 USD) del plan de cuotas de Cuotasur, dentro de su ventana | **PAGAR** |
| `05-cuotasur-cuota-q4-REENVIO.txt` | La misma cuota otra vez | **FRENAR** (R05, duplicado) |

Los casos 04 y 05 sirven para una segunda demo sobre una cuenta que ya tiene 01 a 03: una factura nueva de Globex por el mismo monto dentro de 30 días escala como posible duplicado (R05), por eso el caso limpio de PAGAR es la cuota de Cuotasur. Probado en local el 2026-10-18: 04 → PAGAR (18 chequeos OK), 05 → FRENAR (R05).

Súbelos en orden desde `/subir` (canal chat). Antes de grabar: `backend/sql/reset_demo.sql` en Supabase, reiniciar Render y `backend/scripts/seed_demo.py --apply --with-rules --member-user-id <uuid> --member-email <correo>`.
