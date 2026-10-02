# Arbigen · Trend2Catalog AI

Plataforma de inteligencia de mercado y creación de catálogos para e-commerce, construida por slices. **Alcance actual: fases 0–17. Inicio usa investigaciones, productos depurados, series de Trends y actividad guardados en PostgreSQL; el pipeline conserva la búsqueda bajo demanda, ETL, segmentación, pronóstico y score exploratorio. El despliegue en Vercel está preparado, pendiente de publicar el código y conectar PostgreSQL alojado.**

## Implementado

- Monorepo con Angular 21 (standalone, TypeScript estricto, Router, HttpClient y SCSS) y FastAPI.
- Sidebar, header, navegación responsive, títulos por ruta y página 404.
- Inicio con cuatro conteos reales, investigaciones recientes y actividad registrada en PostgreSQL, aislados por el espacio de este navegador. El selector de 7/30 días filtra por fecha de creación; la actividad filtra por fecha de cada evento. Hay estados de carga, error con reintento y vacío.
- Explorador con palabra clave, país, categoría opcional y periodo. Valida y guarda la investigación mediante FastAPI en PostgreSQL; muestra un error recuperable si la API no está disponible.
- Mis análisis lista investigaciones guardadas para el identificador demo de este navegador y permite abrir una ficha con los parámetros registrados. Desde cada ficha se puede consultar y guardar una muestra de productos de Mercado Libre, limitada por `MAX_PRODUCTS_PER_ANALYSIS` (200 por defecto), e importar una serie de Google Trends para el mismo término y país. El ETL muestra cuántos productos conservó y por qué excluyó otros.
- Resultado de análisis con cinco KPIs, cinco gráficos ECharts, tres segmentos de ejemplo y cluster recomendado. Hay fixtures para anillos, lámparas y vasos; una búsqueda sin fixture muestra un estado vacío con acceso al ejemplo.
- Detalle de oportunidad para anillos, lámparas, vasos y bolsos, con segmento, características, variables y productos similares ficticios. Simulador reactivo por unidad con cinco entradas, validación, costo total, comisión, ganancia, margen, ROI y precio de equilibrio.
- Estudio IA mock con fotografía local, configuración de campaña, espera cancelable, 1–4 vistas previas, regeneración, selección y descarga PNG. Las vistas son recortes y filtros de la imagen original; el escenario todavía no se aplica.
- Mis catálogos con dos campañas de ejemplo ilustradas, búsqueda, filtros, detalle, favoritos, descarga, generación de una vista local, regeneración y eliminación reversible. Desde Estudio IA se puede crear un catálogo con las vistas seleccionadas o, si no hay selección, con todas.
- Placeholders informativos para las pantallas posteriores.
- `GET /api/health`, configuración por entorno, errores JSON centralizados y pruebas de API.
- SQLAlchemy y Alembic con ocho entidades iniciales y migración PostgreSQL. La entrada `backend/index.py` permite que Vercel detecte FastAPI al usar `backend/` como raíz del proyecto.
- `POST /api/v1/analyses`, `GET /api/v1/analyses` paginado y `GET /api/v1/analyses/{id}` con validación, separación entre espacios demo y respuestas sin métricas inventadas.
- La búsqueda de productos depende de `MarketplaceSearchProvider`, no de Apify ni de campos de un actor. Con `APIFY_API_TOKEN` configurado, `auto` usa el actor de Karamelo para MX/CO/AR; sin él conserva la API oficial mexicana y su fallback de catálogo. Los tokens quedan solo en FastAPI y se guarda una muestra normalizada, nunca la respuesta cruda del actor.
- `GET/POST /api/v1/analyses/{id}/trends` lee e importa un CSV de Google Trends mediante `TrendsProvider`. Se validan término, fechas e índice; el país se valida cuando figura dentro del encabezado. La serie normalizada queda en PostgreSQL, no el archivo. `<1` se conserva como valor censurado, distinto de cero.
- `POST /api/v1/analyses/{id}/dataset/refresh` consulta el proveedor una vez, guarda la muestra normalizada en `marketplace_snapshots` y los productos depurados en `products`. `GET /dataset` lee esos datos sin consulta externa; `POST /dataset/reprocess` aplica de nuevo el ETL a la muestra guardada sin gasto de extracción. Trends se incorpora a la vista analítica conservando sus valores censurados.
- `GET /api/v1/analyses/{id}/features` calcula sobre el dataset guardado cobertura y distribución de precios, pistas de material, cobertura/volatilidad de Trends, media móvil, crecimiento, momentum y aceleración cuando hay ventanas válidas. No consulta proveedores; devuelve `null` si no hay evidencia suficiente. La ficha guardada muestra estas señales y exporta el dataset como JSON para el cuaderno reproducible [arbigen_ciencia_de_datos.ipynb](notebooks/arbigen_ciencia_de_datos.ipynb).
- `GET /api/v1/analyses/{id}/clusters` calcula grupos reproducibles sobre productos depurados ya guardados, sin consultar Apify. Usa K-Means determinista con precio normalizado y pistas de material de menor peso; compara 2–4 grupos por silueta, exige muestra y separación mínimas y muestra tamaño, precios y ejemplos de cada grupo. No elige un grupo recomendado sin evidencia comercial.
- `GET /api/v1/analyses/{id}/forecast` lee solo Trends persistido y compara baselines mediante backtesting cronológico de tres pasos. Publica método, errores, dirección reciente y tres valores del índice con un rango orientativo únicamente si hay al menos 16 puntos regulares y el error validado no supera 20 puntos; de otro modo explica por qué no hay pronóstico.
- `GET /api/v1/analyses/{id}/opportunity-score` explica qué evidencia falta y devuelve `score: null` sin supuestos financieros. `POST /api/v1/analyses/{id}/opportunity-score/preview` calcula una vista previa con precio, costos y pesos aportados por el usuario, sin guardar esos importes ni consultar Apify. La ficha guardada contiene el formulario y la descomposición del resultado.
- `GET /api/v1/dashboard?days=7|30` agrega investigaciones, muestras, productos con precio y series importadas del espacio del navegador; devuelve hasta cinco investigaciones recientes y seis eventos reales. No ejecuta proveedores externos ni inventa ROI, score o competencia.

**Los productos y métricas de mercado de las rutas demo de análisis y oportunidad son ficticios; Inicio ya no usa fixtures.** Los parámetros que se envían desde el Explorador se guardan en PostgreSQL. La ficha guardada puede consultar datos actuales de Mercado Libre si el proveedor configurado admite el país. Una publicación puede incluir precio y enlace; un producto de catálogo no incluye ninguno de los dos y se identifica como tal. La muestra y el dataset depurado no son volumen de ventas ni una medida de demanda, competencia o tamaño de mercado. La categoría y el periodo guardados aún no filtran esa consulta. La serie importada de Google Trends es un índice relativo de interés, no ventas ni búsquedas absolutas; el periodo elegido tampoco se verifica automáticamente contra el CSV. El ROI, margen y score de los análisis de ejemplo son valores fijos de fixtures; no provienen del ETL. El detalle demo y la ficha guardada calculan resultados financieros a partir de entradas editables, aunque solo la ficha guardada combina las señales calculadas con esos supuestos. La proyección de las rutas demo es una serie escrita a mano; el pronóstico de la ficha guardada se calcula y valida sobre Trends. Los segmentos de las rutas demo se definieron manualmente; los de investigaciones guardadas se calculan con los productos disponibles.

El Estudio IA y Mis catálogos funcionan completamente en el navegador. No envían fotografías a FastAPI ni a terceros, ni generan imágenes con IA. «Guardar» selecciona vistas para crear un catálogo demo. Las campañas y cambios viven solo en memoria de la pestaña y desaparecen al recargar. Las dos campañas iniciales usan ilustraciones SVG ficticias. Las campañas nuevas y las vistas regeneradas son recortes y filtros locales de la imagen original; la descarga exporta el archivo mostrado.

## Requisitos

- Node.js 22.12+ de la rama 22 (verificado con 22.13.0), npm 11.
- Python 3.11+ con `venv` y `pip`.
- Las fichas de ejemplo, Estudio IA, catálogos mock y `/api/health` funcionan sin base de datos. Inicio, Explorador y Mis análisis requieren FastAPI y PostgreSQL.

Se eligió Angular 21 por su compatibilidad con el Node instalado. La [matriz oficial de Angular](https://angular.dev/reference/versions) documenta las versiones admitidas.

## Levantar frontend

Desde la raíz del repositorio:

```bash
cd frontend
npm ci
npm start
```

Abrir [http://localhost:4200](http://localhost:4200). `npm start` usa `frontend/proxy.conf.json` para dirigir `/api` a FastAPI en `127.0.0.1:8000`; inicia también backend y PostgreSQL para ver Inicio y guardar búsquedas.

```bash
npm run build
```

La compilación de producción queda en `frontend/dist/arbigen/browser/`.

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

El primer `POST /api/v1/analyses` crea un usuario interno ficticio para el identificador UUID guardado en `localStorage` por el navegador. El header `X-Demo-Workspace-ID` separa los registros de esta demo, pero **no es autenticación ni autorización segura**. No se deben guardar datos personales o sensibles en estas investigaciones. Reemplazaremos este mecanismo por cuentas reales antes del despliegue público.

La ficha guardada llama a `POST /api/v1/analyses/{id}/dataset/refresh` solo al pulsar «Consultar y preparar». El servicio pide hasta `MAX_PRODUCTS_PER_ANALYSIS` (200 por defecto) a `MarketplaceSearchProvider` y recibe exclusivamente `MarketplaceProduct` internos: ID, título, precio y moneda opcionales, enlace e imagen HTTPS opcionales. El adaptador Apify usa el [actor de Karamelo](https://apify.com/karamelo/mercadolibre-scraper-espanol-castellano) con `keyword`, la URL de listado de México, Colombia o Argentina según el análisis, hasta `APIFY_MAX_PAGES` (4 por defecto), sin anuncios patrocinados ni páginas de detalle. La API de Apify recibe `maxItems` como tope de resultados facturables y `limit` como tope de respuesta; el backend vuelve a limitar la muestra y el ETL deduplica para el dataset. La ejecución síncrona tiene timeout configurable (120 segundos por defecto). Si no se configura Apify, el adaptador oficial solo admite México: intenta `/sites/MLM/search` y, ante 403, `/products/search`; sus endpoints devuelven una muestra menor, de hasta 20 elementos. La respuesta indica `source: listings` o `source: catalog`; el catálogo no contiene precios ni enlaces de publicaciones. [Apify documenta el endpoint síncrono y sus límites](https://docs.apify.com/api/v2/actor-run-sync-get-dataset-items-post).

El ETL trabaja solo sobre `MarketplaceProduct` y `TrendObservation`. Guarda la muestra normalizada del proveedor en `marketplace_snapshots`, sin JSON específico de Apify, y el dataset de productos con precio válido en `products`. Normaliza espacios, entidades HTML y Unicode de títulos; deduplica por ID; redondea precios a dos decimales en la moneda del país; excluye precios ausentes, inválidos o con moneda incorrecta; y extrae pistas de material del título, marcadas como no verificadas. No convierte MXN/COP/ARS entre sí porque no hay una fuente de tipos de cambio. Los productos de catálogo sin precio permanecen en la muestra, pero no entran en cálculos de precio o clustering. Los puntos de Trends, incluidos `<1`, se incluyen en la lectura analítica sin imputaciones. `POST /dataset/reprocess` permite repetir estas reglas sobre la muestra guardada sin llamar a Apify. Variables descriptivas, grupos, pronóstico y score exploratorio se calculan al leer datos guardados; los importes del escenario se aportan al cálculo y no se persisten.

La segmentación exige al menos ocho productos con precio, cuatro precios distintos y una amplitud de precios de 15 % respecto a la mediana. Una regla de Tukey puede dejar fuera del **ajuste** precios atípicos si representan como máximo el 10 % y quedan al menos ocho productos; el reporte informa cuántos se excluyeron, sin borrarlos del dataset. Estandariza `log(1 + precio)`, incorpora pistas de material con peso 0,35, ajusta K-Means de 2–4 grupos con inicialización determinista y solo devuelve grupos de al menos dos productos y silueta media ≥ 0,20. El máximo de entrada sigue siendo `MAX_PRODUCTS_PER_ANALYSIS` (200 por defecto). La silueta mide separación interna de la muestra, no demanda ni potencial comercial. Los grupos se recalculan al abrir la ficha y no se persisten en `clusters`; no se recomienda ninguno por ahora. No se requieren embeddings, PCA ni nuevas dependencias en esta fase.

El pronóstico compara último valor, media de tres, tendencia lineal y patrón estacional ingenuo cuando existen dos ciclos. Valida un horizonte de tres puntos con al menos seis orígenes cronológicos y selecciona por MAE. Exige al menos 16 observaciones recientes consecutivas, frecuencia regular y MAE ≤ 20 puntos del índice. Los valores `<1` no se imputan: solo se usa la secuencia posterior al último censurado. El rango orientativo usa errores retrospectivos por horizonte y un piso de cinco puntos; no es un intervalo de confianza garantizado. El índice y el rango se limitan a 0–100. Un pronóstico de Trends no representa ventas, volumen absoluto ni Opportunity Score.

La fórmula `exploratory-v1` usa crecimiento reciente de Trends (`clip(50 + crecimiento %)`) y estabilidad del pronóstico (`clip(100 − 5 × MAE)`), más margen (`clip(2,5 × margen %)`) y ROI (`clip(ROI %)`) calculados por unidad; cada componente se limita a 0–100. Los pesos por defecto son 0,25/0,15/0,35/0,25 y pueden cambiarse siempre que sumen 1. Una pérdida da score cero. Se exigen ocho productos con precio, crecimiento 3 contra 3, pronóstico validado, precio y costos explícitos y ROI definido; si falta algo, `score` es `null`. Se trata de una escala provisional sin calibración comercial: **no contiene demanda absoluta, ventas ni competencia medida**. Los impuestos, devoluciones y publicidad solo cuentan si el usuario los introduce en «Otros costos». Los resultados del escenario no se guardan y no requieren migración.

Para importar Trends, abre la ficha guardada, exporta desde [Google Trends](https://trends.google.com/trends/) el gráfico «Interés a lo largo del tiempo» para la misma palabra clave y país, con una sola serie, y elige el CSV en la ficha. El archivo debe ser UTF-8 y medir hasta 256 KB. Se admiten encabezados `Day/Week/Month, término: (país)` y `Time, término` con fechas ISO. La API valida término, fechas únicas y valores de 0 a 100 o `<1`; cuando el encabezado declara un país, también lo verifica. El formato `Time` **no incluye la geografía dentro del CSV**, por lo que se guarda con procedencia `google_trends_csv_geo_unverified` y la ficha advierte que debes confirmar el país elegido al exportar. El nombre del archivo tampoco prueba la geografía. La importación reemplaza atómicamente la serie previa. No consulta Google ni Apify al abrir la ficha. `pytrends` no se incluye: su repositorio está [archivado](https://github.com/GeneralMills/pytrends) y es una interfaz no oficial; la [API oficial](https://developers.google.com/search/apis/trends) sigue con acceso alfa. `TrendsProvider` permite añadir otro adaptador posteriormente.

## Cuaderno de ciencia de datos

El archivo [notebooks/arbigen_ciencia_de_datos.ipynb](notebooks/arbigen_ciencia_de_datos.ipynb) reúne en una sola secuencia la procedencia de fuentes, el ETL, la ingeniería de variables, el clustering, el backtesting, el score exploratorio y sus límites. Seguirá creciendo con las próximas fases de ciencia de datos. En una ficha guardada pulsa «Descargar JSON para notebook» y guarda el archivo como `notebooks/data/dataset.json`. Esta carpeta se ignora en Git; no hace falta crear datos ficticios ni repetir una consulta a Apify. También puedes establecer `ARBIGEN_DATASET_PATH` con una ruta absoluta a otro archivo exportado.

Para abrirlo desde la raíz del proyecto, con el entorno del backend activo, instala Jupyter en ese entorno si no lo tienes y ejecuta:

```bash
cd backend
source .venv/bin/activate
python -m pip install jupyterlab ipykernel
cd ../notebooks
jupyter lab arbigen_ciencia_de_datos.ipynb
```

El cuaderno importa `prepare_dataset`, `calculate_features`, `cluster_products`, `forecast_trends` y `calculate_score` del backend: no mantiene fórmulas paralelas. No pide tokens, no conecta con PostgreSQL y no genera cargos. Si solo has importado Trends, también puedes exportar y analizar esa serie; el clustering y el score informarán qué falta. Para estudiar un escenario financiero y su sensibilidad al precio, crea un JSON local con `sale_price`, `product_cost`, `shipping_cost`, `commission_pct` y `other_costs`, y apunta `ARBIGEN_SCENARIO_PATH` a su ruta absoluta antes de abrir el cuaderno.

Para un ensayo integral en una base local dedicada, configura `ARBIGEN_TEST_DATABASE_URL` con su conexión y ejecuta `python -m pytest -q`. La prueba hace rollback de sus inserciones. Consulta la [guía de Vercel y PostgreSQL](docs/vercel-database.md).

## Configuración

`backend/.env.example` es la referencia ejecutable; el `.env.example` raíz documenta las variables previstas para el proyecto. `Settings` lee `backend/.env` y permite sobrescribirlo con variables del proceso.

| Variable activa | Valor predeterminado | Uso |
| --- | --- | --- |
| `APP_NAME` | `Arbigen API` | Nombre de la API |
| `ENVIRONMENT` | `development` | `development`, `test` o `production` |
| `CORS_ORIGINS` | `["http://localhost:4200"]` | Lista JSON de orígenes permitidos |
| `DATABASE_URL` | vacío | URL de PostgreSQL para FastAPI; preferiblemente endpoint agrupado en Vercel |
| `DATABASE_MIGRATION_URL` | vacío | URL directa para Alembic; si falta, usa `DATABASE_URL` |
| `MERCADO_LIBRE_ACCESS_TOKEN` | vacío | Token para la API oficial de respaldo; nunca se envía a Angular |
| `MARKETPLACE_SEARCH_PROVIDER` | `auto` | `auto`, `apify` o `mercado_libre`; `auto` usa Apify si hay token |
| `MAX_PRODUCTS_PER_ANALYSIS` | `200` | Máximo interno de productos por consulta (1–1000) |
| `APIFY_API_TOKEN` | vacío | Token privado para el actor de Apify |
| `APIFY_ACTOR_ID` | `karamelo/mercadolibre-scraper-espanol-castellano` | Actor seleccionado; su contrato se traduce en el adaptador |
| `APIFY_MAX_PAGES` | `4` | Máximo de páginas que procesa el actor (1–50) |
| `APIFY_REQUEST_TIMEOUT_SECONDS` | `120` | Timeout de la ejecución síncrona (10–290 s) |

Las variables de OpenAI y storage siguen reservadas y vacías. No hay secretos en Angular. Angular CLI no carga `.env` automáticamente; el archivo de ejemplo del frontend explica esta limitación. En desarrollo Angular usa el proxy `/api`; en Vercel, `frontend/vercel.json` reescribe `/api` al backend público. El backend no abre una conexión a PostgreSQL para responder `/api/health`.

## Rutas

| Ruta | Estado |
| --- | --- |
| `/` | Inicio con conteos, investigaciones y actividad reales del espacio local |
| `/explore` | Formulario que guarda búsquedas en FastAPI/PostgreSQL |
| `/analyses` | Historial real de búsquedas del espacio demo de este navegador |
| `/analysis/:id` | Ficha persistida si el ID es UUID, con consulta bajo demanda a Mercado Libre; resultado mock para `demo-rings`, `demo-lamps` y `demo-cups` |
| `/opportunity/:id` | Detalle y simulador para `demo-rings`, `demo-lamps`, `demo-cups` y `demo-bags`; estado vacío en otros casos |
| `/studio` | Estudio IA mock interactivo, sin generación ni persistencia real |
| `/catalogs` | Galería mock con dos ejemplos y campañas creadas durante la sesión |
| `/catalogs/:id` | Detalle, favoritos, descarga y acciones locales de la campaña |
| `/settings` | Placeholder de preferencias |
| `/profile` | Perfil demo informativo |
| Cualquier otra | Página 404 con retorno al Dashboard |

## Verificación

Backend:

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
python -m pip check
```

Las pruebas verifican salud, error 404, CORS, validación del contrato, modelo inicial, configuración de PostgreSQL, ambos adaptadores de productos con respuestas HTTP simuladas, el parser CSV de Trends, ETL, variables descriptivas, clustering, forecasting con backtesting y score exploratorio. Con `ARBIGEN_TEST_DATABASE_URL` apuntando a una **base de pruebas migrada y separada** también verifican escritura/lectura, aislamiento entre UUID demo, importación de Trends, preparación del dataset, lectura analítica y agregados de Inicio con rollback. Las pruebas del proveedor no ejecutan el actor de Apify.

Frontend:

```bash
cd frontend
npm run build
npm run test:simulator
npm audit
```

El lockfile fija el árbol npm. Se incluye un override temporal de `piscina` a `5.3.2` para corregir `GHSA-67c8-pqhq-4rmx` en la dependencia de compilación de Angular. Retirarlo cuando Angular incorpore una versión corregida y volver a verificar build/audit. ECharts se importa de forma modular siguiendo su [guía oficial](https://echarts.apache.org/handbook/en/basics/import/) y solo se carga al abrir un análisis. Las pruebas del cálculo usan `node:test` y el soporte de TypeScript de Node 22, sin añadir dependencias.

El simulador calcula por unidad: comisión = precio × porcentaje; costo total = producto + envío + otros gastos + comisión; ganancia = precio − costo total; margen = ganancia ÷ precio; ROI = ganancia ÷ costo total; equilibrio = costos fijos ÷ (1 − porcentaje de comisión), redondeado al centavo superior. Si un denominador es cero, muestra «—»; con comisión de 100 % y costos fijos positivos no hay precio de equilibrio finito. Impuestos, devoluciones y publicidad solo cuentan si se agregan a «Otros gastos». Los valores editados viven en memoria de la página y se restablecen al recargar.

Prueba manual sugerida:

1. Abrir Inicio con FastAPI y PostgreSQL: debe mostrar los conteos y la actividad de las investigaciones de este navegador, sin ROI ni score ficticios. Si el espacio está vacío, debe mostrar cero y una invitación a investigar.
2. Seleccionar «Últimos 7 días»: los conteos y la tabla deben corresponder a investigaciones creadas en ese periodo; la actividad usa la fecha de cada guardado, preparación o importación.
3. Iniciar PostgreSQL, aplicar `alembic upgrade head`, iniciar FastAPI en `:8000` y Angular con `npm start`. Abrir «Analizar producto». Enviar el formulario vacío o con espacios: debe explicar el mínimo de 3 caracteres y enfocar el campo.
4. Usar el ejemplo, elegir México, Joyería y 6 meses. Guardar: debe aparecer la confirmación y un enlace a una ficha con esos filtros, sin KPIs de mercado.
5. Abrir Mis análisis: debe aparecer la nueva búsqueda. Recargar la página y volver a abrir la ficha: debe conservarse. Una búsqueda creada en otro navegador demo no debe aparecer en éste. En la ficha guardada, pulsar «Consultar y preparar» **solo si deseas hacer una consulta real que puede generar cargos en Apify**. Deben aparecer la muestra, el resumen ETL y las señales descriptivas. Si hay al menos ocho productos con precios variados y grupos suficientemente separados, también deben aparecer segmentos con tamaños y precios reales; de lo contrario, una explicación de datos insuficientes. Recargar: el dataset, las señales y los grupos deben seguir visibles sin otra consulta. Pulsar «Reprocesar datos guardados»: debe actualizar el dataset sin llamar a Apify. Descargar el JSON y ejecutar el cuaderno. Con la API oficial solo funciona MX y puede mostrarse catálogo sin precios ante un 403.
6. En Google Trends, exportar «Interés a lo largo del tiempo» con una sola palabra clave igual a la búsqueda guardada y el mismo país. En la ficha, sección «Interés de búsqueda», elegir «CSV de Google Trends» e «Importar CSV»: debe aparecer la gráfica y persistir tras recargar. Si contiene 16 o más puntos observados consecutivos de frecuencia regular y pasa el backtest, «Pronóstico validado» debe mostrar método, error y tres valores futuros; de otro modo debe explicar por qué no publica uno. Probar un CSV de otro término: debe mostrar un error y mantener la serie previa. Si el encabezado incluye país, uno distinto también debe rechazarse; si solo dice `Time`, la ficha debe advertir que no pudo verificarlo. Un valor `<1` debe conservarse como valor censurado, distinto de cero. En «Puntuación exploratoria», el score debe estar vacío hasta introducir los cinco valores del escenario; con muestra y pronóstico suficientes debe mostrar score, utilidad, margen y ROI. Cambiar un peso y compensar otro modifica el score sin consultar Apify. Recargar borra los supuestos.
7. Abrir `/analysis/demo-rings`: deben aparecer los cinco KPIs, cinco gráficos y el cluster ficticio «Minimalista / Plata / Ajustable». Es una ruta de ejemplo separada de los registros persistidos.
8. Detener FastAPI y repetir el guardado: debe aparecer un error de conexión. Reiniciar FastAPI y pulsar «Reintentar». «Nueva búsqueda» restaura los campos iniciales.
9. Abrir `demo-lamps` y `demo-cups` desde sus URL; deben mostrar sus propios datos. «Ver oportunidad» abre su detalle. `demo-bags` queda disponible por URL mientras esas rutas de ejemplo existan.
10. En `/opportunity/demo-rings`, comprobar valores iniciales: comisión 63, costo total 290, ganancia 130, margen 31,0 %, ROI 44,8 % y equilibrio 267,06 MXN. Cambiar precio o costos y verificar que se recalculen al instante.
11. Probar venta por debajo de costos, campo vacío, costo negativo y comisión mayor a 100 %. La pantalla debe mostrar pérdida o errores según corresponda. Con comisión 100 %, el equilibrio no existe. «Restablecer ejemplo» restaura los cinco campos.
12. Abrir `/opportunity/no-existe`: debe aparecer el estado vacío.
13. Desde un detalle abrir «Abrir Estudio IA» y comprobar que aparece el nombre del producto. Subir un PNG, JPEG o WebP menor de 10 MB; el original debe verse a la izquierda sin modificaciones.
14. Cambiar estilo, escenario, iluminación, formato y número de variaciones. Pulsar «Preparar vistas previas»: aparece carga simulada y luego 1–4 recortes filtrados del original. Probar «Regenerar demo», «Guardar» y «Descargar PNG».
15. Durante la carga usar «Cancelar». Cambiar una opción o la fotografía después de generar: los resultados anteriores deben desaparecer. Probar un archivo inválido o mayor de 10 MB; debe mostrarse el error.
16. En Estudio IA, marcar una vista y pulsar «Crear catálogo demo»: el detalle debe contener solo esa vista y la fotografía original. Volver a Mis catálogos y comprobar la campaña nueva en el filtro «Esta sesión». Repetir sin marcar vistas: deben entrar todas.
17. En `/catalogs`, buscar un producto y comprobar el estado vacío con un término desconocido. Abrir una campaña de ejemplo, cambiar un favorito, descargar una vista, generar una nueva variación y regenerar otra. El límite es cuatro vistas por catálogo.
18. Eliminar un catálogo y usar «Deshacer». Recargar: deben restablecerse las campañas de ejemplo y desaparecer los cambios y las campañas creadas durante la sesión.
19. Navegar por todas las opciones del sidebar, recargar una ruta interna y probar una dirección desconocida.
20. Reducir el ancho a móvil, abrir/cerrar el menú y desplazar horizontalmente la tabla. Los gráficos, el simulador, el Estudio y Mis catálogos deben caber sin desbordamiento.
21. Navegar con Tab; probar «Saltar al contenido» y Escape para cerrar el menú.
22. Iniciar la API y comprobar `/api/health` y `/docs`.

El estado de carga de Inicio aparece al cambiar de periodo. Las ramas vacía y error responden a PostgreSQL real. El Explorador informa errores de conexión o base de datos y permite reintentar. Guardar una investigación no inicia todavía un trabajo analítico.

## Pendiente y siguiente paso

La estructura PostgreSQL, las búsquedas guardadas, los contratos `MarketplaceSearchProvider` y `TrendsProvider`, el modelo `MarketplaceProduct`, los adaptadores Apify/oficial, el importador CSV, el ETL, las variables descriptivas, la segmentación, el pronóstico validado y el score exploratorio ya existen. El token oficial local funciona para `/users/me` y `/products/search`, pero `/sites/MLM/search` responde 403. Con autorización específica se ejecutó una consulta del actor de Karamelo para «juguetes de bebe» en MX, una página y `maxItems=12`: quedaron 12 productos depurados; el clustering agrupó 11 en dos segmentos e informó un precio atípico excluido solo del ajuste. La investigación local tiene ahora 273 puntos mensuales importados del CSV `Time` facilitado por el usuario (enero de 2004 a septiembre de 2026); el pronóstico validado eligió el método estacional ingenuo. El país no es verificable dentro de ese formato, como indica la ficha. Colombia y Argentina están cubiertos por pruebas HTTP simuladas, todavía no por una ejecución real del actor. El límite de 200 es un máximo, no una garantía de que el actor devuelva exactamente 200 productos. Cada pulsación de «Consultar y preparar» o «Actualizar y preparar» inicia otra ejecución del actor y puede generar cargos; reprocesar, descargar el JSON, abrir el cuaderno o calcular un escenario no inicia búsquedas. Siguen pendientes autenticación real, análisis de mercado más amplio, mediciones independientes de demanda y competencia, conexión de las demás pantallas con la API, generación de imágenes con IA y almacenamiento externo. Los catálogos de campañas todavía viven solo en memoria del navegador.

El backend usa una entrada reconocible por Vercel, conexiones perezosas y migraciones externas al ciclo de vida de la Function. La migración 0003 se aplicó a la base local `arbigen`. `frontend/vercel.json` configura la salida Angular, la reescritura de `/api` y el fallback SPA. El código está publicado en el repositorio privado y `/api/health` responde en `arbigen-api.vercel.app`; falta crear PostgreSQL alojado y aplicar las migraciones antes de validar las rutas de datos. El UUID en localStorage sigue siendo aislamiento demo, no autenticación segura.

**Siguiente paso propuesto:** terminar la publicación en Vercel y conectar PostgreSQL alojado; después sustituir las rutas de análisis y oportunidad de ejemplo por datos persistidos donde ya exista evidencia.

Ver [arquitectura e inventario de archivos](docs/architecture.md).
