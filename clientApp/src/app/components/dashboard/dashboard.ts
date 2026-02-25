import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule, DecimalPipe } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { MesureService, Mesure } from '../../services/mesure.service';

interface Stats { min: number; moy: number; max: number; }

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, DecimalPipe, RouterModule],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class DashboardComponent implements OnInit, OnDestroy {
  mesure: Mesure | null = null;
  currentTime = '';
  systemActive = false;
  tempStats: Stats = { min: 0, moy: 0, max: 0 };
  humStats:  Stats = { min: 0, moy: 0, max: 0 };
  presStats: Stats = { min: 0, moy: 0, max: 0 };
  private subs: Subscription[] = [];

  constructor(private svc: MesureService) {}

  ngOnInit() {
    this.tickTime();
    this.subs.push(interval(1000).subscribe(() => this.tickTime()));
    this.refresh();
    this.subs.push(interval(5000).subscribe(() => this.refresh()));
  }

  private tickTime() {
    this.currentTime = new Date().toLocaleTimeString('fr-FR');
  }

  private refresh() {
    this.svc.getLast().subscribe({
      next: (d) => { this.mesure = d; this.systemActive = true; },
      error: ()  => { this.systemActive = false; }
    });
    this.svc.getAll().subscribe({
      next: (all) => {
        this.tempStats = this.stats(all.map(m => m.temperature));
        this.humStats  = this.stats(all.map(m => m.humidity));
        this.presStats = this.stats(all.map(m => m.co2));
      }
    });
  }

  private stats(v: number[]): Stats {
    if (!v.length) return { min: 0, moy: 0, max: 0 };
    return {
      min: Math.min(...v),
      max: Math.max(...v),
      moy: v.reduce((a, b) => a + b, 0) / v.length
    };
  }

  fmt(ts: string): string {
    return ts ? new Date(ts).toLocaleTimeString('fr-FR') : '--:--:--';
  }

  ngOnDestroy() { this.subs.forEach(s => s.unsubscribe()); }
}
