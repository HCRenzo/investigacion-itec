# Modulo de ventas optimizado

Implementacion en Python de un modulo de ventas para responder a la pregunta: **¿De qué manera la optimización de algoritmos y arquitectura de procesamiento en Python reduce el tiempo de generación del recibo?** El sistema reemplaza búsquedas repetitivas sobre una lista por consultas directas sobre un índice y calcula la venta en una sola pasada.

## Tecnologias

- Python 3.12 y FastAPI
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
