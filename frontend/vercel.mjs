// Configuración del proyecto Vercel cuya Root Directory es frontend/.
// El origen público del backend se define en Project Settings, sin secretos.
const rawOrigin = process.env.ARBIGEN_API_ORIGIN;
if (!rawOrigin) {
  throw new Error('Configura ARBIGEN_API_ORIGIN con el dominio HTTPS del proyecto backend antes de desplegar el frontend.');
}

const parsedOrigin = new URL(rawOrigin);
if (parsedOrigin.protocol !== 'https:' || parsedOrigin.username || parsedOrigin.password ||
    parsedOrigin.pathname !== '/' || parsedOrigin.search || parsedOrigin.hash) {
  throw new Error('ARBIGEN_API_ORIGIN debe ser un origen HTTPS sin ruta ni credenciales.');
}

export const config = {
  framework: 'angular',
  buildCommand: 'npm run build',
  outputDirectory: 'dist/arbigen/browser',
  rewrites: [
    { source: '/api/:path*', destination: `${parsedOrigin.origin}/api/:path*` },
    { source: '/(.*)', destination: '/index.html' },
  ],
};
