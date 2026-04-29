// import { Component } from '@angular/core';
// import { RouterOutlet } from '@angular/router';
// import { isPlatformServer } from '@angular/common';
// import { inject, PLATFORM_ID } from '@angular/core';

// @Component({
//   selector: 'app-root',
//   standalone: true,
//   imports: [RouterOutlet],
//   template: '<router-outlet />'
// })

// export class App {
//   private platformId = inject(PLATFORM_ID);

//   private get apiBase(): string {
//     return isPlatformServer(this.platformId) ? 'http://127.0.0.1:5000' : '';
//   }
// }

import { Component } from '@angular/core';
import { RouterOutlet, Router } from '@angular/router';
import { isPlatformServer, CommonModule } from '@angular/common';
import { inject, PLATFORM_ID, afterNextRender } from '@angular/core';
import { NotificationService } from './services/notification.service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, CommonModule],
  template: `
    <router-outlet />

    <div class="toast-container" aria-live="polite">
      @for (t of notifSvc.toasts; track t.id) {
        <div class="toast" [ngClass]="t.level">
          <span class="toast-msg">{{ t.msg }}</span>
          <button class="toast-close" (click)="notifSvc.dismissToast(t.id)">✕</button>
        </div>
      }
    </div>
  `,
  styles: [`
    .toast-container {
      position: fixed;
      bottom: 1.5rem;
      right: 1.5rem;
      display: flex;
      flex-direction: column;
      gap: .6rem;
      z-index: 9999;
      max-width: min(360px, calc(100vw - 2rem));
    }
    .toast {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: .75rem;
      padding: .85rem 1rem;
      border-radius: 14px;
      font-weight: 800;
      font-size: .88rem;
      border: 1px solid;
      backdrop-filter: blur(12px);
      box-shadow: 0 8px 24px rgba(0,0,0,.4);
      animation: toastIn .25s cubic-bezier(0.16,1,0.3,1);
    }
    .toast.warn   { background: rgba(245,158,11,.12); border-color: rgba(245,158,11,.35); color: #f59e0b; }
    .toast.danger { background: rgba(239,68,68,.12);  border-color: rgba(239,68,68,.35);  color: #ef4444; }
    .toast-msg    { flex: 1; line-height: 1.4; }
    .toast-close  { background: none; border: none; color: inherit; opacity: .6; cursor: pointer; font-size: .8rem; padding: 0; transition: opacity .15s; }
    .toast-close:hover { opacity: 1; }
    @keyframes toastIn { from { transform: translateX(110%); opacity: 0; } to { transform: none; opacity: 1; } }
    @media (max-width: 480px) {
      .toast-container { bottom: 1rem; right: 1rem; left: 1rem; max-width: none; }
    }
  `]
})
export class App {
  private platformId = inject(PLATFORM_ID);
  public notifSvc = inject(NotificationService);

  constructor() {
    afterNextRender(() => {
      if (!isPlatformServer(this.platformId)) {
        this.notifSvc.start();
      }
    });
  }
}