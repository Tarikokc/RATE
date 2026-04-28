import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { App } from './app/app';
import { PwaService } from './app/pwa.service';

bootstrapApplication(App, appConfig)
  .then((appRef) => {
    const pwa = appRef.injector.get(PwaService);
    pwa.registerServiceWorker();
  })
  .catch((err) => console.error(err));
