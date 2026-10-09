# Desarrollo local de Arbigen

Esta guía reúne la puesta en marcha y las comprobaciones técnicas. La [portada del proyecto](../README.md) explica el recorrido para quien utiliza la aplicación.

## Requisitos

- Node.js compatible con Angular 21 (`^20.19.0`, `^22.12.0` o `^24.0.0`) y npm.
- Python 3.11 o posterior, con `venv` y `pip`.
- PostgreSQL para cuentas, investigaciones, escenarios y catálogos.

La configuración de ejemplo está en [`backend/.env.example`](../backend/.env.example). Los secretos deben permanecer en `backend/.env` o en las variables del servidor; nunca en Angular ni en Git.

## Iniciar la API

Desde la raíz del repositorio:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
test -f .env || cp .env.example .env
```

Completa `DATABASE_URL` y un `AUTH_REGISTRATION_CODE` de al menos 24 caracteres en `backend/.env`. La base indicada debe existir y estar en funcionamiento. Después aplica las migraciones e inicia FastAPI:

```bash
alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

La API expone [su documentación interactiva](http://localhost:8000/docs) y responde en `http://localhost:8000/api/health`. `alembic downgrade base` elimina tablas y no debe ejecutarse sobre una base con datos que quieras conservar.

## Iniciar la web

En otra terminal, desde la raíz:

```bash
cd frontend
npm ci
npm start
```

Abre [http://localhost:4200](http://localhost:4200). `npm start` usa la configuración `development`; el proxy de Angular envía `/api` a FastAPI en `127.0.0.1:8000`. La web, la API y PostgreSQL deben estar activos para registrar una cuenta y guardar investigaciones.

Para compilar sin iniciar el servidor:

```bash
cd frontend
npm run build:development
```

`npm run build` genera la variante de Production, pero **compilar no despliega** la aplicación. Consulta la [guía de entornos](entornos.md) antes de trabajar con una base alojada.

## Servicios externos y almacenamiento

- `APIFY_API_TOKEN` habilita el proveedor de publicaciones de Apify en modo `auto`. Sin él, la integración oficial de respaldo solo admite México y puede ofrecer una muestra de catálogo sin precios.
- `MAX_PRODUCTS_PER_ANALYSIS` limita la muestra solicitada; su valor predeterminado es `200`. Es un máximo, no una promesa de cantidad recibida.
- `OPENAI_API_KEY` habilita la generación de imágenes en Estudio IA. Cada solicitud real puede generar un cargo.
- `IMAGE_STORAGE_BACKEND=local` guarda las imágenes de Development en disco. Production usa un Blob privado con configuración independiente.

El listado completo de variables y valores predeterminados está en [`backend/.env.example`](../backend/.env.example). Revisa la [arquitectura](architecture.md) para los contratos de proveedores y la [guía de almacenamiento](almacenamiento-imagenes.md) para imágenes y borradores.

## Pruebas

Backend:

```bash
cd backend
source .venv/bin/activate
python -m pytest -q
python -m pip check
```

Frontend:

```bash
cd frontend
npm run build
npm run test:simulator
npm run test:analysis
npm run test:studio-image
```

Las pruebas de proveedores utilizan respuestas simuladas; no ejecutan búsquedas facturables ni generan imágenes de pago. Las pruebas que escriben en PostgreSQL requieren `ARBIGEN_TEST_DATABASE_URL` apuntando a una **base de pruebas migrada y separada**.

## Documentación técnica

- [Arquitectura y pipeline analítico](architecture.md)
- [Entornos local y Production](entornos.md)
- [Autenticación y acceso privado](autenticacion.md)
- [PostgreSQL alojado en Vercel](vercel-database.md)
- [Almacenamiento privado de imágenes](almacenamiento-imagenes.md)
- [Estado y comprobaciones del MVP](release-mvp.md)
- [Cuaderno reproducible de ciencia de datos](../notebooks/arbigen_ciencia_de_datos.ipynb)
