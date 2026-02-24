import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

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
  constructor(private http: HttpClient) {}

  getRooms(): Observable<Room[]> {
    return this.http.get<Room[]>('/api/rooms');
  }

  getReservations(date?: string, roomId?: number): Observable<Reservation[]> {
    const params: any = {};
    if (date)   params['date']    = date;
    if (roomId) params['room_id'] = roomId;
    return this.http.get<Reservation[]>('/api/reservations', { params });
  }

  createReservation(r: Reservation): Observable<Reservation> {
    return this.http.post<Reservation>('/api/reservations', r);
  }

  deleteReservation(id: number): Observable<void> {
    return this.http.delete<void>(`/api/reservations/${id}`);
  }
}
