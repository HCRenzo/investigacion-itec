# Versiones V1 y V2 del recibo: documentación y validación

La tienda genera el recibo con uno de dos **motores** intercambiables. El cliente no elige ni ve cuál se usa: se define en el servidor con la variable `RECEIPT_ENGINE`.

| | **V1 · heredada** | **V2 · optimizada** |
|---|---|---|
| Propósito | Reproduce el problema original: recibo muy lento | Solución propuesta por la investigación |
| Código | [`api/services/receipt/legacy.py`](../api/services/receipt/legacy.py) | [`api/services/receipt/fast.py`](../api/services/receipt/fast.py) |
| Clase | `LegacyReceiptEngine` | `FastReceiptEngine` |
| Activación | `RECEIPT_ENGINE=v1` | `RECEIPT_ENGINE=v2` (por defecto) |
| Puerto (scripts) | **8011** | **8010** |
| Tiempo (pedido de 3 líneas) | ~25 s (objetivo configurable) | ~0.001 s |
| Complejidad | Crece con líneas × productos × `LEGACY_WORK_FACTOR` (cuadrática en líneas) | O(n) lineal |

Ambos motores heredan de `ReceiptEngine` ([`base.py`](../api/services/receipt/base.py)), que suma subtotal, IVA (21 %) y total y mide el tiempo. Solo cambia **cómo se calculan las líneas**. Una fábrica ([`factory.py`](../api/services/receipt/factory.py)) elige el motor y [`checkout_service.py`](../api/services/checkout_service.py) lo usa al comprar.

## Qué hace cada versión

### V1 (heredada, ineficiente a propósito)
No usa `sleep`: el tiempo viene de trabajo real innecesario. No copiar estos patrones.
- Audita el catálogo completo `LEGACY_WORK_FACTOR × 25` veces (copias profundas, comparaciones de todos contra todos).
- Valida cantidad y producto de cada línea 50 veces por pasada.
- Busca cada producto leyendo el catálogo **de la base de datos** (una consulta nueva por búsqueda) y sin cortar al encontrarlo.
- Cada línea nueva revisa de nuevo todas las anteriores.
- Reconstruye el recibo completo varias veces y exige que coincida.

V1 **se calibra sola**: en cada compra ejecuta una pasada pequeña, mide cuánto tarda en ese entorno (CPU y latencia de la base de datos) y dimensiona el trabajo para tardar cerca de `LEGACY_TARGET_SECONDS` (25 s por defecto). Así el tiempo es parecido en tu equipo y en Vercel. Con `LEGACY_TARGET_SECONDS=0` se usa un `LEGACY_WORK_FACTOR` fijo. Mientras V1 trabaja consume CPU y puede ralentizar a otros usuarios del mismo proceso.

### V2 (optimizada)
- **Una** consulta al catálogo para todas las líneas (índice por clave).
- Un único recorrido lineal con acceso directo, aritmética con `Decimal`.

## Scripts

Requieren el entorno virtual (`.venv`) con las dependencias instaladas.

| Script | Qué hace |
|---|---|
| `scripts/start_all.sh` | Levanta V2 (:8010) y V1 (:8011) a la vez, con la misma base de datos |
| `scripts/start_v1.sh` / `scripts/start_v2.sh` | Levanta solo una versión |
| `scripts/stop_all.sh` | Detiene las dos |
| `scripts/validate.py` | Valida que V1 y V2 coinciden y que V2 es más rápida |

Cambiar puertos: `V1_PORT=9001 V2_PORT=9000 scripts/start_all.sh`. Los registros quedan en `scripts/.run/v1.log` y `v2.log`.

## Validar

```bash
scripts/start_all.sh
.venv/bin/python scripts/validate.py      # tarda ~30 s por la compra en V1
scripts/stop_all.sh
```

`validate.py` entra como el cliente de prueba, envía **el mismo carrito** a ambas versiones y comprueba (19 verificaciones):

1. Ambos servidores responden.
2. El login del cliente funciona.
3. La compra se crea en las dos.
4. Subtotal, IVA, total, unidades y líneas del recibo son **idénticos** entre V1 y V2.
5. La respuesta al cliente **no revela** el motor.
6. El panel de administración sí registra el motor de cada pedido (`v1` / `v2`).
7. V1 tarda más de 5 s, V2 menos de 1 s, y V2 es al menos 100 veces más rápida.

Termina con `VALIDACION CORRECTA` (código de salida 0) o lista lo que falló (código 1). Cada ejecución crea 2 pedidos reales y consume unas unidades de stock.

Resultado de referencia (ejecución de ejemplo): V1 **30.03 s**, V2 **0.0010 s**, 19/19 comprobaciones correctas.

## Validación manual en el navegador

- Tienda V2: <http://127.0.0.1:8010> — Tienda V1: <http://127.0.0.1:8011> (el login ya viene con el cliente de prueba `cliente@prueba.com` / `cliente1234`).
- Compra en cada una y compara cuánto tarda el recibo.
- Panel `http://127.0.0.1:8010/admin` (`admin@tienda.local` / `admin1234`): en **Ventas** ves el motor y el tiempo de cada pedido; en **Resumen**, el tiempo promedio por motor.

## Pruebas automáticas

`python -m pytest -q` ejecuta pruebas de los motores con `LEGACY_TARGET_SECONDS=0` y `LEGACY_WORK_FACTOR=1` (para que V1 sea rápida en las pruebas) y verifica que ambos dan el mismo resultado.

## Endpoints del experimento original

`POST /api/sales` (motor V2) y `POST /api/sales/slow` (motor V1) calculan una venta con catálogo en memoria, sin necesidad de login. Sirven para medir los motores aislados de la tienda.
