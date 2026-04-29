import { Injectable, OnDestroy, inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';
import { take } from 'rxjs/operators';
import { MesureService, Mesure } from './mesure.service';
import { getSeverity } from './control-history';

export interface Toast { msg: string; level: 'warn' | 'danger'; id: number; }

@Injectable({ providedIn: 'root' })
export class NotificationService implements OnDestroy {

  toasts: Toast[] = [];
  private toastCounter = 0;
  private worker: Worker | null = null;
  private started = false;
  private platformId = inject(PLATFORM_ID);

  get desktopNotifs() { return localStorage.getItem('rate_notifs') === 'true'; }
  set desktopNotifs(val: boolean) {
    localStorage.setItem('rate_notifs', String(val));
    if (val && 'Notification' in window && Notification.permission === 'default') {
      Notification.requestPermission();
    }
  }

  constructor(private svc: MesureService) {}

  start() {
    if (!isPlatformBrowser(this.platformId)) return;
    if (this.started) return;
    this.started = true;

    if (typeof Worker !== 'undefined') {
      // Web Worker — pas throttlé en arrière-plan
      this.worker = new Worker(new URL('./poll.worker', import.meta.url), { type: 'module' });
      this.worker.onmessage = ({ data }) => {
        if (data.type === 'tick') this.poll();
      };
      this.worker.postMessage({ type: 'start', ms: 30_000 });
    } else {
      // Fallback si Web Worker non supporté
      this.poll();
      setInterval(() => this.poll(), 30_000);
    }
  }

  ngOnDestroy() {
    this.worker?.postMessage({ type: 'stop' });
    this.worker?.terminate();
  }

  private poll() {
    this.svc.getLast().pipe(take(1)).subscribe({
      next: m => this.handleSeverity(m),
      error: () => {}
    });
  }

  private handleSeverity(m: Mesure) {
    const level = getSeverity(m);
    if (level === 'ok') return; // rien à signaler

    const reasons: string[] = [];
    if (m.temp >= 28)      reasons.push(`🌡️ Température trop élevée (${m.temp.toFixed(1)}°C)`);
    else if (m.temp <= 16) reasons.push(`🥶 Température trop basse (${m.temp.toFixed(1)}°C)`);
    else if (m.temp >= 25) reasons.push(`🌡️ Température élevée (${m.temp.toFixed(1)}°C)`);
    else if (m.temp <= 18) reasons.push(`🌡️ Température basse (${m.temp.toFixed(1)}°C)`);

    if (m.co2 >= 1200)     reasons.push(`💨 CO2 critique (${Math.round(m.co2)} ppm)`);
    else if (m.co2 >= 800) reasons.push(`💨 CO2 élevé (${Math.round(m.co2)} ppm)`);

    if (m.hum >= 70)       reasons.push(`💧 Humidité trop élevée (${Math.round(m.hum)}%)`);
    else if (m.hum <= 25)  reasons.push(`💧 Air trop sec (${Math.round(m.hum)}%)`);
    else if (m.hum >= 60)  reasons.push(`💧 Humidité haute (${Math.round(m.hum)}%)`);
    else if (m.hum <= 35)  reasons.push(`💧 Humidité basse (${Math.round(m.hum)}%)`);

    if (!reasons.length) return;

    const msg = reasons.join(' · ');
    const title = level === 'danger' ? '🚨 Alerte critique RATE' : '⚠️ Alerte RATE';

    this.addToast(msg, level as 'warn' | 'danger');
    this.sendDesktopNotif(title, msg);
  }

  addToast(msg: string, level: 'warn' | 'danger') {
    const id = ++this.toastCounter;
    this.toasts.push({ msg, level, id });
    setTimeout(() => this.dismissToast(id), 5000);
  }

  dismissToast(id: number) {
    this.toasts = this.toasts.filter(t => t.id !== id);
  }

  private sendDesktopNotif(title: string, body: string) {
    if (!this.desktopNotifs) return;
    if (!('Notification' in window)) return;
    if (Notification.permission === 'granted') {
      new Notification(title, { body, icon: '/favicon.ico' });
    }
  }
}