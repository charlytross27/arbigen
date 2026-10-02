import { bootstrapApplication } from '@angular/platform-browser';
import { AppComponent } from './app/app.component';
import { appConfig } from './app/app.config';

bootstrapApplication(AppComponent, appConfig).catch((error: unknown) => {
  console.error('No se pudo iniciar Arbigen.', error);
  const root = document.querySelector('app-root');
  if (root) root.textContent = 'No se pudo iniciar la aplicación. Recarga la página para volver a intentarlo.';
});
