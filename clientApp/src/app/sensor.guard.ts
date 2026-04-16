import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { SensorService } from './services/sensor.service';
import { map, catchError } from 'rxjs/operators';
import { of } from 'rxjs';

export const sensorGuard: CanActivateFn = () => {
  const svc    = inject(SensorService);
  const router = inject(Router);

  return svc.getAll().pipe(
    map(sensors => {
      if (sensors.length > 0) return true;
      router.navigate(['/']);
      return false;
    }),
    catchError(() => {
      // Flask injoignable → laisse passer (mode offline/fake data)
      return of(true);
    })
  );
};