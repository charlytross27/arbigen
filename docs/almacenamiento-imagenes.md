# Imágenes de catálogo por entorno

Development guarda las imágenes en `backend/.data/images` (o en la ruta indicada
por `IMAGE_STORAGE_PATH`). No usa Vercel Blob aunque exista un token en el
archivo local. PostgreSQL guarda los metadatos del catálogo, no los bytes de
las imágenes.

Production usará el Blob store **Private** de `arbigen-api`, que ya aparece en
Vercel. El adaptador `VercelBlobImageStorage` escribe con `access="private"`
bajo `arbigen/production/<usuario>/<catálogo>/<archivo>`. Las rutas de catálogo
de FastAPI comprueban la sesión y la propiedad antes de leer cada imagen. El
frontend usa esas rutas; no recibe la URL del Blob ni el token. Una URL directa
de un objeto privado no permite abrirlo sin autorización del almacén.

Para habilitar este almacenamiento cuando se autorice el despliegue de
Production, verifica que el store privado esté vinculado a `arbigen-api` solo
en Production y que el proyecto tenga `BLOB_READ_WRITE_TOKEN`. Configura también
`IMAGE_STORAGE_BACKEND=vercel_blob` y `ENVIRONMENT=production` en ese proyecto;
instala las dependencias de `backend/requirements.txt` durante el build. El
backend comprueba que la URL recibida tras cada subida pertenezca a un dominio
`.private.blob.vercel-storage.com`. Sin la configuración, las rutas de catálogo
responden 503; el código de esta fase aún no se ha desplegado.

No hay migración entre las imágenes locales y Blob: Development y Production
usan bases de datos separadas. Tampoco se ejecutó ninguna subida o consulta
real a Blob durante esta fase; las pruebas usan un cliente simulado.

Consulta [Vercel Blob Private Storage](https://vercel.com/docs/vercel-blob/private-storage)
y [el SDK de Blob para Python](https://vercel.com/docs/vercel-blob/using-blob-sdk).
