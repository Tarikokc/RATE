import { Component, OnInit, OnDestroy } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule, DecimalPipe } from '@angular/common';
import { Subscription, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';

interface Mesure {
  temp: number;
  hum: number;
  pres: number;
  motion: boolean;
  timestamp: string;
}

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, DecimalPipe],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App implements OnInit, OnDestroy {
  mesure: Mesure | null = null;
  status = 'Chargement...';
  private sub: Subscription | null = null;

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.charger(); 
    this.sub = interval(5000).pipe(
      switchMap(() => this.http.get<Mesure>('/api/last'))
    ).subscribe({
      next: (data) => this.mettreAJour(data),
      error: () => { this.status = 'Erreur de connexion au serveur'; }
    });
  }

  charger() {
    this.http.get<Mesure>('/api/last').subscribe({
      next: (data) => this.mettreAJour(data),
      error: () => { this.status = 'Erreur de connexion au serveur'; }
    });
  }

  private mettreAJour(data: Mesure) {
    this.mesure = data;
    this.status = 'Dernière mise à jour : ' + new Date().toLocaleTimeString();
  }

  ngOnDestroy() {
    this.sub?.unsubscribe();
  }
}
