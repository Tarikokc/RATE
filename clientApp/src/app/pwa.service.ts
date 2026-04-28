import { Injectable } from '@angular/core';

@Injectable({ providedIn: 'root' })
export class PwaService {

  registerServiceWorker(): void {
    if ('serviceWorker' in navigator) {
      window.addEventListener('load', () => {
        navigator.serviceWorker
          .register('/sw.js')
          .then((reg) => console.log('[PWA] Service Worker enregistré :', reg.scope))
          .catch((err) => console.warn('[PWA] Erreur SW :', err));
      });
    }
  }
}
