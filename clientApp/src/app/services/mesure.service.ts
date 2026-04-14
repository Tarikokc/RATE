import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { isPlatformServer } from '@angular/common';

export interface Mesure {
  temp: number;
  hum: number;
  co2: number;
  motion: boolean;
  timestamp: string;

  outdoor_temp: number;
  outdoor_hum: number;
  wind_speed: number;
}

@Injectable({ providedIn: 'root' })
export class MesureService {
  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);

  // Base URL de l'API Flask
  private get apiBase(): string {
    if (isPlatformServer(this.platformId)) {
      return 'http://127.0.0.1:5000';
    }
    // IP de ta machine Flask sur le réseau
    return 'http://172.20.10.3:5000';
  }

  getLast(): Observable<Mesure> {
    return this.http.get<Mesure>(`${this.apiBase}/api/last`);
  }

  getAll(): Observable<Mesure[]> {
    return this.http.get<Mesure[]>(`${this.apiBase}/api/all`);
  }
}