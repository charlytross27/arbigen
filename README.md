# Arbigen · Trend2Catalog AI

Plataforma de inteligencia de mercado y creación de catálogos para e-commerce, construida por slices. **Alcance actual en Development: Inicio y resultados usan investigaciones, productos depurados y series de Trends guardados en PostgreSQL; Estudio IA genera imágenes con OpenAI. Hay una versión anterior desplegada en Vercel con PostgreSQL alojado en Neon; los cambios recientes siguen solo en Development.** El [plan de cierre del MVP privado](docs/release-mvp.md) recoge las verificaciones y la publicación pendiente.

## Implementado

- Monorepo con Angular 21 (standalone, TypeScript estricto, Router, HttpClient y SCSS) y FastAPI.
- Sidebar, header, navegación responsive, títulos por ruta y página 404.
- Inicio con cuatro conteos reales, investigaciones recientes y actividad registrada en PostgreSQL, aislados por la cuenta autenticada. El selector de 7/30 días filtra por fecha de creación; la actividad filtra por fecha de cada evento. Hay estados de carga, error con reintento y vacío.
- Registro privado con código de invitación, inicio y cierre de sesión. La API autoriza cada investigación por usuario; el header demo y el UUID de `localStorage` dejaron de otorgar acceso. El perfil muestra el nombre y correo reales de la sesión.
- Explorador con palabra clave, país, categoría opcional y periodo. Valida y guarda la investigación mediante FastAPI en PostgreSQL; muestra un error recuperable si la API no está disponible.
- Mis análisis lista investigaciones guardadas para la cuenta autenticada y permite abrir una ficha con los parámetros registrados. Desde cada ficha se puede consultar y guardar una muestra de productos de Mercado Libre, limitada por `MAX_PRODUCTS_PER_ANALYSIS` (200 por defecto), e importar una serie de Google Trends para el mismo término y país. El ETL muestra cuántos productos conservó y por qué excluyó otros.
- Resultado de análisis para investigaciones guardadas, con resumen de productos, interés y precios, gráfico de distribución de la muestra, evolución de Trends, pronóstico condicionado por evidencia y grupos calculados. Un ID inexistente muestra un estado de investigación no encontrada.
- Estudio IA genera 1–4 imágenes reales a partir de una fotografía de referencia mediante OpenAI. Permite elegir estilo, escena, iluminación y formato; revisar, seleccionar y descargar los PNG.
- Mis catálogos muestra campañas reales guardadas por cuenta en Development, sin campañas ficticias. Permite buscar, abrir, marcar favoritos, descargar, solicitar nuevas variaciones con OpenAI y eliminar con opción de deshacer. El catálogo incluye las vistas seleccionadas en Estudio IA o todas si no se seleccionó ninguna. Si nace de un producto elegido en «Evaluar rentabilidad», conserva el vínculo con esa investigación y permite volver a ella.
- `GET /api/health`, configuración por entorno, errores JSON centralizados y pruebas de API.
- SQLAlchemy y Alembic con ocho entidades iniciales y migración PostgreSQL. La entrada `backend/index.py` permite que Vercel detecte FastAPI al usar `backend/` como raíz del proyecto.
- `POST /api/v1/analyses`, `GET /api/v1/analyses` paginado y `GET /api/v1/analyses/{id}` con validación, autorización por usuario autenticado y respuestas sin métricas inventadas.
- La búsqueda de productos depende de `MarketplaceSearchProvider`, no de Apify ni de campos de un actor. Con `APIFY_API_TOKEN` configurado, `auto` usa el actor de Karamelo para MX/CO/AR; sin él conserva la API oficial mexicana y su fallback de catálogo. Los tokens quedan solo en FastAPI y se guarda una muestra normalizada, nunca la respuesta cruda del actor.
- `GET/POST /api/v1/analyses/{id}/trends` lee e importa un CSV de Google Trends mediante `TrendsProvider`. Se validan término, fechas e índice; el país se valida cuando figura dentro del encabezado. La serie normalizada queda en PostgreSQL, no el archivo. `<1` se conserva como valor censurado, distinto de cero.
- `POST /api/v1/analyses/{id}/dataset/refresh` consulta el proveedor una vez, guarda la muestra normalizada en `marketplace_snapshots` y los productos depurados en `products`. `GET /dataset` lee esos datos sin consulta externa; `POST /dataset/reprocess` aplica de nuevo el ETL a la muestra guardada sin gasto de extracción. Trends se incorpora a la vista analítica conservando sus valores censurados.
- `GET /api/v1/analyses/{id}/features` calcula sobre el dataset guardado cobertura y distribución de precios, pistas de material, cobertura/volatilidad de Trends, media móvil, crecimiento, momentum y aceleración cuando hay ventanas válidas. No consulta proveedores; devuelve `null` si no hay evidencia suficiente. La ficha guardada muestra estas señales y exporta el dataset como JSON para el cuaderno reproducible [arbigen_ciencia_de_datos.ipynb](notebooks/arbigen_ciencia_de_datos.ipynb).
- `GET /api/v1/analyses/{id}/clusters` calcula grupos reproducibles sobre productos depurados ya guardados, sin consultar Apify. Usa K-Means determinista con precio normalizado y pistas de material de menor peso; compara 2–4 grupos por silueta, exige muestra y separación mínimas y muestra tamaño, precios y ejemplos de cada grupo. No elige un grupo recomendado sin evidencia comercial.
- `GET /api/v1/analyses/{id}/forecast` lee solo Trends persistido y compara baselines mediante backtesting cronológico de tres pasos. Publica método, errores, dirección reciente y tres valores del índice con un rango orientativo únicamente si hay al menos 16 puntos regulares y el error validado no supera 20 puntos; de otro modo explica por qué no hay pronóstico.
- `GET /api/v1/analyses/{id}/opportunity-score` usa el escenario financiero guardado, si existe, y explica qué evidencia falta; sin costos explícitos mantiene `score: null`. `POST /api/v1/analyses/{id}/opportunity-score/preview` permite probar otros importes y pesos sin sobrescribir el escenario ni consultar Apify.
- `/opportunity/saved/:id` abre la muestra de productos depurados de una investigación real, permite elegir una publicación, calcular rentabilidad por unidad con cinco importes introducidos por el usuario y guardar un escenario privado. `GET/PUT /api/v1/analyses/{id}/financial-scenario` leen/actualizan ese escenario. El precio y título de referencia se conservan si un reprocesamiento sustituye los productos; actualizar el escenario exige elegir una publicación actual. El JSON descargable alimenta el cuaderno.
- `GET /api/v1/dashboard?days=7|30` agrega investigaciones, muestras, productos con precio y series importadas de la cuenta autenticada; devuelve hasta cinco investigaciones recientes y seis eventos reales. No ejecuta proveedores externos ni inventa ROI, score o competencia.

**Inicio y la ruta de análisis muestran datos de la cuenta, sin métricas ficticias.** Los parámetros que se envían desde el Explorador se guardan en PostgreSQL. La ficha puede consultar datos actuales de Mercado Libre si el proveedor configurado admite el país. Una publicación puede incluir precio y enlace; un producto de catálogo no incluye ninguno de los dos y se identifica como tal. La muestra y el dataset depurado no son volumen de ventas ni una medida de demanda, competencia o tamaño de mercado. La categoría y el periodo guardados aún no filtran esa consulta. La serie importada de Google Trends es un índice relativo de interés, no ventas ni búsquedas absolutas; el periodo elegido tampoco se verifica automáticamente contra el CSV. La ruta de rentabilidad usa un producto de la muestra real y conserva los costos y el precio de venta que introduce el usuario. La ficha de análisis usa el escenario guardado para la puntuación y mantiene un formulario de vista previa temporal para probar otros pesos o costos. El pronóstico y los grupos de una investigación guardada se calculan con los datos disponibles.

Estudio IA crea un borrador privado y sube la fotografía en fragmentos de 2 MB al backend autenticado. Solo después de validar la foto llama a OpenAI con la clave del servidor. Cada pulsación de generar, regenerar o añadir variación puede generar un cargo; las pruebas automatizadas simulan OpenAI y no consumen la API. El backend guarda las vistas PNG y devuelve referencias pequeñas; la API entrega los archivos mediante respuestas por fragmentos. Crear un catálogo copia las vistas elegidas y la foto original sin volver a enviarlas en JSON. Si se pierde una respuesta, «Comprobar resultado» consulta el mismo borrador sin iniciar otra generación; un intento atascado se marca interrumpido tras al menos seis minutos y solo una acción explícita crea una solicitud nueva. Los borradores vencen tras 24 horas; la última generación se puede recuperar en la misma pestaña incluso tras recargar, mientras los catálogos creados permanecen en la cuenta de Development. No se ejecuta Apify en este flujo.

En Development, configura `OPENAI_API_KEY` en `backend/.env` e inicia backend y frontend como de costumbre. Si tu proyecto de OpenAI no tiene acceso al modelo predeterminado, establece `OPENAI_IMAGE_MODEL` con un modelo de edición disponible para tu cuenta. [OpenAI documenta el endpoint de edición y sus parámetros](https://developers.openai.com/api/reference/cli/resources/images/methods/edit); algunos modelos pueden requerir verificar la organización. El usuario ya comprobó una generación real en Development; las pruebas de interrupción usan respuestas simuladas y no requieren repetir la llamada.

## Requisitos

- Node.js 22.12+ de la rama 22 (verificado con 22.13.0), npm 11.
- Python 3.11+ con `venv` y `pip`.
- Estudio IA requiere iniciar sesión, FastAPI y `OPENAI_API_KEY`; la sesión privada usa PostgreSQL. Mis catálogos conserva metadatos en PostgreSQL e imágenes privadas en disco local de Development. `/api/health` funciona sin base de datos.

Se eligió Angular 21 por su compatibilidad con el Node instalado. La [matriz oficial de Angular](https://angular.dev/reference/versions) documenta las versiones admitidas.

## Levantar frontend

Desde la raíz del repositorio:

```bash
cd frontend
npm ci
npm start
```

Abrir [http://localhost:4200](http://localhost:4200). `npm start` selecciona `development` en `angular.json`; su proxy `/api/**` dirige todas las rutas de API a FastAPI en `127.0.0.1:8000`. El encabezado muestra «Desarrollo local». Inicia también backend y PostgreSQL para ver Inicio y guardar búsquedas. La [guía de entornos](docs/entornos.md) explica cómo conservar los datos locales, registrar una cuenta de desarrollo y reasignar investigaciones anteriores a esa cuenta.

```bash
npm run build
```

`npm run build` selecciona `production`; `npm run build:development` compila la variante local sin desplegarla. Ambas dejan la salida en `frontend/dist/arbigen/browser/`, por lo que no se ejecutan simultáneamente.

## Levantar backend

En otra terminal, desde la raíz:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
test -f .env || cp .env.example .env
```

Configura `DATABASE_URL` en `backend/.env` y aplica la migración una vez. Para el actor de Apify elegido agrega `APIFY_API_TOKEN` en ese mismo archivo; `APIFY_ACTOR_ID` ya tiene el valor de Karamelo. Sin token de Apify, `auto` usa `MERCADO_LIBRE_ACCESS_TOKEN` y la API oficial. Reinicia FastAPI después de cambiar la configuración. Después inicia la API:

```bash
alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

Para instalar únicamente dependencias de ejecución, utilizar `requirements.txt`.

```bash
curl http://localhost:8000/api/health
```

Respuesta HTTP 200:

```json
{"status":"ok"}
```

Documentación interactiva: [http://localhost:8000/docs](http://localhost:8000/docs).

## Base de datos y migraciones

Configura `DATABASE_URL` en `backend/.env` con una URL PostgreSQL. Si el proveedor ofrece un endpoint agrupado, úsalo para la aplicación. Configura `DATABASE_MIGRATION_URL` con su endpoint directo para ejecutar Alembic; localmente puede omitirse y se utilizará `DATABASE_URL`. Aceptamos URLs `postgres://` y `postgresql://` y las normalizamos al driver `psycopg`. Para un proveedor remoto incluye el TLS requerido por él, por ejemplo `?sslmode=require`.

```bash
cd backend
source .venv/bin/activate
alembic upgrade head
alembic current
alembic check
```

`alembic downgrade base` **elimina las tablas**; úsalo solo en una base de pruebas desechable. La migración 0002 rechaza un downgrade si existen valores `<1`, porque el esquema anterior no puede representarlos sin corromperlos. No se ejecutan migraciones al iniciar FastAPI ni durante el build de Vercel. No hay seeds: los fixtures actuales del frontend permanecen en memoria y no se copian a PostgreSQL.

El registro privado exige un código de invitación configurado solo en el backend. Las contraseñas se guardan con Argon2; cada sesión revocable usa una cookie HttpOnly, Secure y SameSite=Strict en Production. Las rutas de datos obtienen el usuario desde la sesión y exigen un token CSRF en escrituras. Los antiguos UUID demo no otorgan acceso ni se migran automáticamente a una cuenta. Ver [acceso privado y límites actuales](docs/autenticacion.md).

La ficha guardada llama a `POST /api/v1/analyses/{id}/dataset/refresh` solo al pulsar «Consultar y preparar». El servicio pide hasta `MAX_PRODUCTS_PER_ANALYSIS` (200 por defecto) a `MarketplaceSearchProvider` y recibe exclusivamente `MarketplaceProduct` internos: ID, título, precio y moneda opcionales, enlace e imagen HTTPS opcionales. El adaptador Apify usa el [actor de Karamelo](https://apify.com/karamelo/mercadolibre-scraper-espanol-castellano) con `keyword`, la URL de listado de México, Colombia o Argentina según el análisis, hasta `APIFY_MAX_PAGES` (4 por defecto), sin anuncios patrocinados ni páginas de detalle. La API de Apify recibe `maxItems` como tope de resultados facturables y `limit` como tope de respuesta; el backend vuelve a limitar la muestra y el ETL deduplica para el dataset. La ejecución síncrona tiene timeout configurable (120 segundos por defecto). Si no se configura Apify, el adaptador oficial solo admite México: intenta `/sites/MLM/search` y, ante 403, `/products/search`; sus endpoints devuelven una muestra menor, de hasta 20 elementos. La respuesta indica `source: listings` o `source: catalog`; el catálogo no contiene precios ni enlaces de publicaciones. [Apify documenta el endpoint síncrono y sus límites](https://docs.apify.com/api/v2/actor-run-sync-get-dataset-items-post).

El ETL trabaja solo sobre `MarketplaceProduct` y `TrendObservation`. Guarda la muestra normalizada del proveedor en `marketplace_snapshots`, sin JSON específico de Apify, y el dataset de productos con precio válido en `products`. Normaliza espacios, entidades HTML y Unicode de títulos; deduplica por ID; redondea precios a dos decimales en la moneda del país; excluye precios ausentes, inválidos o con moneda incorrecta; y extrae pistas de material del título, marcadas como no verificadas. No convierte MXN/COP/ARS entre sí porque no hay una fuente de tipos de cambio. Los productos de catálogo sin precio permanecen en la muestra, pero no entran en cálculos de precio o clustering. Los puntos de Trends, incluidos `<1`, se incluyen en la lectura analítica sin imputaciones. `POST /dataset/reprocess` permite repetir estas reglas sobre la muestra guardada sin llamar a Apify. Variables descriptivas, grupos y pronóstico se calculan al leer datos guardados. El escenario financiero se persiste por investigación en `financial_scenarios`; el score usa ese escenario o una vista previa temporal explícita.

La segmentación exige al menos ocho productos con precio, cuatro precios distintos y una amplitud de precios de 15 % respecto a la mediana. Una regla de Tukey puede dejar fuera del **ajuste** precios atípicos si representan como máximo el 10 % y quedan al menos ocho productos; el reporte informa cuántos se excluyeron, sin borrarlos del dataset. Estandariza `log(1 + precio)`, incorpora pistas de material con peso 0,35, ajusta K-Means de 2–4 grupos con inicialización determinista y solo devuelve grupos de al menos dos productos y silueta media ≥ 0,20. El máximo de entrada sigue siendo `MAX_PRODUCTS_PER_ANALYSIS` (200 por defecto). La silueta mide separación interna de la muestra, no demanda ni potencial comercial. Los grupos se recalculan al abrir la ficha y no se persisten en `clusters`; no se recomienda ninguno por ahora. No se requieren embeddings, PCA ni nuevas dependencias en esta fase.

El pronóstico compara último valor, media de tres, tendencia lineal y patrón estacional ingenuo cuando existen dos ciclos. Valida un horizonte de tres puntos con al menos seis orígenes cronológicos y selecciona por MAE. Exige al menos 16 observaciones recientes consecutivas, frecuencia regular y MAE ≤ 20 puntos del índice. Los valores `<1` no se imputan: solo se usa la secuencia posterior al último censurado. El rango orientativo usa errores retrospectivos por horizonte y un piso de cinco puntos; no es un intervalo de confianza garantizado. El índice y el rango se limitan a 0–100. Un pronóstico de Trends no representa ventas, volumen absoluto ni Opportunity Score.

La fórmula `exploratory-v2` conserva los cuatro componentes de `v1`: crecimiento reciente de Trends (`clip(50 + crecimiento %)`), desempeño del pronóstico en pruebas retrospectivas (`clip(100 − 5 × MAE)`), margen (`clip(2,5 × margen %)`) y ROI (`clip(ROI %)`) por unidad, todos limitados a 0–100. El campo técnico `stability` representa desempeño histórico del pronóstico, **no estabilidad del mercado**. Los pesos por defecto son 0,25/0,15/0,35/0,25 y pueden cambiarse si suman 1. Una pérdida da score cero. Se exigen ocho productos con precio, crecimiento 3 contra 3, pronóstico validado, precio y costos explícitos y ROI definido; si falta algo, `score` es `null`. La respuesta informa tamaño y cobertura de la muestra, procedencia y fecha de Trends, fecha de precios y MAE del backtest. Advierte si la muestra tiene 8–19 productos, menos del 80 % de precios válidos, geografía no verificable, precios de más de 30 días o una serie antigua para su frecuencia (14/42/93 días para diaria/semanal/mensual). Estas advertencias no alteran el número silenciosamente. También recalcula utilidad y score si el precio baja 10 % o si suben 10 % los costos de producto, envío y otros gastos. Son pruebas de supuestos, no predicciones. La escala sigue sin calibración comercial: **no contiene demanda absoluta, ventas ni competencia medida**. Impuestos, devoluciones y publicidad solo cuentan si el usuario los introduce en «Otros costos». El escenario guardado usa la migración 0005; la vista previa no lo modifica.

Para importar Trends, abre la ficha guardada, exporta desde [Google Trends](https://trends.google.com/trends/) el gráfico «Interés a lo largo del tiempo» para la misma palabra clave y país, con una sola serie, y elige el CSV en la ficha. El archivo debe ser UTF-8 y medir hasta 256 KB. Se admiten encabezados `Day/Week/Month, término: (país)` y `Time, término` con fechas ISO. La API valida término, fechas únicas y valores de 0 a 100 o `<1`; cuando el encabezado declara un país, también lo verifica. El formato `Time` **no incluye la geografía dentro del CSV**, por lo que se guarda con procedencia `google_trends_csv_geo_unverified` y la ficha advierte que debes confirmar el país elegido al exportar. El nombre del archivo tampoco prueba la geografía. La importación reemplaza atómicamente la serie previa. No consulta Google ni Apify al abrir la ficha. `pytrends` no se incluye: su repositorio está [archivado](https://github.com/GeneralMills/pytrends) y es una interfaz no oficial; la [API oficial](https://developers.google.com/search/apis/trends) sigue con acceso alfa. `TrendsProvider` permite añadir otro adaptador posteriormente.

## Cuaderno de ciencia de datos

El archivo [notebooks/arbigen_ciencia_de_datos.ipynb](notebooks/arbigen_ciencia_de_datos.ipynb) reúne en una sola secuencia la procedencia de fuentes, el ETL, la ingeniería de variables, la distribución de precios, el clustering, el backtesting, la rentabilidad por unidad, el score exploratorio y sus límites. Seguirá creciendo con las próximas fases de ciencia de datos. En una ficha guardada pulsa «Descargar datos para el cuaderno» y guarda el archivo como `notebooks/data/dataset.json`. Esta carpeta se ignora en Git; no hace falta crear datos ficticios ni repetir una consulta a Apify. También puedes establecer `ARBIGEN_DATASET_PATH` con una ruta absoluta a otro archivo exportado.

Para abrirlo desde la raíz del proyecto, con el entorno del backend activo, instala Jupyter en ese entorno si no lo tienes y ejecuta:

```bash
cd backend
source .venv/bin/activate
python -m pip install jupyterlab ipykernel
cd ../notebooks
jupyter lab arbigen_ciencia_de_datos.ipynb
```

El cuaderno importa `prepare_dataset`, `calculate_features`, `cluster_products`, `forecast_trends`, `calculate_profitability` y `calculate_score` del backend: no mantiene fórmulas paralelas. No pide tokens, no conecta con PostgreSQL y no genera cargos. Si solo has importado Trends, también puedes exportar y analizar esa serie; el clustering y el score informarán qué falta. Para estudiar un escenario financiero y su sensibilidad al precio, descárgalo como JSON desde «Evaluar rentabilidad» y apunta `ARBIGEN_SCENARIO_PATH` a su ruta absoluta antes de abrir el cuaderno. Los JSON exportados permanecen fuera de Git.

Para un ensayo integral en una base local dedicada, configura `ARBIGEN_TEST_DATABASE_URL` con su conexión y ejecuta `python -m pytest -q`. La prueba hace rollback de sus inserciones. Consulta la [guía de Vercel y PostgreSQL](docs/vercel-database.md).

## Configuración

`backend/.env.example` es la referencia ejecutable; el `.env.example` raíz documenta las variables previstas para el proyecto. `Settings` lee `backend/.env` y permite sobrescribirlo con variables del proceso.

| Variable activa | Valor predeterminado | Uso |
| --- | --- | --- |
| `APP_NAME` | `Arbigen API` | Nombre de la API |
| `ENVIRONMENT` | `development` | `development`, `test` o `production` |
| `CORS_ORIGINS` | `localhost:4200` y `127.0.0.1:4200` | Lista JSON de orígenes permitidos |
| `AUTH_REGISTRATION_CODE` | vacío | Código de invitación de al menos 24 caracteres; sin él el registro responde 503 |
| `DATABASE_URL` | vacío | URL de PostgreSQL para FastAPI; preferiblemente endpoint agrupado en Vercel |
| `DATABASE_MIGRATION_URL` | vacío | URL directa para Alembic; si falta, usa `DATABASE_URL` |
| `MERCADO_LIBRE_ACCESS_TOKEN` | vacío | Token para la API oficial de respaldo; nunca se envía a Angular |
| `MARKETPLACE_SEARCH_PROVIDER` | `auto` | `auto`, `apify` o `mercado_libre`; `auto` usa Apify si hay token |
| `MAX_PRODUCTS_PER_ANALYSIS` | `200` | Máximo interno de productos por consulta (1–1000) |
| `APIFY_API_TOKEN` | vacío | Token privado para el actor de Apify |
| `APIFY_ACTOR_ID` | `karamelo/mercadolibre-scraper-espanol-castellano` | Actor seleccionado; su contrato se traduce en el adaptador |
| `APIFY_MAX_PAGES` | `4` | Máximo de páginas que procesa el actor (1–50) |
| `APIFY_REQUEST_TIMEOUT_SECONDS` | `120` | Timeout de la ejecución síncrona (10–290 s) |
| `OPENAI_API_KEY` | vacío | Clave privada para la generación de imágenes de Estudio IA |
| `OPENAI_IMAGE_MODEL` | `gpt-image-2` si está vacío | Modelo de edición de imágenes compatible con la API |
| `OPENAI_IMAGE_TIMEOUT_SECONDS` | `180` | Tiempo máximo de espera de la respuesta de imágenes (30–290 s) |
| `IMAGE_STORAGE_BACKEND` | `local` | `local` en Development; `vercel_blob` para Blob privado en Production |
| `IMAGE_STORAGE_PATH` | `backend/.data/images` | Carpeta local de imágenes en Development |
| `BLOB_READ_WRITE_TOKEN` | vacío | Token secreto del almacén Blob de Production; nunca en Angular ni Git |

`OPENAI_API_KEY` se lee solo en FastAPI; `OPENAI_IMAGE_MODEL` vacío usa `gpt-image-2`. Las migraciones locales hasta `0009_studio_attempts` ya están aplicadas: 0008 añade borradores temporales por cuenta y 0009 registra intentos para detectar interrupciones y evitar llamadas simultáneas al proveedor. En Development, los metadatos quedan en PostgreSQL y las imágenes usan disco local. En Production, las rutas de catálogos siguen respondiendo 503 hasta configurar explícitamente Blob privado ([guía de almacenamiento](docs/almacenamiento-imagenes.md)). La API sirve imágenes solo a la cuenta propietaria; las URL privadas del Blob no se envían al navegador. No hay secretos en Angular. Angular CLI no carga `.env` automáticamente: `environment.ts` contiene solo la ruta pública `/api` y `environment.development.ts` la sustituye mediante `fileReplacements`. En desarrollo el proxy de Angular dirige `/api/**` al backend local; en Vercel, `frontend/vercel.json` reescribe `/api` al backend público. El backend no abre una conexión a PostgreSQL para responder `/api/health`.

## Rutas

| Ruta | Estado |
| --- | --- |
| `/` | Inicio con conteos, investigaciones y actividad reales de la cuenta |
| `/login`, `/register` | Acceso a la cuenta y registro privado con invitación |
| `/explore` | Formulario que guarda búsquedas en FastAPI/PostgreSQL |
| `/analyses` | Historial real de búsquedas de la cuenta |
| `/analysis/:id` | Resultados de una investigación guardada si el ID es UUID; usa datos persistidos y consulta Mercado Libre solo bajo acción explícita |
| `/opportunity/saved/:id` | Producto observado y escenario financiero persistido para una investigación de tu cuenta |
| `/studio` | Generación real de imágenes con OpenAI; resultados temporales hasta descargar o crear catálogo |
| `/catalogs` | Galería de campañas reales guardadas por cuenta en Development |
| `/catalogs/:id` | Detalle, favoritos, descarga y generación adicional con OpenAI |
| `/profile` | Nombre y correo reales de la cuenta autenticada; permite cerrar sesión |
| Cualquier otra | Página 404 con retorno al Dashboard |

## Verificación

Backend:

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
python -m pip check
```

Las pruebas verifican salud, error 404, CORS, validación del contrato, modelo inicial, configuración de PostgreSQL, ambos adaptadores de productos con respuestas HTTP simuladas, edición de imágenes con respuesta OpenAI simulada, el parser CSV de Trends, ETL, variables descriptivas, clustering, forecasting con backtesting y score exploratorio. Con `ARBIGEN_TEST_DATABASE_URL` apuntando a una **base de pruebas migrada y separada** también verifican escritura/lectura, aislamiento entre cuentas autenticadas, importación de Trends, preparación del dataset, lectura analítica, escenarios financieros privados y agregados de Inicio con rollback. Las pruebas del proveedor no ejecutan el actor de Apify ni crean imágenes de pago.

Frontend:

```bash
cd frontend
npm run build
npm run test:simulator
npm run test:analysis
npm audit
```

El lockfile fija el árbol npm. Se incluye un override temporal de `piscina` a `5.3.2` para corregir `GHSA-67c8-pqhq-4rmx` en la dependencia de compilación de Angular. Retirarlo cuando Angular incorpore una versión corregida y volver a verificar build/audit. ECharts se importa de forma modular siguiendo su [guía oficial](https://echarts.apache.org/handbook/en/basics/import/) y solo se carga al abrir un análisis. Las pruebas del cálculo usan `node:test` y el soporte de TypeScript de Node 22, sin añadir dependencias.

El simulador calcula por unidad: comisión = precio × porcentaje, redondeada a centavos; costo total = producto + envío + otros gastos + comisión; ganancia = precio − costo total; margen = ganancia ÷ precio; ROI = ganancia ÷ costo total. El equilibrio busca el menor precio en centavos que cubre el costo con la comisión redondeada. Si un denominador es cero, muestra «—»; con comisión de 100 % y costos fijos positivos no hay precio de equilibrio finito. Impuestos, devoluciones y publicidad solo cuentan si se agregan a «Otros gastos». «Guardar escenario» persiste los importes de una investigación en PostgreSQL local y los recupera al recargar.

Prueba manual sugerida:

1. Abrir Inicio con FastAPI y PostgreSQL: debe mostrar los conteos y la actividad de las investigaciones de la cuenta, sin ROI ni score ficticios. Si el espacio está vacío, debe mostrar cero y una invitación a investigar.
2. Seleccionar «Últimos 7 días»: los conteos y la tabla deben corresponder a investigaciones creadas en ese periodo; la actividad usa la fecha de cada guardado, preparación o importación.
3. Iniciar PostgreSQL, aplicar `alembic upgrade head`, iniciar FastAPI en `:8000` y Angular con `npm start`. Abrir «Analizar producto». Enviar el formulario vacío o con espacios: debe explicar el mínimo de 3 caracteres y enfocar el campo.
4. Usar el ejemplo, elegir México, Joyería y 6 meses. Guardar: debe aparecer la confirmación y un enlace a una ficha con esos filtros; los indicadores sin datos deben mostrar cero o «—», nunca cifras ficticias.
5. Abrir Mis análisis: debe aparecer la nueva búsqueda. Recargar la página y volver a abrir la ficha: debe conservarse. Una búsqueda creada en otra cuenta no debe aparecer en ésta. En la ficha guardada, pulsar «Consultar y preparar» **solo si deseas hacer una consulta real que puede generar cargos en Apify**. Deben aparecer la muestra, el resumen ETL y las señales descriptivas. Si hay al menos ocho productos con precios variados y grupos suficientemente separados, también deben aparecer segmentos con tamaños y precios reales; de lo contrario, una explicación de datos insuficientes. Recargar: el dataset, las señales y los grupos deben seguir visibles sin otra consulta. Pulsar «Reprocesar datos guardados»: debe actualizar el dataset sin llamar a Apify. Descargar el JSON y ejecutar el cuaderno. Con la API oficial solo funciona MX y puede mostrarse catálogo sin precios ante un 403.
6. En Google Trends, exportar «Interés a lo largo del tiempo» con una sola palabra clave igual a la búsqueda guardada y el mismo país. En la ficha, sección «Interés de búsqueda», elegir «CSV de Google Trends» e «Importar CSV»: debe aparecer la gráfica y persistir tras recargar. Si contiene 16 o más puntos observados consecutivos de frecuencia regular y pasa el backtest, «Pronóstico validado» debe mostrar método, error y tres valores futuros; de otro modo debe explicar por qué no publica uno. Probar un CSV de otro término: debe mostrar un error y mantener la serie previa. Si el encabezado incluye país, uno distinto también debe rechazarse; si solo dice `Time`, la ficha debe advertir que no pudo verificarlo. Un valor `<1` debe conservarse como valor censurado, distinto de cero. En «Puntuación exploratoria», el score debe estar vacío hasta introducir los cinco valores del escenario; con muestra y pronóstico suficientes debe mostrar score, utilidad, margen y ROI, además de advertencias de calidad, procedencia, antigüedad y dos pruebas de estrés. Cambiar un peso y compensar otro modifica el score sin consultar Apify. Recargar borra solo la vista previa; un escenario guardado desde «Evaluar rentabilidad» permanece y alimenta la lectura inicial del score.
7. Desde una investigación con productos, abrir «Evaluar rentabilidad»: seleccionar una publicación y confirmar que su precio observado no rellena automáticamente el costo del proveedor. Introducir precio de venta y costos propios, guardar y recargar: deben conservarse el producto, los importes y la utilidad. Descargar el JSON, configurar `ARBIGEN_SCENARIO_PATH` y ejecutar el cuaderno. Cambiar la muestra mediante reprocesamiento no debe borrar la hipótesis guardada; la vista previa de score no debe sobrescribirla. Esta ruta no llama a Apify.
8. Abrir una investigación con productos guardados: el resumen y el gráfico de precios deben reflejar la misma muestra. Recargar no debe iniciar otra búsqueda ni cambiar los conteos. `/analysis/demo-rings` debe indicar que no existe una investigación con ese ID.
9. Detener FastAPI y repetir el guardado: debe aparecer un error de conexión. Reiniciar FastAPI y pulsar «Reintentar». «Nueva búsqueda» restaura los campos iniciales.
10. Abrir un catálogo guardado: no debe ofrecer un enlace a una oportunidad ficticia. «Nueva campaña» debe llevar el nombre del producto al Estudio.
11. Abrir `/opportunity/demo-rings`: debe mostrar la página 404. Desde una investigación guardada, «Evaluar rentabilidad» debe seguir abriendo su simulador real.
12. En el simulador de una investigación guardada, probar venta por debajo de costos, campo vacío, costo negativo y comisión mayor a 100 %. La pantalla debe mostrar pérdida o errores según corresponda. Con comisión 100 % y costos fijos positivos, el equilibrio no existe. «Borrar valores» limpia los campos sin alterar el escenario guardado.
13. Abrir `/opportunity/saved/no-existe`: debe aparecer «Investigación no encontrada». La antigua `/opportunity/no-existe` debe mostrar 404.
14. Desde un catálogo abrir «Nueva campaña» y comprobar que aparece el nombre del producto en el Estudio. Subir un PNG, JPEG o WebP menor de 10 MB; el original debe verse a la izquierda sin modificaciones.
15. Con una clave de OpenAI válida y aceptando el posible cargo, cambiar estilo, escenario, iluminación, formato y número de variaciones. Pulsar «Generar imágenes»: aparecen 1–4 imágenes nuevas basadas en la foto. Probar selección y «Descargar PNG». No repetir generaciones solo para verificar la interfaz.
16. Durante la carga mantener la pantalla abierta. Cambiar una opción o la fotografía después de generar: los resultados anteriores deben desaparecer. Probar un archivo inválido o mayor de 10 MB; debe mostrarse el error sin llamar a OpenAI.
17. En Estudio IA, marcar una vista y pulsar «Crear catálogo»: el detalle debe contener solo esa vista generada y la fotografía original. Repetir sin marcar vistas: deben entrar todas. Recargar y comprobar que el catálogo sigue en la cuenta local. Desde «Evaluar rentabilidad», seleccionar un producto y abrir Estudio IA: el nombre debe aparecer precargado. Al guardar una nueva campaña, el detalle debe mostrar el producto de origen y un enlace a su investigación; abrirla no ejecuta Apify ni OpenAI, pero generar una imagen sí puede generar un cargo.
18. En `/catalogs`, buscar un producto y comprobar el estado vacío con un término desconocido. Abrir una campaña creada, cambiar un favorito y descargar una vista. Añadir o regenerar una variación solo si se acepta otra solicitud de pago a OpenAI. El límite es cuatro vistas por catálogo.
19. Eliminar un catálogo y usar «Deshacer». Recargar: el catálogo debe seguir guardado con favoritos y fotografías.
20. Navegar por todas las opciones del sidebar, recargar una ruta interna y probar una dirección desconocida.
21. Reducir el ancho a móvil, abrir/cerrar el menú y desplazar horizontalmente la tabla. Los gráficos, el simulador, el Estudio y Mis catálogos deben caber sin desbordamiento.
22. Navegar con Tab; probar «Saltar al contenido» y Escape para cerrar el menú.
23. Iniciar la API y comprobar `/api/health` y `/docs`.

El estado de carga de Inicio aparece al cambiar de periodo. Las ramas vacía y error responden a PostgreSQL real. El Explorador informa errores de conexión o base de datos y permite reintentar. Guardar una investigación no inicia todavía un trabajo analítico.

## Pendiente y siguiente paso

La estructura PostgreSQL, las búsquedas guardadas, los contratos `MarketplaceSearchProvider` y `TrendsProvider`, el modelo `MarketplaceProduct`, los adaptadores Apify/oficial, el importador CSV, el ETL, las variables descriptivas, la segmentación, el pronóstico validado y el score exploratorio ya existen. El token oficial local funciona para `/users/me` y `/products/search`, pero `/sites/MLM/search` responde 403. Con autorización específica se ejecutó una consulta del actor de Karamelo para «juguetes de bebe» en MX, una página y `maxItems=12`: quedaron 12 productos depurados; el clustering agrupó 11 en dos segmentos e informó un precio atípico excluido solo del ajuste. La investigación local tiene ahora 273 puntos mensuales importados del CSV `Time` facilitado por el usuario (enero de 2004 a septiembre de 2026); el pronóstico validado eligió el método estacional ingenuo. El país no es verificable dentro de ese formato, como indica la ficha. Colombia y Argentina están cubiertos por pruebas HTTP simuladas, todavía no por una ejecución real del actor. El límite de 200 es un máximo, no una garantía de que el actor devuelva exactamente 200 productos. Cada pulsación de «Consultar y preparar» o «Actualizar y preparar» inicia otra ejecución del actor y puede generar cargos; reprocesar, descargar el JSON, abrir el cuaderno o calcular un escenario no inicia búsquedas. Siguen pendientes recuperación de cuenta, MFA, protección persistente contra intentos masivos, análisis de mercado más amplio, mediciones independientes de demanda y competencia. El adaptador de Blob privado para Production está implementado y probado con un servicio simulado; falta configurarlo y verificarlo al desplegar. Los catálogos cuentan con persistencia local por cuenta; el recorrido de lectura y favoritos ya se validó en el navegador. El usuario validó el nuevo recorrido de subida, generación y catálogo en Development. La recuperación de intentos interrumpidos se probó con respuestas simuladas, sin otra llamada a OpenAI.

El backend usa una entrada reconocible por Vercel, conexiones perezosas y migraciones externas al ciclo de vida de la Function. Neon `neon-bole-cave` (rama `main`, base `neondb`) y la base local `arbigen` están en la migración 0009. Neon conserva la cuenta de Production, sin investigaciones, productos ni Trends locales. `frontend/vercel.json` configura la salida Angular, la reescritura de `/api` y el fallback SPA. El código publicado en Production sigue en `main`; los cambios de Development están en una rama local hasta su publicación. [Arbigen web](https://arbigen-web.vercel.app/) responde en Production; `/api/health` y las rutas protegidas de `/api/v1/` pasan mediante su proxy hacia [Arbigen API](https://arbigen-api.vercel.app/api/health). La investigación local histórica ya pertenece a la cuenta registrada en Development; el UUID demo de localStorage no concede acceso.

**Siguiente paso propuesto:** programar la limpieza de borradores temporales en Development y revisar los controles de acceso antes del despliegue. Antes de publicar habrá que migrar Neon a 0009, habilitar Blob privado en Production y programar allí la limpieza de borradores vencidos.

Ver [arquitectura e inventario de archivos](docs/architecture.md).
