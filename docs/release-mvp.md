# Cierre del MVP privado

Alcance aprobado: Opportunity Score **exploratorio**, registro privado por código de invitación y recuperación de contraseña fuera de esta versión. Production comienza vacía: no se copian investigaciones, escenarios ni imágenes locales a Neon o Blob. Los datos de Development permanecen en PostgreSQL y disco locales.

## Estado validado en Development

- Una investigación local tiene muestra, serie de Trends y escenario financiero guardado. `GET /opportunity-score` puede calcular la versión `exploratory-v2`, sin entradas faltantes, y devuelve dos pruebas de sensibilidad. Las advertencias indican muestra pequeña y geografía no verificable en el CSV; el número no es una predicción de ventas.
- La base local está en `0009_studio_attempts`. Las 91 pruebas del backend pasaron con una base PostgreSQL temporal y migrada, eliminada al terminar. La compilación Angular de Development y Production y las pruebas del frontend pasaron. Los proveedores de pago se simularon.

## Estado de Production y publicación pendiente

- Neon `neon-bole-cave` (rama `main`, base `neondb`) ya tiene las migraciones aditivas `0005`–`0009`. Se verificó `alembic_version=0009_studio_attempts`, las tablas financieras y de borradores, una cuenta existente y cero investigaciones/campañas. El editor SQL volvió a modo de solo lectura.
- `arbigen-api` ya tiene `IMAGE_STORAGE_BACKEND=vercel_blob` como variable Config exclusiva de Production. El almacén `arbigen-api-blob` es Private y el token local corresponde a ese almacén. Aún falta confirmar las tres variables Secret de Production.

1. Revisar y fusionar la rama de Development en `main`. Vercel despliega `main` en `arbigen-web` y `arbigen-api`; no publicar el frontend nuevo antes de que la API y la base estén preparadas.
2. En `arbigen-api` Production, conservar `DATABASE_URL`, `ENVIRONMENT=production`, `CORS_ORIGINS` y `AUTH_REGISTRATION_CODE`. Confirmar como Secret `OPENAI_API_KEY`, `APIFY_API_TOKEN` y `BLOB_READ_WRITE_TOKEN` para habilitar generación, búsqueda multipaís y catálogos. No colocar estas variables en Angular. La conexión del Blob store incluye Production y Preview, por lo que conviene limitarla a Production. El SDK Python incluido requiere `BLOB_READ_WRITE_TOKEN`; `BLOB_STORE_ID` por sí solo no habilita el adaptador actual.
3. Desplegar la API y después el frontend. Probar salud, registro con invitación, inicio/cierre de sesión, una investigación vacía, importación CSV y escenario financiero sin llamar a Apify. Una búsqueda real o generación de imagen puede cobrar; autorizarla por separado antes de ejecutarla.
4. Programar la limpieza de borradores vencidos con `python -m scripts.cleanup_studio_drafts --apply` en un entorno seguro que tenga acceso a Neon y Blob. El script de inventario, sin `--apply`, permite comprobar primero qué se eliminaría.

El lanzamiento puede empezar sin datos y sin una nueva consulta pagada. El Opportunity Score seguirá indicado como exploratorio hasta contar con ventas y competencia observadas para calibrarlo.
