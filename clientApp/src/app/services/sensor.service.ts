// import { Injectable, inject, PLATFORM_ID } from '@angular/core';
// import { HttpClient } from '@angular/common/http';
// import { Observable } from 'rxjs';
// import { isPlatformServer } from '@angular/common';

// export interface Sensor {
//   id?: number;
//   name: string;
//   floor: string;
//   description?: string;
//   sensor_id: string;
//   capacity?: number;
// }

// export interface AvailableSensor {
//   sensor_id: string;
//   last_seen: string;
// }

// @Injectable({ providedIn: 'root' })
// export class SensorService {
//   private http = inject(HttpClient);
//   private platformId = inject(PLATFORM_ID);

//   private get apiBase(): string {
//     if (isPlatformServer(this.platformId)) {
//       return 'http://127.0.0.1:5000';
//     }
//     return 'http://192.168.1.94:5000';
//   }

//   getAll(): Observable<Sensor[]> {
//     return this.http.get<Sensor[]>(`${this.apiBase}/api/rooms`);
//   }

//   create(s: Sensor): Observable<Sensor> {
//     return this.http.post<Sensor>(`${this.apiBase}/api/rooms`, s);
//   }

//   delete(id: number): Observable<void> {
//     return this.http.delete<void>(`${this.apiBase}/api/rooms/${id}`);
//   }

//   getAvailableSensors(): Observable<AvailableSensor[]> {
//     return this.http.get<AvailableSensor[]>(`${this.apiBase}/api/sensors/available`);
//   }

//   // Associe un capteur ESP à une salle existante
//   assignSensor(roomId: number, sensorId: string): Observable<any> {
//     return this.http.patch(`${this.apiBase}/api/rooms/${roomId}`, { sensor_id: sensorId });
//   }
// }

import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { isPlatformServer } from '@angular/common';

export interface Sensor {
  id?: number;
  name: string;
  floor: string;
  description?: string;
  sensor_id: string;
  capacity?: number;
}

export interface AvailableSensor {
  sensor_id: string;
  last_seen: string;
}

@Injectable({ providedIn: 'root' })
export class SensorService {
  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);

  private get apiBase(): string {
    return isPlatformServer(this.platformId) ? 'http://127.0.0.1:5000' : '';
  }

  getAll(): Observable<Sensor[]> {
    return this.http.get<Sensor[]>(`${this.apiBase}/api/rooms`);
  }

  create(s: Sensor): Observable<Sensor> {
    return this.http.post<Sensor>(`${this.apiBase}/api/rooms`, s);
  }

  delete(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiBase}/api/rooms/${id}`);
  }

  getAvailableSensors(): Observable<AvailableSensor[]> {
    return this.http.get<AvailableSensor[]>(`${this.apiBase}/api/sensors/available`);
  }

  assignSensor(roomId: number, sensorId: string): Observable<any> {
    return this.http.patch(`${this.apiBase}/api/rooms/${roomId}`, { sensor_id: sensorId });
  }
}