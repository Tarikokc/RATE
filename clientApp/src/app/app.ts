import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { isPlatformServer } from '@angular/common';
import { inject, PLATFORM_ID } from '@angular/core';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet],
  template: '<router-outlet />'
})

export class App {
  private platformId = inject(PLATFORM_ID);

  private get apiBase(): string {
    return isPlatformServer(this.platformId) ? 'http://127.0.0.1:5000' : '';
  }
}