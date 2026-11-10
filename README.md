# Modulo de ventas optimizado

Implementacion en Python de un modulo de ventas para responder a la pregunta: **¿De qué manera la optimización de algoritmos y arquitectura de procesamiento en Python reduce el tiempo de generación del recibo?** El sistema reemplaza búsquedas repetitivas sobre una lista por consultas directas sobre un índice y calcula la venta en una sola pasada.

## Tienda, cuentas y panel de ventas

La aplicación ahora incluye:

- **Registro e inicio de sesión** (JWT, contraseñas con scrypt).
- **Tienda**: catálogo con búsqueda y categorías, carrito y compra en línea. El stock se descuenta de forma atómica, así que dos compradores no pueden llevarse la última unidad a la vez.
- **Mis pedidos**: historial de compras del usuario.
- **Panel de administración** separado en `/admin`, con su propio login (la tienda de clientes está en `/`; las sesiones no se comparten y las cuentas admin no pueden entrar por la tienda). Rol `admin`: resumen de ventas, listado de todas las ventas e inventario (alta y edición de productos).

Los endpoints `/api/sales` y `/api/sales/slow` del experimento de investigación se conservan: ahora usan los mismos motores de recibo que la tienda (rápido y heredado), sin `sleep`.

### Arquitectura (MVC orientado a objetos)

```
api/
  models/         M  Entidades sobre las tablas t_*: User, Role, Product, Category, Order, OrderItem...
  repositories/      Acceso a datos (UserRepository, ProductRepository, OrderRepository)
  services/          Lógica de negocio: AuthService, CatalogService, CheckoutService, ReportService
    receipt/         Motores de recibo intercambiables (patrón Strategy + Template Method + Factory)
  controllers/    C  Rutas HTTP delgadas: auth, shop, admin, research, pages
  views/          V  Presentadores JSON (qué ve cada audiencia) y esquemas de entrada
  container.py       Inyección de dependencias por petición
  errors.py          Errores de dominio, convertidos a HTTP en un solo lugar
static/              Interfaz web (tienda en / y panel en /admin)
```

### Motores de recibo V1 / V2 (interno)

El cliente no elige versión: se define en el servidor con `RECEIPT_ENGINE`.

- **v2** (por defecto): una sola consulta al catálogo y un recorrido lineal. Casi instantáneo.
- **v1**: código heredado ineficiente a propósito, sin `sleep`. Relee el catálogo de la base de datos en cada búsqueda, escanea sin cortar, revalida y copia todo repetidamente y reconstruye el recibo varias veces. Con `LEGACY_WORK_FACTOR=6000` un pedido de 3 líneas tarda ~30 s en esta máquina; el tiempo depende del hardware, ajustar el factor para calibrarlo.

Documentación detallada, scripts para levantar ambas versiones y validación automática: [scripts/README.md](scripts/README.md).

Cada pedido guarda el motor usado y su tiempo; el panel `/admin` los muestra (Ventas y Resumen) para comparar V1 contra V2.


### Base de datos (Supabase / PostgreSQL)

El esquema son 9 tablas con prefijo `t_` (`t_rol`, `t_usuario`, `t_categoria`, `t_producto`, `t_pedido`, `t_pedido_detalle`, `t_movimiento_inventario`, `t_auditoria`, `t_parametro`). Todas llevan `id`, `uuid` y auditoría (`created_at/by`, `updated_at/by`, `deleted_at/by`). Diseño completo en [docs/PLAN_BASE_DE_DATOS.md](docs/PLAN_BASE_DE_DATOS.md).

1. **Crear las tablas** (una sola vez): en Supabase → *SQL Editor* ejecutar [supabase/migrations/0001_esquema.sql](supabase/migrations/0001_esquema.sql). Es repetible sin riesgo.
2. **Conectar la app**: en Supabase → *Project Settings → Database → Connection string → Transaction pooler* (puerto 6543) y ponerla en `.env` como `DATABASE_URL=postgresql://postgres.<ref>:<PASSWORD>@aws-0-<region>.pooler.supabase.com:6543/postgres`. En Vercel, la misma variable en *Environment Variables*. Ver [.env.example](.env.example).
3. Al arrancar, la app crea (si faltan) roles, parámetros, el catálogo de ejemplo, el administrador y el cliente de prueba.

Notas:
- La API pública de Supabase (`SUPABASE_KEY`) **no se usa**: las tablas tienen RLS activado sin políticas, solo el backend entra por `DATABASE_URL`.
- Los identificadores que ve el navegador son `uuid`, no números.
- `created_by` / `updated_by` y la tabla `t_auditoria` se llenan solos con el usuario autenticado. Los borrados son lógicos (`deleted_at`).
- Cada venta descuenta stock de forma atómica y deja un movimiento en `t_movimiento_inventario`.
- `t_parametro` guarda `TASA_IVA` y `MOTOR_RECIBO`. Si defines `RECEIPT_ENGINE` en el entorno, esa variable manda sobre la tabla (así se pueden levantar V1 y V2 a la vez sobre la misma base).
- Sin `DATABASE_URL` se usa SQLite local (`tienda.db`), útil para desarrollo y pruebas.
- Pruebas contra Postgres real: `TEST_DATABASE_URL=postgresql://... python -m pytest -q` (con la migración aplicada en esa base).

### Variables de entorno

| Variable | Uso | Por defecto |
|---|---|---|
| `DATABASE_URL` | Conexión a Postgres (Supabase, pooler 6543) | SQLite local |
| `SECRET_KEY` | Firma de sesiones (**cambiar en producción**) | clave de desarrollo |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Administrador inicial | `admin@tienda.local` / `admin1234` |
| `RECEIPT_ENGINE` | Motor de recibo: `v1` (lento) o `v2` (rápido). Si no se define, se lee `t_parametro.MOTOR_RECIBO` | `v2` |
| `LEGACY_WORK_FACTOR` | Cuánto trabajo inútil hace v1 | `6000` |

## Tecnologias

- Python 3.12 y FastAPI, SQLAlchemy, PyJWT
- Frontend HTML, CSS y JavaScript
- pytest para pruebas funcionales y de rendimiento
- Vercel Python Runtime

## Ejecutar localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn api.index:app --reload
```

Abrir `http://127.0.0.1:8000`. La documentación interactiva estará en `/docs`.

## Pruebas

```bash
python -m pytest -q
```

La prueba carga 500 líneas de venta y exige menos de 20 segundos de procesamiento. No es una prueba de carga HTTP completa; su objetivo es detectar regresiones del algoritmo de cálculo.

## Arquitectura de optimizacion

El problema de referencia tarda unos 3 minutos porque cada línea puede buscar su producto recorriendo la colección completa. Con $n$ líneas y $p$ productos, esa estrategia puede aproximarse a $O(n \times p)$, mientras que el índice de productos de esta implementación ofrece búsqueda promedio $O(1)$. El cálculo completo queda en $O(n)$.

Se evitan servicios externos durante la transacción, las operaciones monetarias usan `Decimal`, y se calcula y serializa el recibo una sola vez. Los resultados deberían medirse también con monitoreo de latencia en producción, incluyendo cold starts.

## Desplegar en Vercel

**Importante para que el login funcione:**

- Las tablas, el administrador y el cliente de prueba se crean en la primera petición de cada instancia (no dependen del arranque del servidor).
- Sin `DATABASE_URL`, Vercel usa SQLite en `/tmp`: **cada instancia tiene su propia copia temporal** y los usuarios registrados se pierden al reiniciarse o al cambiar de instancia. Para uso real define `DATABASE_URL` con una base Postgres (Neon, Supabase, Vercel Postgres…) en *Settings → Environment Variables*.
- Define también `SECRET_KEY` (valor largo y aleatorio), `ADMIN_PASSWORD`, y `SEED_DEMO_CUSTOMER=0` para no crear el cliente de prueba `cliente@prueba.com` en producción.
- Para probar V1 en Vercel: `RECEIPT_ENGINE=v1` (el límite de tiempo de las funciones puede cortar recibos de ~30 s).


1. Instalar Vercel CLI: `npm i -g vercel`.
2. Desde la raiz del proyecto ejecutar `vercel`.
3. En el primer despliegue, aceptar la vinculacion del directorio actual.
4. Para producción ejecutar `vercel --prod`.

Alternativamente, importar el repositorio desde el dashboard de Vercel como proyecto existente. El archivo `vercel.json` enruta la aplicación ASGI de `api/index.py`.