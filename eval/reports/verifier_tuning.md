# Ajuste del verificador: menos «violations» falsas (solo dev)

**Fecha:** 2026-10-18. **Alcance:** `data/invoices/dev` (34) y `data/golden/dev.json`. El holdout no se usó.

## Problema

En la corrida 4 de T5.2 (`t5_2_calibration.md`), el verificador marcó 11 «violations» en 10 facturas. Ninguna era una contradicción citable:

| Tipo | Facturas | Evidencia |
|---|---|---|
| `on_fail` nulo en R06 INDETERMINADO (`R06_ON_FAIL_*`) | dev-015, 016, 021, 023, 024, 025, 027, 032 | repite `CHECKS[R06].detail` y `on_fail = null` |
| Repite una regla ya INDETERMINADO | dev-012 (`R06`, evidencia «R06») | solo el id de la regla |
| Repite una regla ya FALLA | dev-031 (`R13`), dev-032 (`R13_EVIDENCE_MISSING`) | R13 ya detectó la inyección y escala |

Por el piso del verificador, 7 de esas facturas pasaron de ESCALAR a FRENAR sin motivo.

## Cambio (`backend/app/verifier/run.py`)

Ahora una `violation` pasa a `uncertainty` de forma determinista en cualquiera de estos casos:
1. no trae evidencia (regla que ya existía);
2. el código o la evidencia hablan de confirmación de contrato o de `on_fail`;
3. todos los ids de regla del código son reglas cuyo chequeo ya salió INDETERMINADO o FALLA;
4. la evidencia no trae una cita literal del SOURCE de al menos 6 caracteres. La comparación ignora mayúsculas y espacios.

El prompt ahora pide una cita literal entre comillas y nombra los estados conocidos que no son violaciones. I4 se mantiene: `uncertainty` sigue llevando la decisión a ESCALAR como mínimo, nunca a PAGAR. Los tests están en `backend/tests/test_verifier.py`: una prueba por regla, una para la contradicción real de monto (sigue en FRENAR), una para la inyección no detectada con cita (sigue en FRENAR) y una de no-bajada.

## Resultado e2e en dev (mismo comando y modelos que la corrida 4)

| | Antes (corrida 4) | Después |
|---|---|---|
| Autonomía | 14/34 (41.2 %) | **19/34 (55.9 %)** |
| `unsafe_pay` | 0 | **0** |
| «violations» del verificador | 11 | 0 |

Matriz después (filas = esperado, columnas = obtenido: PAGAR / ESCALAR / FRENAR): PAGAR 0/11/0 · ESCALAR 0/16/0 · FRENAR 0/4/3.

Cambiaron 8 facturas, todas de FRENAR a ESCALAR: dev-012, 021, 023, 024, 025, 027, 031 y 032. dev-027 (se esperaba FRENAR por R07) antes daba FRENAR solo gracias a la violation falsa de R06. Ahora sale ESCALAR, porque R07 no falla. Es un hueco de R07, no del verificador. dev-023, 031 y 032 salieron por `error_tecnico`: hay un `schema_mismatch` intermitente en `lookup_contract` antes de llegar al verificador (ya anotado en T5.2 §7). Al repetir dev-023 aisladamente salió ESCALAR por R02/R04.

El holdout no se usó.
