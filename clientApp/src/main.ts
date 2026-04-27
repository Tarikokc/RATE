import { bootstrapApplication } from '@angular/platform-browser';
import { appConfig } from './app/app.config';
import { AppComponent } from './app/app.component';
import { PwaService } from './app/pwa.service';

bootstrapApplication(AppComponent, appConfig)
  .then((appRef) => {
    const pwa = appRef.injector.get(PwaService);
    pwa.registerServiceWorker();
  })
  .catch((err) => console.error(err));
