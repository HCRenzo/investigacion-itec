# Módulo de ventas optimizado

Tienda en línea en Python que responde a la pregunta de investigación: **¿de qué manera la optimización de algoritmos y arquitectura de procesamiento en Python reduce el tiempo de generación del recibo?**

Para medirlo, el recibo se puede generar con dos motores intercambiables:

- **V1 (heredado):** ineficiente a propósito. Relee el catálogo de la base en cada búsqueda, escanea sin cortar y reconstruye el recibo varias veces. Se auto-calibra para tardar cerca de 25 s.
- **V2 (optimizado):** una sola consulta al catálogo y un recorrido lineal, O(n). Casi instantáneo.

Cada pedido guarda el motor usado y su tiempo, y el panel de administración los compara.

## Contenido

- [Funcionalidades](#funcionalidades)
- [Ejecutar localmente](#ejecutar-localmente)
- [Pruebas](#pruebas)
- [Variables de entorno](#variables-de-entorno)
- [Motores V1 y V2](#motores-v1-y-v2)
- [Base de datos](#base-de-datos)
- [Desplegar en Vercel](#desplegar-en-vercel)
- [Arquitectura](#arquitectura)
- [Documentación adicional](#documentación-adicional)

## Funcionalidades

- **Tienda** (`/`): registro e inicio de sesión (JWT, contraseñas con scrypt), catálogo con búsqueda y categorías, carrito y compra. El stock se descuenta de forma atómica: dos compradores no pueden llevarse la última unidad.
- **Mis pedidos:** historial de compras del usuario.
- **Panel de administración** (`/admin`): login propio y separado (las sesiones no se comparten y las cuentas admin no entran por la tienda). Incluye resumen de ventas, listado de ventas, inventario (alta y edición de productos) y configuración del motor.
- **API del experimento:** `POST /api/sales` (V2) y `POST /api/sales/slow` (V1) calculan una venta con catálogo en memoria, sin login, para medir los motores aislados.

Stack: Python 3.12, FastAPI, SQLAlchemy, PyJWT, frontend en HTML/CSS/JS, pytest, Vercel.

## Ejecutar localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn api.index:app --reload
```

Abre <http://127.0.0.1:8000>. La documentación interactiva de la API está en `/docs`.

Sin `DATABASE_URL` se usa SQLite local (`tienda.db`). Al arrancar se crean roles, parámetros, catálogo de ejemplo, el administrador (`admin@tienda.local` / `admin1234`) y un cliente de prueba (`cliente@prueba.com` / `cliente1234`).

Para levantar V1 y V2 a la vez y compararlas, ver [scripts/README.md](scripts/README.md).

## Pruebas

```bash
python -m pytest -q
```

Cubren la tienda, los motores y el endpoint serverless. Las pruebas de V1 usan `LEGACY_TARGET_SECONDS=0` y `LEGACY_WORK_FACTOR=1` para que sea rápida. La prueba de rendimiento carga 500 líneas y exige menos de 20 s: detecta regresiones del algoritmo, no es una prueba de carga HTTP.

Contra Postgres real: `TEST_DATABASE_URL=postgresql://... python -m pytest -q` (con la migración ya aplicada en esa base).

## Variables de entorno

Plantilla en [.env.example](.env.example). El archivo `.env` no se sube a git.

| Variable | Uso | Por defecto |
|---|---|---|
| `DATABASE_URL` | Conexión a Postgres (Supabase, pooler puerto 6543) | SQLite local |
| `SECRET_KEY` | Firma de sesiones (**cambiar en producción**) | clave de desarrollo |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Administrador inicial | `admin@tienda.local` / `admin1234` |
| `SEED_DEMO_CUSTOMER` | `0` evita crear el cliente de prueba | `1` |
| `RECEIPT_ENGINE` | `v1` o `v2`. Solo aplica si el panel está en *Automático* | `v2` |
| `LEGACY_TARGET_SECONDS` | Tiempo objetivo de V1 (auto-calibrado). `0` = usar `LEGACY_WORK_FACTOR` | `25` |
| `LEGACY_WORK_FACTOR` | Trabajo inútil de V1, solo si `LEGACY_TARGET_SECONDS=0` | `550` |

## Motores V1 y V2

El cliente no ve ni elige el motor. Prioridad de selección: **panel `/admin` → Configuración (V1/V2) → variable `RECEIPT_ENGINE` → V2**. Con el panel en *Automático* manda la variable, lo que permite tener dos despliegues con motores distintos sobre la misma base.

Código: [legacy.py](api/services/receipt/legacy.py) (V1), [fast.py](api/services/receipt/fast.py) (V2). Detalles, scripts y validación automática en [scripts/README.md](scripts/README.md).

## Base de datos

Nueve tablas con prefijo `t_`, todas con `id`, `uuid` y columnas de auditoría. Referencia en [docs/PLAN_BASE_DE_DATOS.md](docs/PLAN_BASE_DE_DATOS.md).

1. **Crear el esquema** (una vez): en Supabase → *SQL Editor*, ejecutar [0001_esquema.sql](supabase/migrations/0001_esquema.sql) y luego [0002_motor_recibo_auto.sql](supabase/migrations/0002_motor_recibo_auto.sql). Son repetibles sin riesgo.
2. **Conectar la app:** en Supabase → *Project Settings → Database → Connection string → Transaction pooler* (puerto 6543) y ponerla como `DATABASE_URL` en `.env` y en las variables de Vercel.
3. Al arrancar, la app crea lo que falte (roles, parámetros, catálogo de ejemplo, administrador, cliente de prueba). Opcionalmente, `python3 scripts/generate_seed_sql.py` genera un SQL equivalente para pegar en Supabase.

Notas:
- La API pública de Supabase **no se usa**: las tablas tienen RLS activado sin políticas y solo el backend entra, por `DATABASE_URL`.
- El navegador ve `uuid`, no ids numéricos.
- `created_by`/`updated_by` y `t_auditoria` se llenan solos; los borrados son lógicos (`deleted_at`).
- Cada venta descuenta stock de forma atómica y deja un movimiento en `t_movimiento_inventario`.

## Desplegar en Vercel

Requisitos para que el login funcione:

- Definir `DATABASE_URL` con una base Postgres. Sin ella, Vercel usa SQLite en `/tmp`: cada instancia tiene su propia copia temporal y los usuarios se pierden al reiniciar.
- Definir `SECRET_KEY` (largo y aleatorio) y `ADMIN_PASSWORD`. Usar `SEED_DEMO_CUSTOMER=0` en producción.
- Las tablas y cuentas iniciales se crean en la primera petición de cada instancia.

Pasos:

1. `npm i -g vercel`
2. Desde la raíz: `vercel` (primer despliegue) y `vercel --prod` (producción). También se puede importar el repositorio desde el dashboard de Vercel.

[vercel.json](vercel.json) enruta todo a la aplicación ASGI de `api/index.py`. Para tener V1 y V2 a la vez en dos proyectos de Vercel, y el aviso sobre el límite de tiempo de las funciones (V1 tarda ~25 s), ver [docs/DESPLIEGUE_V1_V2.md](docs/DESPLIEGUE_V1_V2.md).

## Arquitectura

MVC orientado a objetos:

```
api/
  index.py           Punto de entrada ASGI (Vercel y uvicorn)
  models/         M  Entidades sobre las tablas t_*
  repositories/      Acceso a datos (usuarios, productos, pedidos)
  services/          Lógica de negocio: auth, catálogo, compra, reportes, configuración
    receipt/         Motores de recibo (Strategy + Template Method + Factory)
  controllers/    C  Rutas HTTP delgadas: auth, shop, admin, research, pages
  views/          V  Presentadores JSON y esquemas de entrada
  container.py       Inyección de dependencias por petición
  errors.py          Errores de dominio, convertidos a HTTP en un solo lugar
static/              Interfaz web (tienda y panel)
supabase/migrations/ Esquema SQL
scripts/             Levantar y validar V1/V2
tests/               Pruebas con pytest
```

**Por qué V2 es más rápida.** Con $n$ líneas y $p$ productos, buscar cada producto recorriendo el catálogo cuesta $O(n \times p)$; con un índice por clave la búsqueda es $O(1)$ promedio y el cálculo completo queda en $O(n)$. Además se usa `Decimal` para dinero, no se llama a servicios externos durante la transacción y el recibo se calcula y serializa una sola vez. En producción conviene medir también la latencia real, incluidos los cold starts.

## Documentación adicional

| Documento | Contenido |
|---|---|
| [scripts/README.md](scripts/README.md) | Diferencias V1/V2, scripts para levantar ambas y validación automática |
| [docs/DESPLIEGUE_V1_V2.md](docs/DESPLIEGUE_V1_V2.md) | Elegir motor desde el panel y desplegar V1 y V2 en Vercel |
| [docs/PLAN_BASE_DE_DATOS.md](docs/PLAN_BASE_DE_DATOS.md) | Diseño del esquema de base de datos |
