# Separar V1 y V2 en Vercel (misma base de Supabase)

El motor del recibo lo decide la variable de entorno `RECEIPT_ENGINE` de **cada despliegue**. Para probar las dos versiones a la vez en Vercel hay que tener **dos proyectos de Vercel apuntando al mismo repositorio**. Ambos usan la misma base de Supabase, así que comparten usuarios, productos y stock, y todos los pedidos (con su motor y su tiempo) aparecen juntos en el panel `/admin`.

| | Proyecto V2 | Proyecto V1 |
|---|---|---|
| Nombre sugerido | `tienda-itec-v2` | `tienda-itec-v1` |
| `RECEIPT_ENGINE` | `v2` | `v1` |
| Recibo | casi instantáneo | lento a propósito (~20-30 s) |
| Repositorio / rama | el mismo (`main`) | el mismo (`main`) |

## Variables de entorno

Idénticas en los dos proyectos, **salvo** `RECEIPT_ENGINE` (y opcionalmente `LEGACY_WORK_FACTOR`, solo en V1).

| Variable | Valor | Notas |
|---|---|---|
| `DATABASE_URL` | cadena del *Transaction pooler* de Supabase (puerto 6543) | La misma en ambos |
| `SECRET_KEY` | texto largo aleatorio | **La misma en ambos** (si no, una sesión de uno no vale en el otro) |
| `RECEIPT_ENGINE` | `v2` en un proyecto, `v1` en el otro | Lo único que los diferencia |
| `LEGACY_WORK_FACTOR` | `550` (solo V1) | Más alto = V1 más lenta. Ajustar hasta el tiempo deseado: en Vercel el CPU es distinto al de tu equipo |
| `ADMIN_PASSWORD`, `SEED_DEMO_CUSTOMER` | como ya los tengas | Opcionales |

> Cambiar una variable en Vercel **no afecta al despliegue ya publicado**: hay que volver a desplegar (*Deployments → ⋯ → Redeploy*).

## Pasos (panel de Vercel)

1. Ya tienes un proyecto funcionando: ése será **V2**. Confirma que tiene `RECEIPT_ENGINE=v2` (o que no está definida: por defecto es v2) y vuelve a desplegar.
2. *Add New → Project* y elige **el mismo repositorio**. Nómbralo `tienda-itec-v1`.
3. Antes de pulsar *Deploy*, en *Environment Variables* copia las mismas variables del proyecto V2 y pon `RECEIPT_ENGINE=v1`.
4. Despliega. Cada proyecto tendrá su propia URL.

Con la CLI (equivalente, sin probar en este repositorio):

```bash
vercel link --project tienda-itec-v1       # enlaza o crea el proyecto V1
vercel env add RECEIPT_ENGINE production   # escribe: v1
vercel env add DATABASE_URL production     # la misma cadena de Supabase
vercel env add SECRET_KEY production       # la misma clave del proyecto V2
vercel --prod
```

## Comprobar que cada URL usa el motor correcto

- Entra a `https://<proyecto>/admin`. Arriba, junto a tu nombre, verás una etiqueta **Motor V1** o **Motor V2** (al pasar el ratón indica de dónde sale la configuración). Los clientes no ven esa etiqueta ni en pantalla ni en la API.
- También: `GET /api/admin/config` con el token de administrador devuelve `{"receipt_engine": "v1", ...}`.
- Compra algo en cada tienda y mira en **Ventas** del panel: cada pedido muestra su motor y su tiempo; en **Resumen**, el promedio por motor.

## Ojo con el límite de tiempo de Vercel

V1 tarda 20-30 s. Si tu plan o tu configuración limita las funciones a menos tiempo (el límite por defecto depende del plan y de si tienes *Fluid Compute*), Vercel cortará la compra con un error 504 y **no se guardará el pedido**. Revisa el límite en *Settings → Functions → Max Duration* del proyecto V1. Si no puedes subirlo, baja `LEGACY_WORK_FACTOR` en V1 (por ejemplo a `200`) para que el recibo termine dentro del límite.

## Alternativas

- **Cambiar el motor sin redesplegar** (un solo proyecto): no definas `RECEIPT_ENGINE` y edita en Supabase la fila `MOTOR_RECIBO` de `t_parametro` (`v1`/`v2`). Sirve para alternar, pero **no** para tener las dos versiones a la vez.
- **Local**: `scripts/start_all.sh` levanta V2 (:8010) y V1 (:8011) con la base local (SQLite), sin tocar Supabase ni tu `.env`.
