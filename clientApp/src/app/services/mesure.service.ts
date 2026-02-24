import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface Mesure {
  temp: number;
  hum: number;
  pres: number;
  motion: boolean;
  timestamp: string;
}

@Injectable({ providedIn: 'root' })
export class MesureService {
  constructor(private http: HttpClient) {}
  getLast(): Observable<Mesure>   { return this.http.get<Mesure>('/api/last'); }
  getAll():  Observable<Mesure[]> { return this.http.get<Mesure[]>('/api/all'); }
}
