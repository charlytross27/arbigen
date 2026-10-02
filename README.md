# Arbigen · Trend2Catalog AI

Plataforma de inteligencia de mercado y creación de catálogos para e-commerce, construida por slices. **Alcance actual en Development: fases 0–20. Inicio y resultados usan investigaciones, productos depurados y series de Trends guardados en PostgreSQL; el pipeline conserva la búsqueda bajo demanda, ETL, segmentación, pronóstico y score exploratorio. Hay una versión anterior desplegada en Vercel con PostgreSQL alojado en Neon; los cambios recientes siguen solo en Development.**

## Implementado

- Monorepo con Angular 21 (standalone, TypeScript estricto, Router, HttpClient y SCSS) y FastAPI.
- Sidebar, header, navegación responsive, títulos por ruta y página 404.
- Inicio con cuatro conteos reales, investigaciones recientes y actividad registrada en PostgreSQL, aislados por la cuenta autenticada. El selector de 7/30 días filtra por fecha de creación; la actividad filtra por fecha de cada evento. Hay estados de carga, error con reintento y vacío.
- Registro privado con código de invitación, inicio y cierre de sesión. La API autoriza cada investigación por usuario; el header demo y el UUID de `localStorage` dejaron de otorgar acceso. El perfil muestra el nombre y correo reales de la sesión.
- Explorador con palabra clave, país, categoría opcional y periodo. Valida y guarda la investigación mediante FastAPI en PostgreSQL; muestra un error recuperable si la API no está disponible.
- Mis análisis lista investigaciones guardadas para la cuenta autenticada y permite abrir una ficha con los parámetros registrados. Desde cada ficha se puede consultar y guardar una muestra de productos de Mercado Libre, limitada por `MAX_PRODUCTS_PER_ANALYSIS` (200 por defecto), e importar una serie de Google Trends para el mismo término y país. El ETL muestra cuántos productos conservó y por qué excluyó otros.
- Resultado de análisis para investigaciones guardadas, con resumen de productos, interés y precios, gráfico de distribución de la muestra, evolución de Trends, pronóstico condicionado por evidencia y grupos calculados. Un ID inexistente muestra un estado de investigación no encontrada.
- Detalle de oportunidad para anillos, lámparas, vasos y bolsos, con segmento, características, variables y productos similares ficticios. Simulador reactivo por unidad con cinco entradas, validación, costo total, comisión, ganancia, margen, ROI y precio de equilibrio.
- Estudio IA mock con fotografía local, configuración de campaña, espera cancelable, 1–4 vistas previas, regeneración, selección y descarga PNG. Las vistas son recortes y filtros de la imagen original; el escenario todavía no se aplica.
- Mis catálogos con dos campañas de ejemplo ilustradas, búsqueda, filtros, detalle, favoritos, descarga, generación de una vista local, regeneración y eliminación reversible. Desde Estudio IA se puede crear un catálogo con las vistas seleccionadas o, si no hay selección, con todas.
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

**Inicio y la ruta de análisis muestran datos de la cuenta, sin métricas ficticias.** Los parámetros que se envían desde el Explorador se guardan en PostgreSQL. La ficha puede consultar datos actuales de Mercado Libre si el proveedor configurado admite el país. Una publicación puede incluir precio y enlace; un producto de catálogo no incluye ninguno de los dos y se identifica como tal. La muestra y el dataset depurado no son volumen de ventas ni una medida de demanda, competencia o tamaño de mercado. La categoría y el periodo guardados aún no filtran esa consulta. La serie importada de Google Trends es un índice relativo de interés, no ventas ni búsquedas absolutas; el periodo elegido tampoco se verifica automáticamente contra el CSV. El detalle de oportunidad de ejemplo conserva fixtures separados, mientras que la ruta de oportunidad guardada calcula y conserva un escenario sobre un producto de la muestra real. La ficha de análisis usa el escenario guardado para la puntuación y mantiene un formulario de vista previa temporal para probar otros pesos o costos. El pronóstico y los grupos de una investigación guardada se calculan con los datos disponibles.

El Estudio IA y Mis catálogos funcionan completamente en el navegador. No envían fotografías a FastAPI ni a terceros, ni generan imágenes con IA. «Guardar» selecciona vistas para crear un catálogo demo. Las campañas y cambios viven solo en memoria de la pestaña y desaparecen al recargar. Las dos campañas iniciales usan ilustraciones SVG ficticias. Las campañas nuevas y las vistas regeneradas son recortes y filtros locales de la imagen original; la descarga exporta el archivo mostrado.

## Requisitos

- Node.js 22.12+ de la rama 22 (verificado con 22.13.0), npm 11.
- Python 3.11+ con `venv` y `pip`.
- El detalle de oportunidad de ejemplo, Estudio IA, catálogos mock y `/api/health` funcionan sin base de datos. Inicio, Explorador, Mis análisis y los resultados de investigación requieren FastAPI y PostgreSQL.

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

La fórmula `exploratory-v1` usa crecimiento reciente de Trends (`clip(50 + crecimiento %)`) y estabilidad del pronóstico (`clip(100 − 5 × MAE)`), más margen (`clip(2,5 × margen %)`) y ROI (`clip(ROI %)`) calculados por unidad; cada componente se limita a 0–100. Los pesos por defecto son 0,25/0,15/0,35/0,25 y pueden cambiarse siempre que sumen 1. Una pérdida da score cero. Se exigen ocho productos con precio, crecimiento 3 contra 3, pronóstico validado, precio y costos explícitos y ROI definido; si falta algo, `score` es `null`. Se trata de una escala provisional sin calibración comercial: **no contiene demanda absoluta, ventas ni competencia medida**. Los impuestos, devoluciones y publicidad solo cuentan si el usuario los introduce en «Otros costos». La ruta de oportunidad guarda un escenario por investigación mediante la migración 0005; la vista previa de score con pesos alternativos no modifica ese registro.

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

Las variables de OpenAI y storage siguen reservadas y vacías. No hay secretos en Angular. Angular CLI no carga `.env` automáticamente: `environment.ts` contiene solo la ruta pública `/api` y `environment.development.ts` la sustituye mediante `fileReplacements`. En desarrollo el proxy de Angular dirige `/api/**` al backend local; en Vercel, `frontend/vercel.json` reescribe `/api` al backend público. El backend no abre una conexión a PostgreSQL para responder `/api/health`.

## Rutas

| Ruta | Estado |
| --- | --- |
| `/` | Inicio con conteos, investigaciones y actividad reales de la cuenta |
| `/login`, `/register` | Acceso a la cuenta y registro privado con invitación |
| `/explore` | Formulario que guarda búsquedas en FastAPI/PostgreSQL |
| `/analyses` | Historial real de búsquedas de la cuenta |
| `/analysis/:id` | Resultados de una investigación guardada si el ID es UUID; usa datos persistidos y consulta Mercado Libre solo bajo acción explícita |
| `/opportunity/saved/:id` | Producto observado y escenario financiero persistido para una investigación de tu cuenta |
| `/opportunity/:id` | Detalle y simulador para `demo-rings`, `demo-lamps`, `demo-cups` y `demo-bags`; estado vacío en otros casos |
| `/studio` | Estudio IA mock interactivo, sin generación ni persistencia real |
| `/catalogs` | Galería mock con dos ejemplos y campañas creadas durante la sesión |
| `/catalogs/:id` | Detalle, favoritos, descarga y acciones locales de la campaña |
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

Las pruebas verifican salud, error 404, CORS, validación del contrato, modelo inicial, configuración de PostgreSQL, ambos adaptadores de productos con respuestas HTTP simuladas, el parser CSV de Trends, ETL, variables descriptivas, clustering, forecasting con backtesting y score exploratorio. Con `ARBIGEN_TEST_DATABASE_URL` apuntando a una **base de pruebas migrada y separada** también verifican escritura/lectura, aislamiento entre cuentas autenticadas, importación de Trends, preparación del dataset, lectura analítica, escenarios financieros privados y agregados de Inicio con rollback. Las pruebas del proveedor no ejecutan el actor de Apify.

Frontend:

```bash
cd frontend
npm run build
npm run test:simulator
npm run test:analysis
npm audit
```

El lockfile fija el árbol npm. Se incluye un override temporal de `piscina` a `5.3.2` para corregir `GHSA-67c8-pqhq-4rmx` en la dependencia de compilación de Angular. Retirarlo cuando Angular incorpore una versión corregida y volver a verificar build/audit. ECharts se importa de forma modular siguiendo su [guía oficial](https://echarts.apache.org/handbook/en/basics/import/) y solo se carga al abrir un análisis. Las pruebas del cálculo usan `node:test` y el soporte de TypeScript de Node 22, sin añadir dependencias.

El simulador calcula por unidad: comisión = precio × porcentaje, redondeada a centavos; costo total = producto + envío + otros gastos + comisión; ganancia = precio − costo total; margen = ganancia ÷ precio; ROI = ganancia ÷ costo total. El equilibrio busca el menor precio en centavos que cubre el costo con la comisión redondeada. Si un denominador es cero, muestra «—»; con comisión de 100 % y costos fijos positivos no hay precio de equilibrio finito. Impuestos, devoluciones y publicidad solo cuentan si se agregan a «Otros gastos». Los valores de la ruta demo viven en memoria de la página. En la ruta de una investigación guardada, «Guardar escenario» persiste los importes en PostgreSQL local y los recupera al recargar.

Prueba manual sugerida:

1. Abrir Inicio con FastAPI y PostgreSQL: debe mostrar los conteos y la actividad de las investigaciones de la cuenta, sin ROI ni score ficticios. Si el espacio está vacío, debe mostrar cero y una invitación a investigar.
2. Seleccionar «Últimos 7 días»: los conteos y la tabla deben corresponder a investigaciones creadas en ese periodo; la actividad usa la fecha de cada guardado, preparación o importación.
3. Iniciar PostgreSQL, aplicar `alembic upgrade head`, iniciar FastAPI en `:8000` y Angular con `npm start`. Abrir «Analizar producto». Enviar el formulario vacío o con espacios: debe explicar el mínimo de 3 caracteres y enfocar el campo.
4. Usar el ejemplo, elegir México, Joyería y 6 meses. Guardar: debe aparecer la confirmación y un enlace a una ficha con esos filtros; los indicadores sin datos deben mostrar cero o «—», nunca cifras ficticias.
5. Abrir Mis análisis: debe aparecer la nueva búsqueda. Recargar la página y volver a abrir la ficha: debe conservarse. Una búsqueda creada en otra cuenta no debe aparecer en ésta. En la ficha guardada, pulsar «Consultar y preparar» **solo si deseas hacer una consulta real que puede generar cargos en Apify**. Deben aparecer la muestra, el resumen ETL y las señales descriptivas. Si hay al menos ocho productos con precios variados y grupos suficientemente separados, también deben aparecer segmentos con tamaños y precios reales; de lo contrario, una explicación de datos insuficientes. Recargar: el dataset, las señales y los grupos deben seguir visibles sin otra consulta. Pulsar «Reprocesar datos guardados»: debe actualizar el dataset sin llamar a Apify. Descargar el JSON y ejecutar el cuaderno. Con la API oficial solo funciona MX y puede mostrarse catálogo sin precios ante un 403.
6. En Google Trends, exportar «Interés a lo largo del tiempo» con una sola palabra clave igual a la búsqueda guardada y el mismo país. En la ficha, sección «Interés de búsqueda», elegir «CSV de Google Trends» e «Importar CSV»: debe aparecer la gráfica y persistir tras recargar. Si contiene 16 o más puntos observados consecutivos de frecuencia regular y pasa el backtest, «Pronóstico validado» debe mostrar método, error y tres valores futuros; de otro modo debe explicar por qué no publica uno. Probar un CSV de otro término: debe mostrar un error y mantener la serie previa. Si el encabezado incluye país, uno distinto también debe rechazarse; si solo dice `Time`, la ficha debe advertir que no pudo verificarlo. Un valor `<1` debe conservarse como valor censurado, distinto de cero. En «Puntuación exploratoria», el score debe estar vacío hasta introducir los cinco valores del escenario; con muestra y pronóstico suficientes debe mostrar score, utilidad, margen y ROI. Cambiar un peso y compensar otro modifica el score sin consultar Apify. Recargar borra solo la vista previa; un escenario guardado desde «Evaluar rentabilidad» permanece y alimenta la lectura inicial del score.
7. Desde una investigación con productos, abrir «Evaluar rentabilidad»: seleccionar una publicación y confirmar que su precio observado no rellena automáticamente el costo del proveedor. Introducir precio de venta y costos propios, guardar y recargar: deben conservarse el producto, los importes y la utilidad. Descargar el JSON, configurar `ARBIGEN_SCENARIO_PATH` y ejecutar el cuaderno. Cambiar la muestra mediante reprocesamiento no debe borrar la hipótesis guardada; la vista previa de score no debe sobrescribirla. Esta ruta no llama a Apify.
8. Abrir una investigación con productos guardados: el resumen y el gráfico de precios deben reflejar la misma muestra. Recargar no debe iniciar otra búsqueda ni cambiar los conteos. `/analysis/demo-rings` debe indicar que no existe una investigación con ese ID.
9. Detener FastAPI y repetir el guardado: debe aparecer un error de conexión. Reiniciar FastAPI y pulsar «Reintentar». «Nueva búsqueda» restaura los campos iniciales.
10. Los detalles de oportunidad de ejemplo `/opportunity/demo-lamps`, `/opportunity/demo-cups` y `/opportunity/demo-bags` siguen disponibles para probar el simulador; no enlazan a resultados de análisis ficticios.
11. En `/opportunity/demo-rings`, comprobar valores iniciales: comisión 63, costo total 290, ganancia 130, margen 31,0 %, ROI 44,8 % y equilibrio 267,06 MXN. Cambiar precio o costos y verificar que se recalculen al instante.
12. Probar venta por debajo de costos, campo vacío, costo negativo y comisión mayor a 100 %. La pantalla debe mostrar pérdida o errores según corresponda. Con comisión 100 %, el equilibrio no existe. «Restablecer ejemplo» restaura los cinco campos.
13. Abrir `/opportunity/no-existe`: debe aparecer el estado vacío.
14. Desde un detalle abrir «Abrir Estudio IA» y comprobar que aparece el nombre del producto. Subir un PNG, JPEG o WebP menor de 10 MB; el original debe verse a la izquierda sin modificaciones.
15. Cambiar estilo, escenario, iluminación, formato y número de variaciones. Pulsar «Preparar vistas previas»: aparece carga simulada y luego 1–4 recortes filtrados del original. Probar «Regenerar demo», «Guardar» y «Descargar PNG».
16. Durante la carga usar «Cancelar». Cambiar una opción o la fotografía después de generar: los resultados anteriores deben desaparecer. Probar un archivo inválido o mayor de 10 MB; debe mostrarse el error.
17. En Estudio IA, marcar una vista y pulsar «Crear catálogo demo»: el detalle debe contener solo esa vista y la fotografía original. Volver a Mis catálogos y comprobar la campaña nueva en el filtro «Esta sesión». Repetir sin marcar vistas: deben entrar todas.
18. En `/catalogs`, buscar un producto y comprobar el estado vacío con un término desconocido. Abrir una campaña de ejemplo, cambiar un favorito, descargar una vista, generar una nueva variación y regenerar otra. El límite es cuatro vistas por catálogo.
19. Eliminar un catálogo y usar «Deshacer». Recargar: deben restablecerse las campañas de ejemplo y desaparecer los cambios y las campañas creadas durante la sesión.
20. Navegar por todas las opciones del sidebar, recargar una ruta interna y probar una dirección desconocida.
21. Reducir el ancho a móvil, abrir/cerrar el menú y desplazar horizontalmente la tabla. Los gráficos, el simulador, el Estudio y Mis catálogos deben caber sin desbordamiento.
22. Navegar con Tab; probar «Saltar al contenido» y Escape para cerrar el menú.
23. Iniciar la API y comprobar `/api/health` y `/docs`.

El estado de carga de Inicio aparece al cambiar de periodo. Las ramas vacía y error responden a PostgreSQL real. El Explorador informa errores de conexión o base de datos y permite reintentar. Guardar una investigación no inicia todavía un trabajo analítico.

## Pendiente y siguiente paso

La estructura PostgreSQL, las búsquedas guardadas, los contratos `MarketplaceSearchProvider` y `TrendsProvider`, el modelo `MarketplaceProduct`, los adaptadores Apify/oficial, el importador CSV, el ETL, las variables descriptivas, la segmentación, el pronóstico validado y el score exploratorio ya existen. El token oficial local funciona para `/users/me` y `/products/search`, pero `/sites/MLM/search` responde 403. Con autorización específica se ejecutó una consulta del actor de Karamelo para «juguetes de bebe» en MX, una página y `maxItems=12`: quedaron 12 productos depurados; el clustering agrupó 11 en dos segmentos e informó un precio atípico excluido solo del ajuste. La investigación local tiene ahora 273 puntos mensuales importados del CSV `Time` facilitado por el usuario (enero de 2004 a septiembre de 2026); el pronóstico validado eligió el método estacional ingenuo. El país no es verificable dentro de ese formato, como indica la ficha. Colombia y Argentina están cubiertos por pruebas HTTP simuladas, todavía no por una ejecución real del actor. El límite de 200 es un máximo, no una garantía de que el actor devuelva exactamente 200 productos. Cada pulsación de «Consultar y preparar» o «Actualizar y preparar» inicia otra ejecución del actor y puede generar cargos; reprocesar, descargar el JSON, abrir el cuaderno o calcular un escenario no inicia búsquedas. Siguen pendientes recuperación de cuenta, MFA, protección persistente contra intentos masivos, análisis de mercado más amplio, mediciones independientes de demanda y competencia, conexión de las demás pantallas con la API, generación de imágenes con IA y almacenamiento externo. Los catálogos de campañas todavía viven solo en memoria del navegador.

El backend usa una entrada reconocible por Vercel, conexiones perezosas y migraciones externas al ciclo de vida de la Function. La migración 0004 está aplicada en Neon `neon-bole-cave` (rama `main`, base `neondb`); la base local `arbigen` está en 0005. Production no recibió los cambios de esta fase. `frontend/vercel.json` configura la salida Angular, la reescritura de `/api` y el fallback SPA. El código publicado en Production sigue en `main`; los cambios de Development están en una rama local para probarlos antes de publicar. [Arbigen web](https://arbigen-web.vercel.app/) responde en Production; `/api/health` y las rutas protegidas de `/api/v1/` pasan mediante su proxy hacia [Arbigen API](https://arbigen-api.vercel.app/api/health). La base alojada no recibió las investigaciones, productos ni Trends locales. La investigación local histórica ya pertenece a la cuenta registrada en Development; el UUID demo de localStorage no concede acceso.

**Siguiente paso propuesto:** retirar la ruta de oportunidad ficticia y dirigir los enlaces que aún la usan hacia investigaciones y escenarios financieros guardados. Después, sustituir las campañas de ejemplo y el almacenamiento temporal de Estudio IA y Mis catálogos cuando exista una generación o persistencia real. Esta limpieza puede hacerse sin ejecutar una nueva búsqueda de Apify.

Ver [arquitectura e inventario de archivos](docs/architecture.md).
