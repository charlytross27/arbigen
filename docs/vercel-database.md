# PostgreSQL externo para Arbigen en Vercel

La arquitectura de despliegue usa **dos proyectos Vercel del mismo repositorio**: uno con raíz `frontend/` para Angular y otro con raíz `backend/` para FastAPI. `backend/index.py` exporta `app`, la entrada que Vercel detecta para su Function de Python. La base de datos no vive en Vercel Functions ni en su filesystem: será PostgreSQL administrado por un proveedor externo conectado al proyecto backend.

Vercel ya no ofrece el producto anterior «Vercel Postgres» para proyectos nuevos. Su [Marketplace de almacenamiento](https://vercel.com/docs/marketplace-storage) ofrece integraciones PostgreSQL como Neon, Supabase y Aurora; la [guía de Postgres en Vercel](https://vercel.com/docs/postgres) confirma ese modelo externo. Arbigen usa SQL estándar de PostgreSQL y no importa un SDK del proveedor. Neon es una opción práctica para el primer despliegue porque ofrece cadenas agrupadas y directas; el código admite otro proveedor compatible.

## Variables por entorno

| Variable | Dónde | Uso |
| --- | --- | --- |
| `DATABASE_URL` | Backend Vercel y desarrollo local | Conexión de la API. Utilizar el endpoint agrupado del proveedor si existe. |
| `DATABASE_MIGRATION_URL` | Entorno seguro que ejecuta Alembic | Conexión directa para DDL. No es necesaria dentro de la Function. |
| `CORS_ORIGINS` | Backend Vercel | Lista JSON con la URL pública exacta del frontend. |
| `MERCADO_LIBRE_ACCESS_TOKEN` | Backend Vercel | Token de la API oficial, usado cuando Apify no está seleccionado. |
| `MARKETPLACE_SEARCH_PROVIDER` | Backend Vercel | `auto`, `apify` o `mercado_libre`; `auto` usa Apify si hay token. |
| `MAX_PRODUCTS_PER_ANALYSIS` | Backend Vercel | Máximo de productos normalizados; 200 por defecto. |
| `APIFY_API_TOKEN` | Backend Vercel | Token privado del actor; nunca se expone a Angular. |
| `APIFY_ACTOR_ID` | Backend Vercel | Actor de Karamelo elegido, configurable sin cambiar el contrato interno. |
| `APIFY_MAX_PAGES` | Backend Vercel | Páginas máximas del actor; 4 por defecto. |
| `APIFY_REQUEST_TIMEOUT_SECONDS` | Backend Vercel | Timeout de consulta síncrona; 120 segundos por defecto. |

Las integraciones pueden inyectar variables con otros nombres; mapéalas a los nombres anteriores en la configuración del proyecto. El frontend no recibe URLs de PostgreSQL ni secretos. Mantén bases o ramas separadas para Preview y Production. En conexiones remotas, usa el TLS que indique el proveedor; no desactives la verificación de certificados para resolver errores de conexión.

[Neon documenta](https://github.com/neondatabase/website/blob/main/content/docs/get-started/connect-neon.md) que su host con `-pooler` sirve para muchas conexiones concurrentes y recomienda la conexión directa para migraciones o funciones de sesión. El backend crea su `Engine` solo cuando una ruta lo necesite, con un pool local pequeño de dos conexiones por instancia, reciclaje y verificación de conexiones. El número total de conexiones crece con las instancias de Vercel, por lo que se utilizará además el pooler del proveedor y se vigilará su límite. [Vercel](https://vercel.com/kb/guide/connection-pooling-with-functions) y [SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/pooling.html) documentan estos patrones.

## Secuencia para terminar el despliegue de la fase 17

1. Publicar el código local en el repositorio privado `charlytross27/arbigen`. Su rama remota `main` contiene de momento solo README y `.gitignore`; Vercel no puede construir aún el monorepo completo.
2. Crear dos proyectos Vercel desde ese mismo repositorio: raíz `backend/` para FastAPI y raíz `frontend/` para Angular. `backend/index.py` es la entrada reconocida; `frontend/vercel.json` fija `npm run build`, salida `dist/arbigen/browser`, reescritura externa de `/api` y fallback de rutas SPA.
3. En Vercel → Storage → Neon → Create, revisar y aceptar los términos de Vercel/Neon, elegir el plan y la región antes de crear el recurso. Neon tiene una opción desde $0, pero se debe confirmar el plan mostrado. Vincular el recurso solo al proyecto backend. Crear una base o rama separada para Preview antes de usarlo con datos de prueba.
4. Mapear la URL agrupada inyectada por Neon a `DATABASE_URL` en el proyecto backend; conservar la URL directa únicamente para el proceso controlado de migraciones como `DATABASE_MIGRATION_URL`. No colocar estas URL en el proyecto frontend ni en Git. El nombre exacto de las variables de Neon se comprueba una vez creado el recurso.
5. Ejecutar desde `backend/` y contra la base correcta: `alembic upgrade head`, seguido de `alembic current` y `alembic check`. Hacer esto **fuera** del build de Vercel y antes de dirigir tráfico a código que necesite el esquema nuevo.
6. Configurar la región de la Function cerca de la base y `CORS_ORIGINS` con el dominio exacto del frontend. La [reescritura externa de Vercel](https://vercel.com/docs/routing/rewrites) de `/api/:path*` hacia `arbigen-api.vercel.app` y el fallback SPA están en `frontend/vercel.json`; si cambia ese dominio, actualizar y volver a desplegar el frontend. Angular llama a rutas relativas `/api`; `frontend/proxy.conf.json` solo funciona durante `npm start`.
7. Guardar `APIFY_API_TOKEN` solo en el proyecto backend y configurar el actor de Karamelo elegido. No ejecutar una búsqueda de prueba salvo necesidad concreta y autorización de costo. La ejecución es bajo demanda; el timeout del actor (120 s por defecto) debe quedar bajo la duración permitida de la Function. Con Fluid Compute, [Vercel documenta 300 s por defecto](https://vercel.com/docs/functions/configuring-functions/duration). Sin Apify, `auto` mantiene la consulta oficial mexicana y su fallback de catálogo, con máximo de 20 resultados.
8. Validar `/api/health`, Inicio, creación/listado/lectura de una búsqueda, aislamiento entre espacios, la reescritura `/api` y la recarga de una ruta Angular interna. Si se migran investigaciones locales, también habrá que transferir de forma controlada el ID del espacio, porque localStorage pertenece al origen local y no se copia al nuevo dominio.
9. Antes de exponer datos privados en un sitio público, sustituir `X-Demo-Workspace-ID` por autenticación y autorización reales o limitar el acceso al despliegue. El UUID que conserva el navegador separa datos de la demo, pero cualquiera que lo conozca podría consultar sus búsquedas.

Todavía no hay un recurso PostgreSQL administrado ni despliegues de estos proyectos. Las migraciones hasta `0003_analytical_dataset` se aplicaron a la base local `arbigen`; las pruebas de la API y del nuevo Inicio usan transacciones revertidas. La [documentación de FastAPI en Vercel](https://vercel.com/docs/frameworks/backend/fastapi) describe el entrypoint y los límites de Functions. Las fotografías futuras necesitarán un storage externo independiente de PostgreSQL.

El esquema remoto debe incluir las migraciones `0001`, `0002` y `0003` antes de probar Inicio o las rutas analíticas. La importación CSV de Trends guarda puntos sin filesystem persistente; ETL/refresh puede ejecutar Apify una vez, mientras `/dataset`, `/features`, `/clusters`, `/forecast` y `/opportunity-score` leen datos ya guardados y no generan consultas facturables. Vigilar duración de la Function y tamaño de JSONB si crece la muestra.
