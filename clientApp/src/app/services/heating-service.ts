// import { Injectable, inject, PLATFORM_ID } from '@angular/core';
// import { HttpClient } from '@angular/common/http';
// import { Observable } from 'rxjs';
// import { isPlatformServer } from '@angular/common';

// export interface HeatingDecision {
//   room: string;
//   current_temp: number | null;
//   decision: {
//     status: string;
//     label: string;
//     color: string;
//     action: string;
//     detail: string;
//   };
// }

// @Injectable({ providedIn: 'root' })
// export class HeatingService {
//   private http = inject(HttpClient);
//   private platformId = inject(PLATFORM_ID);

//   private get apiBase(): string {
//     return isPlatformServer(this.platformId) ? 'http://127.0.0.1:5000' : '';
//   }

//   getDecisions(): Observable<HeatingDecision[]> {
//     return this.http.get<HeatingDecision[]>(`${this.apiBase}/api/heating/decision`);
//   }
// }

import { Injectable, inject, PLATFORM_ID } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { isPlatformServer } from '@angular/common';


export interface HeatingDecision {
  room: string;
  current_temp: number | null;
  decision: {
    status: string;
    label: string;
    color: string;
    action: string;
    detail: string;
  };
}


@Injectable({ providedIn: 'root' })
export class HeatingService {
  private http = inject(HttpClient);
  private platformId = inject(PLATFORM_ID);

  private get apiBase(): string {
    return isPlatformServer(this.platformId)
      ? 'http://127.0.0.1:5000'
      : 'http://172.20.10.3:5000';
  }

  getDecisions(): Observable<HeatingDecision[]> {
    return this.http.get<HeatingDecision[]>(`${this.apiBase}/api/heating/decision`);
  }
}