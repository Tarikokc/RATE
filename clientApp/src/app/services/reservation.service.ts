// import { Injectable, inject, PLATFORM_ID } from '@angular/core';
// import { HttpClient } from '@angular/common/http';
// import { Observable } from 'rxjs';
// import { isPlatformServer } from '@angular/common';


// export interface Room {
//   id: number;
//   name: string;
//   capacity: number;
//   floor: string;
//   description: string;
// }


// export interface Reservation {
//   id?: number;
//   room_id: number;
//   room_name?: string;
//   user_name: string;
//   title: string;
//   start_datetime: string;
//   end_datetime: string;
//   people_count: number;
// }


// @Injectable({ providedIn: 'root' })
// export class ReservationService {
//   private http = inject(HttpClient);
//   private platformId = inject(PLATFORM_ID);

//   private get apiBase(): string {
//     return isPlatformServer(this.platformId)
//       ? 'http://127.0.0.1:5000'
//       : 'http://192.168.1.94:5000';
//   }

//   getRooms(): Observable<Room[]> {
//     return this.http.get<Room[]>(`${this.apiBase}/api/rooms`);
//   }

//   getReservations(date?: string, roomId?: number): Observable<Reservation[]> {
//     const params: any = {};
//     if (date)   params['date']    = date;
//     if (roomId) params['room_id'] = roomId;
//     return this.http.get<Reservation[]>(`${this.apiBase}/api/reservations`, { params });
//   }

//   createReservation(r: Reservation): Observable<Reservation> {
//     return this.http.post<Reservation>(`${this.apiBase}/api/reservations`, r);
//   }

//   deleteReservation(id: number): Observable<void> {
//     return this.http.delete<void>(`${this.apiBase}/api/reservations/${id}`);
//   }
// }

import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { isPlatformServer } from '@angular/common';

export interface Room {
  id: number;
  name: string;
  capacity: number;
  floor: string;
  description: string;
}

export interface Reservation {
  id?: number;
  room_id: number;
  room_name?: string;
  user_name: string;
  title: string;
  start_datetime: string;
  end_datetime: string;
  people_count: number;
}

@Injectable({ providedIn: 'root' })
export class ReservationService {
  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);

  private get apiBase(): string {
    return isPlatformServer(this.platformId) ? 'http://127.0.0.1:5000' : '';
  }

  getRooms(): Observable<Room[]> {
    return this.http.get<Room[]>(`${this.apiBase}/api/rooms`);
  }

  getReservations(date?: string, roomId?: number): Observable<Reservation[]> {
    const params: any = {};
    if (date)   params['date']    = date;
    if (roomId) params['room_id'] = roomId;
    return this.http.get<Reservation[]>(`${this.apiBase}/api/reservations`, { params });
  }

  createReservation(r: Reservation): Observable<Reservation> {
    return this.http.post<Reservation>(`${this.apiBase}/api/reservations`, r);
  }

  deleteReservation(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiBase}/api/reservations/${id}`);
  }
}