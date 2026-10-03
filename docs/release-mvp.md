# Cierre del MVP privado

Alcance aprobado: Opportunity Score **exploratorio**, registro privado por código de invitación y recuperación de contraseña fuera de esta versión. Production comienza vacía: no se copian investigaciones, escenarios ni imágenes locales a Neon o Blob. Los datos de Development permanecen en PostgreSQL y disco locales.

## Estado validado en Development

- Una investigación local tiene muestra, serie de Trends y escenario financiero guardado. `GET /opportunity-score` puede calcular la versión `exploratory-v2`, sin entradas faltantes, y devuelve dos pruebas de sensibilidad. Las advertencias indican muestra pequeña y geografía no verificable en el CSV; el número no es una predicción de ventas.
- La investigación histórica permanece en Development. Para este release, las 93 pruebas del backend pasaron con una base PostgreSQL temporal migrada hasta `0010_listing_signals`, eliminada al terminar. La compilación Angular y las pruebas de simulador, análisis e imágenes del frontend pasaron. Los proveedores de pago se simularon.

## Estado de Production

- Neon `neon-bole-cave` (rama `main`, base `neondb`) tiene las migraciones hasta `0010_listing_signals`. Se verificó `alembic_version=0010_listing_signals` y la presencia de `products.listing_signals` y `marketplace_snapshots.reported_total_results`. La migración fue aditiva; no se copiaron datos locales. El editor SQL volvió a modo de solo lectura.
- `arbigen-api` tiene `IMAGE_STORAGE_BACKEND=vercel_blob` como variable Config, y `OPENAI_API_KEY`, `APIFY_API_TOKEN` y `BLOB_READ_WRITE_TOKEN` como Secret, todas exclusivas de Production. El almacén `arbigen-api-blob` es Private, está conectado solo a Production y el token local corresponde a ese almacén.
- El PR [#1](https://github.com/charlytross27/arbigen/pull/1) se integró en `main` como `1f8b70c`. Los despliegues de `arbigen-api` y `arbigen-web` quedaron en estado Ready con ese commit. `/api/health` responde 200 en API y proxy web, `/login` responde 200, la ruta privada `/api/v1/auth/me` responde 401 sin sesión y el preflight CORS permite `https://arbigen-web.vercel.app`.

## Comprobaciones operativas pendientes

1. Validar con la cuenta de Production el inicio/cierre de sesión, una investigación vacía, la importación CSV y el escenario financiero. Las pruebas automatizadas cubren esas rutas, pero la comprobación manual autenticada en Production no se hizo porque no se comparten contraseñas.
2. Validar una búsqueda real de Apify y una generación de imagen cuando se quiera comprobar la integración completa. Ambas pueden generar cargos; las pruebas del release usaron simulaciones y no iniciaron consultas pagadas.
3. Programar la limpieza de borradores vencidos con `python -m scripts.cleanup_studio_drafts --apply` en un entorno seguro que tenga acceso a Neon y Blob. El script de inventario, sin `--apply`, permite comprobar primero qué se eliminaría. Production no tenía borradores en la verificación inicial.

El lanzamiento puede empezar sin datos y sin una nueva consulta pagada. El Opportunity Score seguirá indicado como exploratorio hasta contar con ventas y competencia observadas para calibrarlo.
