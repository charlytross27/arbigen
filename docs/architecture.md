# Arquitectura de Arbigen hasta la fase 19

## Límite del slice

Se construyeron setup, layout, Dashboard, Explorador, análisis, detalle con simulador, Estudio IA mock, galería de catálogos mock, esquema PostgreSQL y el flujo Angular → FastAPI → PostgreSQL. Las investigaciones de MX/CO/AR pueden pedir una muestra actual de Mercado Libre mediante FastAPI, guardar una serie CSV de Google Trends, preparar un dataset limpio, calcular señales descriptivas, segmentar productos y evaluar un pronóstico temporal. Los modelos de oportunidad y las campañas visuales siguen siendo demos locales.

```text
Angular Router
  └─ ShellComponent
       ├─ DashboardComponent → AnalysisApiService → GET /api/v1/dashboard → PostgreSQL
       ├─ ExploreComponent → AnalysisApiService → POST /api/v1/analyses
       ├─ AnalysesComponent → AnalysisApiService → GET /api/v1/analyses
       ├─ AnalysisComponent → AnalysisDemoService → fixtures tipados
       │    ├─ ID UUID → AnalysisApiService → GET /api/v1/analyses/{id}
       │    │    ├─ consulta manual → POST /dataset/refresh → MarketplaceSearchProvider → ETL
       │    │    ├─ lectura → GET /dataset → PostgreSQL
       │    │    ├─ variables → GET /features → ingeniería sobre dataset guardado
       │    │    ├─ segmentos → GET /clusters → K-Means sobre productos guardados
       │    │    ├─ pronóstico → GET /forecast → backtesting sobre Trends guardado
       │    │    └─ reprocesar → POST /dataset/reprocess → ETL, sin proveedor externo
       │    └─ AnalysisChartComponent → ECharts (SVG, cinco vistas)
       ├─ SavedOpportunityComponent → GET/PUT /financial-scenario → PostgreSQL
       │    └─ calculateProfitability() → vista previa sobre producto guardado
       ├─ OpportunityComponent → OpportunityDemoService → fixtures tipados
       │    └─ calculateProfitability() → cálculo puro por unidad
       ├─ StudioComponent → StudioDemoService → variantes locales simuladas
       │    └─ studio-preview.ts → exportación PNG con recorte y filtro
       ├─ CatalogsComponent → CatalogDemoService → fixtures + campañas de sesión
       │    └─ studio-preview.ts → variaciones y regeneración locales
       └─ PlaceholderComponent → contenido de cada ruta

FastAPI create_app()
  ├─ Settings (Pydantic Settings, entorno)
  ├─ CORS + manejadores de errores
  ├─ health/router.py → HealthResponse
  ├─ analyses/router.py → schemas → service → SQLAlchemy Session
  └─ dashboard/router.py → service → conteos y actividad por workspace

app/modules/marketplace/domain.py → MarketplaceProduct + MarketplaceSearchProvider
app/integrations/marketplace_search.py → selección del adaptador en la composición
app/integrations/apify/provider.py → Actor Karamelo → MarketplaceProduct
app/integrations/mercado_libre/provider.py → API oficial → MarketplaceProduct
app/modules/etl/pipeline.py → MarketplaceProduct + TrendObservation → PreparedDataset
app/modules/analyses/dataset.py → marketplace_snapshots (entrada) + products (salida)
app/modules/features/engineering.py → PreparedDataset → FeatureReport (sin I/O)
app/modules/analyses/features.py → dataset persistido → respuesta de API
app/modules/clustering/model.py → AnalyticalProduct → ClusterReport (sin I/O)
app/modules/analyses/clusters.py → dataset persistido → respuesta de API
app/modules/forecasting/model.py → AnalyticalTrendPoint → ForecastReport (sin I/O)
app/modules/analyses/forecast.py → Trends persistido → respuesta de API
app/modules/profitability/model.py → supuestos explícitos → economía unitaria con Decimal
app/modules/analyses/financial.py → escenario privado persistido → respuesta de API
app/modules/scoring/model.py → señales + costos explícitos → score exploratorio
notebooks/arbigen_ciencia_de_datos.ipynb → JSON exportado → mismo pipeline analítico y financiero

backend/index.py → app.main:app (entrada Vercel)
frontend/vercel.json → salida Angular + /api externo + fallback SPA
app/database/models.py → 11 tablas SQLAlchemy → PostgreSQL local o administrado
app/database/session.py → Engine perezoso y sesiones por petición
alembic/versions/0001–0005 → esquema inicial, Trends, ETL, sesiones y escenarios financieros (ejecución explícita)
```

## Responsabilidades y decisiones

1. `core/models` define los contratos del Dashboard, las búsquedas guardadas, el dataset y sus variables; los fixtures todavía usados por rutas demo permanecen en servicios separados. `AnalysisApiService` encapsula HttpClient para las rutas persistentes.
2. `layout` contiene navegación, menú móvil y encabezado. Signals manejan el estado local. Los cambios de ruta cierran el menú y dirigen el foco al contenido.
3. `features/dashboard` presenta conteos e investigaciones reales; RxJS cancela la solicitud HTTP anterior al cambiar entre 7 y 30 días. No hay servicio de fixtures, ROI ni score inventado en Inicio. El endpoint agregado lee únicamente el workspace del navegador; filtra conteos por `analyses.created_at` y eventos por su propia fecha.
4. `features/explore` valida la palabra clave (3–120 caracteres tras normalizar espacios) y envía query, país, categoría y periodo a FastAPI. El estado de carga corresponde a una petición HTTP real. El éxito guarda los parámetros y recibe un UUID; no calcula métricas ni obtiene datos de mercado.
5. `features/analysis` consulta FastAPI cuando el ID de la ruta es un UUID guardado; muestra los filtros persistidos sin KPIs de mercado. Los IDs `demo-rings`, `demo-lamps` y `demo-cups` conservan los tres fixtures locales. Los demás IDs muestran un estado vacío.
6. `AnalysisChartComponent` encapsula la inicialización de ECharts, usa el renderer SVG, redimensiona con `ResizeObserver` y libera la instancia al destruirse. `analysis-chart-options.ts` define interés, proyección ilustrativa, histograma de precios, dispersión precio-demanda y segmentos. Los gráficos viven en el chunk lazy de la ruta de análisis.
7. `features/placeholder` mantiene las pantallas aún no implementadas. `features/analyses` lista las búsquedas persistidas con paginación de 20 en 20; `features/analysis` lee parámetros reactivos de Router para actualizarse cuando Angular reutiliza el componente.
8. Inicio cuenta investigaciones, muestras preparadas, productos con precio y series importadas. Sus filas y eventos enlazan a fichas guardadas; no deduce demanda, competencia ni rentabilidad de esos conteos. Un workspace sin datos devuelve ceros y listas vacías.
9. El fixture principal conserva score 87, ROI 42%, margen 31%, competencia media, tendencia creciente, cluster Minimalista / Plata / Ajustable, precio 420 MXN, costo proveedor 115 MXN y envío 35 MXN. El simulador usa supuestos editables independientes de los KPI ficticios.
10. La proyección de tres puntos es una serie fija; los grupos y el cluster recomendado son etiquetas y puntos predefinidos; el score es un valor fijo. El selector de periodo recorta únicamente la serie de interés. Estas decisiones mantienen la demo honesta mientras se posponen modelos y fórmulas.
11. `features/opportunity` compone los datos de los tres análisis existentes con metadatos de detalle ficticios; añade una ficha autónoma para el bolso enlazado desde el Dashboard. Un ID desconocido muestra un estado vacío.
12. `profitability.ts` calcula la vista previa por unidad sin consultar el backend. La comisión es un porcentaje del precio de venta y se redondea a centavos. Margen usa el precio como denominador; ROI usa el costo total. El equilibrio busca el menor centavo que cubre los costos tras redondear la comisión. Los cocientes con denominador cero son indefinidos; con 100 % de comisión y costos fijos positivos no existe precio de equilibrio. La vista valida importes no negativos y comisión entre 0 y 100 %; al guardar exige precio de venta positivo.
13. Los supuestos financieros se editan en memoria. Los ROI/márgenes de Dashboard y análisis son fixtures independientes: se mantienen como métricas ilustrativas, no se sincronizan con el simulador. Impuestos, devoluciones y publicidad deben agregarse a «Otros gastos» si se desean incluir.
14. `features/studio` mantiene imagen y configuración en memoria mediante Signals. Solo acepta PNG, JPEG y WebP hasta 10 MB, verifica que la imagen se pueda decodificar y libera las URL temporales al reemplazarla o salir. El nombre del producto puede llegar desde el detalle por query param.
15. `StudioDemoService` simula una espera y produce parámetros de recorte/filtro para 1–4 vistas. El escenario y descripción se recogen para el contrato futuro, pero no transforman la fotografía. Regenerar cambia el tratamiento local; «Guardar» selecciona una vista para la nueva campaña de demostración.
16. `studio-preview.ts` exporta a PNG el recorte y filtro mostrados. Ninguna fotografía se envía al backend, a OpenAI ni a almacenamiento; la descarga la inicia el navegador. No existe todavía `ImageGenerationProvider` porque no hay generación real en esta fase.
17. `features/catalogs` conserva dos fixtures SVG y campañas creadas desde Estudio IA en un servicio singleton con Signals. Los cambios, favoritos y eliminaciones reversibles viven solo en memoria. Cada catálogo tiene hasta cuatro vistas y conserva su original para derivar variaciones locales. Las URL de objetos de la pantalla Studio se liberan al salir; el servicio de catálogos crea sus propias URL para conservar los archivos durante la sesión.
18. El backend contiene los módulos `health` y `analyses`, cada uno con rutas y contratos propios; `analyses` separa además la persistencia en un servicio. `main.py` solo monta middleware, errores y routers.
19. La API configura errores con envelope `{"error":{"code":"...","message":"..."}}`; los errores internos se registran sin exponer el traceback al cliente. CORS permite solo orígenes configurados.
20. La fase 8 añade `User`, `Analysis`, `Product`, `TrendPoint`, `Cluster`, `Opportunity`, `Campaign` y `GeneratedAsset` como tablas PostgreSQL. UUID y fechas con zona horaria tienen defaults del servidor; JSONB guarda atributos de producto. Las imágenes se referencian mediante URL, sin bytes en la base.
21. `database/session.py` normaliza URLs PostgreSQL al driver psycopg. El Engine se crea perezosamente con pool de dos conexiones por instancia, sin abrir red al responder salud. Las sesiones se cierran por petición; el servicio que escriba será responsable del commit.
22. Alembic usa `DATABASE_MIGRATION_URL` (o `DATABASE_URL` local) y una conexión sin pool para DDL. Las migraciones se ejecutan fuera del arranque y del build de Vercel. Neon proporciona URL agrupada para tráfico y directa para migraciones; el esquema remoto está en `0004_auth_sessions` y Development local en `0005_financial_scenarios`.
23. La fase 9 creó `users` y `analyses` para guardar búsquedas, entonces asociadas a un UUID de navegador. La fase 18 deja de aceptar esa identidad demo: `POST /api/v1/analyses` y todas las lecturas obtienen el usuario de una sesión validada; cada ficha se filtra por `user_id`. Los registros de usuarios ficticios anteriores conservan `password_hash=NULL` y no pueden iniciar sesión.
24. El cliente Angular llama a `/api`, que `npm start` dirige al backend mediante `proxy.conf.json`. En Vercel, `frontend/vercel.json` reescribe `/api` desde `arbigen-web` hacia `arbigen-api`. La API valida cuerpo y cookie de sesión, devuelve solo datos del propietario y pagina resultados; las rutas de demo visual permanecen separadas.
25. La búsqueda de productos depende de `MarketplaceSearchProvider` y devuelve `MarketplaceSearchResult` con objetos `MarketplaceProduct`; no expone campos de Apify. `MAX_PRODUCTS_PER_ANALYSIS` limita la respuesta a 200 por defecto. La composición selecciona Apify cuando `APIFY_API_TOKEN` está configurado en modo `auto`; de otro modo usa la API oficial, que solo admite MX. El adaptador Apify traduce el contrato del actor `karamelo/mercadolibre-scraper-espanol-castellano`, limita páginas, excluye patrocinados y páginas de detalle, envía `maxItems` y `limit` a la API de Apify, valida enlaces, IDs y monedas por país y deduplica antes de entregar el modelo interno. El adaptador oficial intenta `/sites/MLM/search` y, ante 403, `/products/search`, con una muestra máxima de 20. Los productos de catálogo no tienen precio ni enlace de publicación. La UI usa `POST /dataset/refresh` para consultar y preparar en una sola ejecución. Se retiró el endpoint de muestra aislado, ya sin consumidores. Categoría y periodo no se aplican todavía.
26. `TrendsProvider` define una serie interna de `TrendObservation`. La implementación inicial analiza CSV exportados de Google Trends: acepta `Day/Week/Month` con término y país en el encabezado, y `Time` con solo término. Verifica fechas únicas e índice 0–100, y conserva `<1` como valor censurado (`value=NULL`, `less_than_one=true`). En el formato `Time` no puede verificar la geografía y marca la procedencia `google_trends_csv_geo_unverified`; la ficha advierte esa limitación. `GET/POST /api/v1/analyses/{id}/trends` comprueba que la investigación pertenece al usuario autenticado antes de leer o sustituir sus puntos. La migración 0002 añade procedencia e instante de importación a `analyses` y permite el valor censurado en `trend_points`. El frontend carga la serie persistida al abrir la ficha e importa el CSV bajo acción explícita; no realiza una petición a Google. El periodo del CSV es responsabilidad del usuario porque el encabezado exportado no lo identifica con seguridad.
27. El ETL de fase 12 consume solo `MarketplaceProduct` y `TrendObservation`. `POST /dataset/refresh` consulta una vez y guarda la muestra normalizada en `marketplace_snapshots`; `products` contiene solo filas depuradas con precio válido. `GET /dataset` no consulta fuentes externas y `POST /dataset/reprocess` vuelve a aplicar las reglas a la muestra guardada. El ETL normaliza títulos, deduplica por ID, redondea precios dentro de su moneda local, excluye faltantes/valores inválidos y extrae pistas de material del título sin presentarlas como atributos verificados. Conserva los puntos `<1` de Trends como censurados. `ProductQuality` explica conteos de inclusión/exclusión. No se convierten divisas sin tipos de cambio ni se calculan ventas. La migración 0003 crea la tabla de muestras y añade `permalink` a `products`.
28. La fase 13 calcula `FeatureReport` sobre productos y puntos internos, sin campos de Apify ni llamadas externas. Precio mínimo, máximo, media, mediana, desviación estándar poblacional y cobertura describen la muestra con precio; el conteo por material es una pista textual. Para Trends se informan cobertura observada, nivel/volatilidad y ventanas regulares de tres puntos para media móvil, crecimiento, momentum y aceleración. `<1` nunca se imputa; ventanas incompletas o irregulares y cocientes con denominador cero producen `null`. `GET /features` verifica el workspace y calcula desde PostgreSQL. El cuaderno consume JSON exportado y reutiliza las funciones de producción. La ficha guardada reemplaza parte de la experiencia mock con señales reales; las rutas demo aisladas siguen explícitamente marcadas como ficticias.
29. La fase 14 calcula grupos desde `AnalyticalProduct` mediante K-Means determinista. Usa `log1p(precio)` estandarizado y categorías de pistas de material con peso menor, evalúa 2–4 grupos por silueta y exige mínimo de muestra, variación de precios y dos miembros por grupo. Una regla de Tukey puede excluir del ajuste una fracción pequeña (≤10 %) de precios atípicos, informando el conteo y dejando intacto el dataset. Los grupos se ordenan por precio mediano, sin interpretar ventas, competencia o demanda. `GET /clusters` verifica el workspace, lee PostgreSQL y calcula sin llamar al proveedor; no persiste resultados en la tabla `clusters` preexistente. El cuaderno llama a la misma función y la ficha muestra grupos reales separados de los fixtures demo. No hay recomendación automática de un grupo.
30. La fase 15 calcula un pronóstico sobre `AnalyticalTrendPoint`. Usa solo la secuencia numérica posterior al último `<1`, valida frecuencia diaria/semanal/mensual y requiere 16 puntos como mínimo. Un backtest de al menos seis orígenes y horizonte tres compara último valor, media móvil, drift y, si existen dos ciclos, patrón estacional ingenuo. Elige el menor MAE y no publica pronóstico si supera 20 puntos. El rango por horizonte usa errores retrospectivos con piso de cinco puntos, sin presentarse como intervalo de confianza. `GET /forecast` verifica el workspace y calcula sobre Trends guardado, sin Apify, Google ni persistencia adicional; el mismo algoritmo se documenta y ejecuta en el cuaderno. La clasificación de dirección es reciente y descriptiva, no un pronóstico de ventas.
31. La fase 16 introduce `scoring/model.py`, una función pura sobre `FeatureReport`, `ForecastReport` y supuestos financieros explícitos. `exploratory-v1` normaliza crecimiento, MAE, margen y ROI a 0–100 y combina pesos configurables que suman uno; exige ocho productos con precio, crecimiento calculable, pronóstico validado y economía unitaria con ROI definido. El score permanece `null` si falta una entrada. Una operación con pérdida recibe cero. Este indicador provisional no contiene demanda absoluta ni competencia, y no debe confundirse con una recomendación. `GET /opportunity-score` informa faltantes; `POST /opportunity-score/preview` calcula sin escrituras ni proveedores externos. El formulario de vista previa de la ficha guardada no persiste costos; la ruta de rentabilidad de la fase 19 sí los guarda. El cuaderno usa el mismo cálculo y estudia sensibilidad del precio aportado por el usuario.
32. La fase 17 reemplaza el servicio mock de Inicio por `GET /api/v1/dashboard`. El backend usa agregados por investigación para evitar multiplicar filas de productos y Trends; devuelve hasta cinco fichas y seis eventos ordenados por fecha. La sesión determina el usuario también en esta ruta. `frontend/vercel.json` configura la salida estática, el proxy de `/api` hacia el dominio público de FastAPI y el fallback SPA. Neon `neon-bole-cave` está vinculado solo al backend Production; el esquema remoto tiene 11 tablas y responde a lecturas reales, todavía sin registros migrados de la base local.
33. La fase 18 añade `auth_sessions` y `users.password_hash`, registro con invitación, hash Argon2, cookie HttpOnly/Secure/SameSite, revocación de sesión, validación de origen y CSRF en escrituras. El guard de Angular solo organiza la navegación; la autorización efectiva ocurre en FastAPI. Las sesiones y datos privados no se cachean. La recuperación de cuenta y los controles contra intentos masivos siguen pendientes.
34. La fase 19 añade `financial_scenarios` (migración 0005), un escenario privado por investigación. La API valida que el producto pertenezca a la investigación del usuario, exige CSRF para escribir y conserva título, moneda y precio observado aunque se sustituya la muestra. `profitability/model.py` calcula economía unitaria con Decimal; la pantalla guardada hace una vista previa sin fuente externa y el cuaderno reutiliza la misma función. El score leído usa el escenario guardado si existe; el endpoint de vista previa acepta importes y pesos alternativos sin persistirlos. El despliegue de Production sigue en 0004.

## Fronteras futuras, todavía sin implementación

- `MarketplaceSearchProvider` aísla la fuente de productos de MX/CO/AR. El clustering consume `AnalyticalProduct` derivados de `MarketplaceProduct`; forecasting consume `AnalyticalTrendPoint`; el score exploratorio consume `FeatureReport`, `ForecastReport` y `FinancialAssumptions`, nunca nombres de campos de Apify. `TrendsProvider` aísla la fuente histórica y permite sustituir el CSV por una API cuando esté disponible.
- La fase 12 separa la muestra de entrada normalizada del dataset de productos limpio. No conserva el JSON crudo de Apify; las reglas analíticas no conocen su contrato.
- `CampaignService` dependerá de `ImageGenerationProvider` y `StorageProvider`, sin importar un SDK concreto. Las claves y los prompts pertenecerán al backend.
- La fuente Mercado Libre se consulta bajo demanda, Google Trends se importa desde CSV y el ETL prepara datos. Variables descriptivas, segmentos, pronóstico y score exploratorio se calculan sin una nueva consulta. La validación comercial completa sigue pendiente.
- El Opportunity Score de las rutas demo sigue siendo un dato ficticio. La ficha guardada muestra por separado un score exploratorio, calculado con datos persistidos y supuestos del usuario, sin sustituir todavía una medición comercial completa.
- Los trabajos largos de análisis/generación deberán evaluar los límites de ejecución de Vercel antes de implementar una estrategia. Este slice no toma decisiones de infraestructura sobre ellos.

## Archivos principales de datos y ciencia de datos

```text
backend/app/modules/marketplace/domain.py
backend/app/modules/etl/domain.py
backend/app/modules/etl/pipeline.py
backend/app/modules/features/domain.py
backend/app/modules/features/engineering.py
backend/app/modules/clustering/domain.py
backend/app/modules/clustering/model.py
backend/app/modules/forecasting/domain.py
backend/app/modules/forecasting/model.py
backend/app/modules/profitability/model.py
backend/app/modules/scoring/model.py
backend/app/modules/analyses/dataset.py
backend/app/modules/analyses/features.py
backend/app/modules/analyses/clusters.py
backend/app/modules/analyses/forecast.py
backend/app/modules/analyses/financial.py
backend/app/modules/analyses/scoring.py
backend/app/modules/analyses/router.py
backend/tests/test_etl.py
backend/tests/test_features.py
backend/tests/test_clustering.py
backend/tests/test_forecasting.py
backend/tests/test_profitability.py
backend/tests/test_financial_scenario.py
frontend/src/app/core/models/analytical-dataset.model.ts
frontend/src/app/core/models/analysis-features.model.ts
frontend/src/app/core/models/analysis-clusters.model.ts
frontend/src/app/core/models/analysis-forecast.model.ts
frontend/src/app/core/models/saved-financial-scenario.model.ts
frontend/src/app/core/services/analysis-api.service.ts
frontend/src/app/features/analysis/analysis.component.ts
frontend/src/app/features/analysis/analysis.component.html
frontend/src/app/features/opportunity/saved-opportunity.component.ts
frontend/src/app/features/opportunity/saved-opportunity.component.html
notebooks/arbigen_ciencia_de_datos.ipynb
```

Los JSON exportados se guardan en `notebooks/data/` y están ignorados por Git. `node_modules`, `.angular`, `dist`, `.venv`, cachés de Python y `.env` también son artefactos locales ignorados.
