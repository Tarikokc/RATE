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
  sensor_id?: string;
  sensor?: string; // rétrocompat ancienne clé
}

@Injectable({ providedIn: 'root' })
export class MesureService {
  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);

  private get apiBase(): string {
    if (isPlatformServer(this.platformId)) {
      return 'http://127.0.0.1:5000';
    }
    return 'http://172.20.10.8:5000';
  }

  getLast(): Observable<Mesure> {
    return this.http.get<Mesure>(`${this.apiBase}/api/last`);
  }

  // Filtre directement côté serveur par sensor_id si fourni
  getAll(sensorId?: string): Observable<Mesure[]> {
    const url = sensorId
      ? `${this.apiBase}/api/measures?sensor_id=${encodeURIComponent(sensorId)}`
      : `${this.apiBase}/api/all`;
    return this.http.get<Mesure[]>(url);
  }
}