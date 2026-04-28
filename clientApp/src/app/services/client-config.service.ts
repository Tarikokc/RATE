import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, shareReplay } from 'rxjs';
import { isPlatformServer } from '@angular/common';

export interface OrgConfig {
  name: string;
  type: string;
  logo: string;
  address: string;
  contact: string;
}

export interface Thresholds {
  co2:         { warning: number; critical: number };
  temperature: { min: number; max: number };
  humidity:    { min: number; max: number };
}

export interface RoomTemplate {
  name: string;
  floor: string;
  description: string;
  capacity: number;
}

export interface ClientConfig {
  organisation: OrgConfig;
  thresholds:   Thresholds;
  rooms:        RoomTemplate[];
}

@Injectable({ providedIn: 'root' })
export class ClientConfigService {
  private http       = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);

  private get apiBase(): string {
    return isPlatformServer(this.platformId) ? 'http://127.0.0.1:5000' : '';
  }

  // Mise en cache : un seul appel HTTP pour toute la session
  private config$: Observable<ClientConfig> | null = null;

  getConfig(): Observable<ClientConfig> {
    if (!this.config$) {
      this.config$ = this.http
        .get<ClientConfig>(`${this.apiBase}/api/client-config`)
        .pipe(shareReplay(1));
    }
    return this.config$;
  }
}
