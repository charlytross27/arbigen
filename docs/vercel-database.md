# PostgreSQL externo para Arbigen en Vercel

La aplicación utiliza **dos proyectos Vercel del mismo repositorio**: `arbigen-web` con raíz `frontend/` para Angular y `arbigen-api` con raíz `backend/` para FastAPI. Existe además un proyecto `arbigen` que también tiene raíz `frontend/` y dominio `arbigen.vercel.app`; es un despliegue duplicado del frontend, no un entorno Development ni otra base de datos. Se conserva hasta decidir qué dominio debe ser el principal. `backend/index.py` exporta `app`, la entrada que Vercel detecta para su Function de Python. La base de datos no vive en Vercel Functions ni en su filesystem: es PostgreSQL administrado por Neon, conectado solo a `arbigen-api` en Production.

Vercel ya no ofrece el producto anterior «Vercel Postgres» para proyectos nuevos. Su [Marketplace de almacenamiento](https://vercel.com/docs/marketplace-storage) ofrece integraciones PostgreSQL como Neon, Supabase y Aurora; la [guía de Postgres en Vercel](https://vercel.com/docs/postgres) confirma ese modelo externo. Arbigen usa SQL estándar de PostgreSQL y no importa un SDK del proveedor. Neon es una opción práctica para el primer despliegue porque ofrece cadenas agrupadas y directas; el código admite otro proveedor compatible.

## Variables por entorno

| Variable | Dónde | Uso |
| --- | --- | --- |
| `DATABASE_URL` | Backend Vercel y desarrollo local | Conexión de la API. Utilizar el endpoint agrupado del proveedor si existe. |
| `DATABASE_MIGRATION_URL` | Entorno seguro que ejecuta Alembic | Conexión directa para DDL. No es necesaria dentro de la Function. |
| `CORS_ORIGINS` | Backend Vercel | Lista JSON con la URL pública exacta del frontend. |
| `ENVIRONMENT` | Backend Vercel | `production` activa la cookie segura `__Host-`. |
| `AUTH_REGISTRATION_CODE` | Backend Vercel | Secreto de 24+ caracteres para el registro privado; solo Production. |
| `MERCADO_LIBRE_ACCESS_TOKEN` | Backend Vercel | Token de la API oficial, usado cuando Apify no está seleccionado. |
| `MARKETPLACE_SEARCH_PROVIDER` | Backend Vercel | `auto`, `apify` o `mercado_libre`; `auto` usa Apify si hay token. |
| `MAX_PRODUCTS_PER_ANALYSIS` | Backend Vercel | Máximo de productos normalizados; 200 por defecto. |
| `APIFY_API_TOKEN` | Backend Vercel | Token privado del actor; nunca se expone a Angular. |
| `APIFY_ACTOR_ID` | Backend Vercel | Actor de Karamelo elegido, configurable sin cambiar el contrato interno. |
| `APIFY_MAX_PAGES` | Backend Vercel | Páginas máximas del actor; 4 por defecto. |
| `APIFY_REQUEST_TIMEOUT_SECONDS` | Backend Vercel | Timeout de consulta síncrona; 120 segundos por defecto. |

La integración de Neon inyectó `DATABASE_URL` y `DATABASE_URL_UNPOOLED` como variables sensibles de Production en `arbigen-api`; no se copiaron al frontend ni al repositorio. Preview no está conectado a esa base. Si se habilita Preview, usa una rama o base separada. En conexiones remotas, usa el TLS que indique el proveedor; no desactives la verificación de certificados para resolver errores de conexión.

[Neon documenta](https://github.com/neondatabase/website/blob/main/content/docs/get-started/connect-neon.md) que su host con `-pooler` sirve para muchas conexiones concurrentes y recomienda la conexión directa para migraciones o funciones de sesión. El backend crea su `Engine` solo cuando una ruta lo necesite, con un pool local pequeño de dos conexiones por instancia, reciclaje y verificación de conexiones. El número total de conexiones crece con las instancias de Vercel, por lo que se utilizará además el pooler del proveedor y se vigilará su límite. [Vercel](https://vercel.com/kb/guide/connection-pooling-with-functions) y [SQLAlchemy](https://docs.sqlalchemy.org/en/20/core/pooling.html) documentan estos patrones.

## Estado del despliegue de la fase 18

El código está en el repositorio privado `charlytross27/arbigen`. Los proyectos [arbigen-web](https://arbigen-web.vercel.app/) y [arbigen-api](https://arbigen-api.vercel.app/api/health) están desplegados desde ese monorepo. `frontend/vercel.json` fija la salida Angular, la [reescritura externa](https://vercel.com/docs/routing/rewrites) de `/api/:path*` hacia la API y el fallback de rutas SPA. Angular usa rutas relativas `/api`; `frontend/proxy.conf.json` solo funciona durante `npm start`.

Neon Free creó `neon-bole-cave`, rama `main`, base `neondb`, vinculada únicamente a `arbigen-api` Production. Se generó SQL offline con Alembic desde las revisiones `0001` a `0004`, se comprobó su integridad y se ejecutó en transacciones desde el editor SQL de Neon, fuera del build y del arranque de Vercel. La consulta posterior devolvió `0004_auth_sessions` y 11 tablas públicas, incluida `alembic_version`. No se guardó una URL de conexión en Git.

En Production quedaron `ENVIRONMENT=production`, `CORS_ORIGINS=["https://arbigen-web.vercel.app"]` y `AUTH_REGISTRATION_CODE` como Secret solo en `arbigen-api`. Ambos proyectos desplegaron el commit de fase 18. `/api/health` respondió 200; `/api/v1/analyses` respondió 401 incluso con el antiguo header demo; `/api/v1/auth/register` respondió 403 con un código incorrecto, confirmando la restricción de invitación; `/login` respondió 200. Las respuestas privadas llevan `Cache-Control: private, no-store`. No se insertaron registros de prueba ni se ejecutó Apify. La base alojada sigue vacía porque las investigaciones locales no se migraron.

El código de invitación nunca se copia al frontend. La [guía de autenticación](autenticacion.md) describe cookie, CSRF y límites pendientes. Para transferir investigaciones locales hará falta un mapeo explícito del usuario demo a una cuenta nueva; localStorage no se copia entre `localhost` y Vercel. El PostgreSQL local estaba apagado durante esta fase, por lo que sus pruebas de integración quedaron pendientes; la prueba de registro y aislamiento se ejecutó con una base temporal y el esquema de Neon se verificó por SQL. Para migraciones posteriores, usar una conexión directa controlada con `DATABASE_MIGRATION_URL`, ejecutar `alembic upgrade head`, `alembic current` y `alembic check` fuera de Vercel; no ejecutar migraciones durante el build.

Si se habilita el actor en Production, guardar `APIFY_API_TOKEN` solo en `arbigen-api` y evaluar el costo antes de cada prueba. `POST /dataset/refresh` puede iniciar una ejecución facturable; `/dataset`, `/features`, `/clusters`, `/forecast` y `/opportunity-score` leen datos guardados sin nuevas búsquedas. La importación CSV de Trends no necesita filesystem persistente. Hay que vigilar la duración de la Function y el tamaño de JSONB si crece la muestra. Las fotografías futuras necesitarán storage externo independiente de PostgreSQL. La [documentación de FastAPI en Vercel](https://vercel.com/docs/frameworks/backend/fastapi) describe el entrypoint y los límites de Functions.
