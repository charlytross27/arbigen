# Desarrollo local y Production

| | Development local | Production |
| --- | --- | --- |
| Angular | `npm start` → `ng serve --configuration development` en `localhost:4200` | `npm run build` → `ng build --configuration production` en Vercel |
| API en el navegador | `/api/**` → proxy Angular a `127.0.0.1:8000` | `/api/:path*` → rewrite de `arbigen-web` a `arbigen-api` |
| FastAPI | `ENVIRONMENT=development` en `backend/.env` | `ENVIRONMENT=production` en `arbigen-api` |
| PostgreSQL | `DATABASE_URL` local, actualmente `localhost:5432/arbigen` | Neon, vinculado únicamente a `arbigen-api` Production |
| Cuentas y datos | Se guardan solo en la base local | Se guardan solo en Neon |

Angular usa las [configuraciones de compilación y `fileReplacements`](https://angular.dev/tools/cli/environments): `src/environments/environment.ts` es la variante de Production y `environment.development.ts` la sustituye en Development. Los dos builds usan `/api` como ruta relativa para que la cookie sea del mismo origen. Lo que cambia es el destino en el servidor: el [proxy del servidor de desarrollo](https://angular.dev/tools/cli/serve#proxying-to-a-backend-server) frente al rewrite de Vercel. No se incluyen URLs de bases de datos ni secretos en el bundle Angular. El distintivo «Desarrollo local» aparece solo en la interfaz compilada para Development.

Para probar localmente:

```bash
sudo pg_ctlcluster 18 main start
pg_lsclusters                     # debe mostrar online
cd backend
./.venv/bin/alembic upgrade head # aplica 0004 si aún falta
./.venv/bin/python -m uvicorn app.main:app --reload --port 8000
```

En otra terminal:

```bash
cd frontend
npm start
```

Abre `http://localhost:4200/register` y crea **una cuenta local** con el código de invitación guardado en `backend/.env`. Aunque uses el mismo correo que en Production, las cuentas y las sesiones son independientes; una cuenta de Neon no inicia sesión en la base local. No uses `arbigen-web.vercel.app` para ensayar cambios locales, pues ese dominio siempre sirve el último despliegue de Production.

Las investigaciones creadas antes de la autenticación quedaron ligadas a usuarios demo sin contraseña. Después de registrar tu cuenta local, puedes ver una vista previa de su reasignación, sin consultar Apify ni cambiar datos:

```bash
cd backend
./.venv/bin/python -m scripts.attach_local_data --target-email tu-correo@example.com
```

Si el conteo coincide con tus datos, haz una copia de la base y ejecuta el mismo comando con `--apply`. Mueve solo la propiedad de análisis y campañas de usuarios antiguos sin contraseña; productos, series de Trends y muestras siguen ligados a cada análisis y se conservan. El script rechaza cualquier conexión que no sea PostgreSQL en `localhost` o cuyo `ENVIRONMENT` no sea `development`. No modifica Neon. Si el conteo es cero, no hace falta reasignar nada.

Los proyectos Vercel `arbigen` y `arbigen-web` compilan actualmente el mismo frontend. El primero no representa Development y genera un despliegue adicional al publicar `main`; `arbigen-web` es el dominio usado por el rewrite y por `CORS_ORIGINS`. No cambies ese dominio ni borres un proyecto sin revisar antes los enlaces y usuarios que puedan usarlo. Para probar una versión alojada de Development en el futuro hará falta otra base o rama de Neon, nunca conectar Preview a la base de Production.

Al 2 de octubre de 2026, la base local `arbigen` quedó en la revisión `0004`, se registró una cuenta local y se reasignó la investigación histórica a ella. Permanecen 1 investigación, 12 productos, 273 puntos de Trends y 1 muestra. El respaldo previo está en `backend/local-backups/`, ignorado por Git. Esta operación no copió ningún dato a Neon.
