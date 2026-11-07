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
  models/         M  Entidades: User, Product, Order, OrderItem
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


### Base de datos

Se usa SQLAlchemy. Variable `DATABASE_URL`:

- Sin definir: SQLite local (`tienda.db`). **En Vercel este archivo no persiste**, así que allí hay que definir `DATABASE_URL`.
- Para conectar la base del cliente: `postgresql://usuario:clave@host:5432/base` (también MySQL si se instala su driver). Las tablas (`users`, `products`, `orders`, `order_items`) se crean al arrancar; si el cliente ya tiene un esquema propio, hay que ajustar los modelos en `api/database.py`.

### Variables de entorno

| Variable | Uso | Por defecto |
|---|---|---|
| `DATABASE_URL` | Base de datos | SQLite local |
| `SECRET_KEY` | Firma de sesiones (**cambiar en producción**) | clave de desarrollo |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Administrador inicial | `admin@tienda.local` / `admin1234` |
| `RECEIPT_ENGINE` | Motor de recibo: `v1` (lento) o `v2` (rápido) | `v2` |
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

1. Instalar Vercel CLI: `npm i -g vercel`.
2. Desde la raiz del proyecto ejecutar `vercel`.
3. En el primer despliegue, aceptar la vinculacion del directorio actual.
4. Para producción ejecutar `vercel --prod`.

Alternativamente, importar el repositorio desde el dashboard de Vercel como proyecto existente. El archivo `vercel.json` enruta la aplicación ASGI de `api/index.py`.



