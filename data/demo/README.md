# Paquete de demo (3 casos)

Empresa: **Acme Demo Inc.** (USD), con acuerdo mensual fijo de **Globex LLC** (1200 USD) y acuerdo por horas de **Andesbyte SAS** (45 USD/hora, 160 h incluidas, recargo 1,5×).

| Archivo | Qué muestra | Resultado esperado |
|---|---|---|
| `01-globex-mensualidad-octubre.txt` | Factura que cuadra con el acuerdo | **PAGAR** |
| `02-globex-mensualidad-octubre-REENVIO.txt` | La misma factura otra vez (ya se pagó) | **FRENAR** (R05, duplicado) |
| `03-andesbyte-horas-octubre.txt` | Pago variable por horas | **ESCALAR** (R19: requiere aprobación humana) |

Súbelos en orden desde `/subir` (canal chat). Antes de grabar: `backend/sql/reset_demo.sql` en Supabase, reiniciar Render y `backend/scripts/seed_demo.py --apply --with-rules --member-user-id <uuid> --member-email <correo>`.
