import { Component, OnDestroy, OnInit, AfterViewInit, PLATFORM_ID, inject } from '@angular/core';
import { CommonModule, DecimalPipe, isPlatformBrowser } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { MesureService, Mesure } from '../../services/mesure.service';
import { BaseChartDirective } from 'ng2-charts';
import { ChartConfiguration } from 'chart.js';

interface Stats {
  min: number;
  moy: number;
  max: number;
}

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, DecimalPipe, RouterModule, BaseChartDirective],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css',
})
export class DashboardComponent implements OnInit, AfterViewInit, OnDestroy {
  mesure: Mesure | null = this.getFakeMesure();
  currentTime = '';
  systemActive = false;

  tempStats: Stats = { min: 0, moy: 0, max: 0 };
  humStats: Stats = { min: 0, moy: 0, max: 0 };
  co2Stats: Stats = { min: 0, moy: 0, max: 0 };

  private subs: Subscription[] = [];
  private platformId = inject(PLATFORM_ID);

  chartLabels: string[] = [];
  chartDatasets: ChartConfiguration<'line'>['data']['datasets'] = [
    {
      data: [],
      label: 'Température (°C)',
      borderColor: '#e74c3c',
      backgroundColor: 'rgba(231,76,60,0.1)',
      tension: 0.4,
      fill: true,
    },
  ];
  chartOptions: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    scales: {
      x: { ticks: { maxTicksLimit: 10 } },
    },
  };

  constructor(private svc: MesureService) {}

  ngOnInit() {
    this.tickTime();

    if (isPlatformBrowser(this.platformId)) {
      this.subs.push(interval(1000).subscribe(() => this.tickTime()));
      this.subs.push(interval(5000).subscribe(() => this.refresh()));
    }
  }

  ngAfterViewInit() {
    if (isPlatformBrowser(this.platformId)) {
      setTimeout(() => this.refresh(), 0);
    }
  }

  private tickTime() {
    this.currentTime = new Date().toLocaleTimeString('fr-FR');
  }

  private refresh() {
    this.svc.getLast().subscribe({
      next: (d) => {
        this.mesure = d;
        this.systemActive = true;
      },
      error: () => {
        this.systemActive = false;
        this.mesure = this.getFakeMesure();
      },
    });

    this.svc.getAll().subscribe({
      next: (all) => {
        const data = all.length ? all : this.getFakeHistory(); 
        this.tempStats = this.stats(data.map((m) => m.temp));
        this.humStats = this.stats(data.map((m) => m.hum));
        this.co2Stats = this.stats(data.map((m) => m.co2));

        const last30 = data.slice(-30);
        this.chartLabels = last30.map((m) => this.fmt(m.timestamp)); 
        this.chartDatasets[0].data = last30.map((m) => m.temp);
      },
      error: () => {
        const fake = this.getFakeHistory();
        this.tempStats = this.stats(fake.map((m) => m.temp));
        this.humStats = this.stats(fake.map((m) => m.hum));
        this.co2Stats = this.stats(fake.map((m) => m.co2));

        const last30 = fake.slice(-30);
        this.chartLabels = last30.map((m) => this.fmt(m.timestamp));
        this.chartDatasets[0].data = last30.map((m) => m.temp);
      },
    });
  }

  // ─── Données fictives ─────────────────────────────────
  private getFakeMesure(): Mesure {
    return {
      temp: 20.4,
      hum: 52.1,
      co2: 620,
      motion: false,
      timestamp: new Date().toISOString(),
      outdoor_temp: 12.3,
      outdoor_hum: 68,
      wind_speed: 14.2,
    };
  }

  private getFakeHistory(): Mesure[] {
    const now = Date.now();
    return Array.from({ length: 30 }, (_, i) => {
      const ts = new Date(now - (30 - i) * 5 * 60 * 1000);
      const hour = ts.getHours();
      const factor = 8 <= hour && hour <= 18 ? 1 : 0.85;
      return {
        temp: parseFloat((19 + Math.random() * 3 * factor).toFixed(2)),
        hum: parseFloat((45 + Math.random() * 20).toFixed(1)),
        co2: Math.round(400 + Math.random() * 400 * factor),
        motion: Math.random() > 0.6,
        timestamp: ts.toISOString(),
        outdoor_temp: parseFloat((10 + Math.random() * 5).toFixed(1)),
        outdoor_hum: parseFloat((55 + Math.random() * 20).toFixed(1)),
        wind_speed: parseFloat((5 + Math.random() * 20).toFixed(1)),
      };
    });
  }

  private stats(values: number[]): Stats {
    if (!values.length) {
      return { min: 0, moy: 0, max: 0 };
    }

    return {
      min: Math.min(...values),
      max: Math.max(...values),
      moy: values.reduce((a, b) => a + b, 0) / values.length,
    };
  }

  fmt(ts: string): string {
    return ts ? new Date(ts).toLocaleTimeString('fr-FR') : '--:--:--';
  }

  ngOnDestroy() {
    this.subs.forEach((s) => s.unsubscribe());
  }
}
