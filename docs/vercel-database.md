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

## Secuencia para la fase 21: deployment

1. Crear los proyectos Vercel con raíz `frontend/` y `backend/`, sin duplicar el repositorio.
2. Aprovisionar PostgreSQL administrado externo para Production y una base o rama distinta para Preview. Conectar solo el proyecto backend.
3. Guardar `DATABASE_URL` en el entorno backend correspondiente. Guardar `DATABASE_MIGRATION_URL` en el ejecutor controlado de migraciones, con permisos para DDL.
4. Ejecutar desde `backend/` y contra la base correcta: `alembic upgrade head`, seguido de `alembic current` y `alembic check`. Hacer esto **fuera** del build de Vercel y antes de dirigir tráfico a código que necesite el esquema nuevo.
5. Configurar la región de la Function cerca de la base y `CORS_ORIGINS` con el dominio exacto del frontend. En el proyecto frontend, agregar una [reescritura externa de Vercel](https://vercel.com/docs/routing/rewrites) de `/api/:path*` hacia `https://DOMINIO-BACKEND/api/:path*`: Angular llama a rutas relativas `/api`, y `frontend/proxy.conf.json` solo funciona durante `npm start`. Comprobar también que las rutas internas de Angular carguen al recargar la página.
6. Guardar `APIFY_API_TOKEN` en el proyecto backend y configurar el actor de Karamelo elegido. Probar `POST /api/v1/analyses/{id}/dataset/refresh` con búsquedas `MX`, `CO` y `AR` solo cuando se autorice el costo: el backend debe devolver productos normalizados de cada país, con un máximo de `MAX_PRODUCTS_PER_ANALYSIS`. La ejecución es bajo demanda; `maxItems` limita los resultados facturables del actor y `limit` la respuesta. El actor puede tardar hasta `APIFY_REQUEST_TIMEOUT_SECONDS` (120 s por defecto), por lo que la duración permitida de la Function debe superar ese valor. Con Fluid Compute, [Vercel documenta 300 s por defecto](https://vercel.com/docs/functions/configuring-functions/duration); si el proyecto usa otros límites, ajustar el timeout o migrar a ejecuciones asíncronas. Sin Apify, `auto` mantiene la consulta oficial mexicana y su fallback de catálogo, con máximo de 20 resultados.
6a. Aplicar la migración 0002 antes de habilitar el importador de Trends en Production. `POST /api/v1/analyses/{id}/trends` acepta un CSV de hasta 256 KB y guarda puntos normalizados en PostgreSQL; la Function no necesita filesystem persistente ni `pytrends`.
6b. Aplicar la migración 0003 antes de habilitar el ETL. La UI llama a `POST /api/v1/analyses/{id}/dataset/refresh`, que ejecuta el actor una sola vez y persiste la muestra normalizada junto al dataset depurado. `GET /dataset` y `POST /dataset/reprocess` usan PostgreSQL y no ejecutan Apify. Vigilar tamaño de JSONB por muestra y duración total de la Function en Production.
6c. `GET /api/v1/analyses/{id}/features` usa solo el dataset guardado: no necesita otra migración, proveedor ni llamada facturable. La descarga JSON para el cuaderno ocurre en el navegador y no escribe archivos en la Function.
6d. `GET /api/v1/analyses/{id}/opportunity-score` y `POST /api/v1/analyses/{id}/opportunity-score/preview` leen datos persistidos, calculan en memoria y no requieren migración ni llamada facturable a Apify. Los supuestos de precio/costos de la vista previa no se guardan en Vercel ni PostgreSQL.
6d. `GET /api/v1/analyses/{id}/clusters` calcula K-Means de forma determinista sobre los productos depurados (hasta `MAX_PRODUCTS_PER_ANALYSIS`, 200 por defecto) y tampoco llama a Apify. No necesita migración ni librerías numéricas adicionales; conviene vigilar la duración en la Function y ampliar el enfoque si el límite de productos crece.
6e. `GET /api/v1/analyses/{id}/forecast` valida y compara modelos simples sobre puntos de Trends ya persistidos. No descarga series ni llama a Apify, no usa filesystem persistente y no necesita migración ni dependencia nueva. En producción debe conservarse el tiempo de cómputo bajo el límite de la Function si crece el historial.
7. Antes de abrir el sitio al público, reemplazar `X-Demo-Workspace-ID` por autenticación y autorización reales. El UUID que conserva el navegador solo separa datos de la demo y cualquiera que lo conozca podría consultar sus búsquedas. Después validar `/api/health`, creación, listado y lectura de una búsqueda, aislamiento entre cuentas y el fallback SPA.

No hay credenciales de PostgreSQL administrado ni proyectos Vercel configurados en esta fase. Las migraciones hasta `0003_analytical_dataset` se aplicaron a la base local `arbigen`; el flujo de API, incluidos Trends y ETL, se comprobó allí con transacciones revertidas y `alembic check` no encontró diferencias. El aprovisionamiento externo y el despliegue público son trabajo de la fase 21. La [documentación de FastAPI en Vercel](https://vercel.com/docs/frameworks/backend/fastapi) describe el entrypoint y los límites de Functions. Las fotografías futuras necesitarán un storage externo independiente de PostgreSQL.
