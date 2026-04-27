import {
  Component, OnDestroy, OnInit, AfterViewInit,
  PLATFORM_ID, inject, ChangeDetectorRef
} from '@angular/core';
import { CommonModule, DecimalPipe, isPlatformBrowser } from '@angular/common';
import { RouterModule } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { MesureService, Mesure } from '../../services/mesure.service';
import { ClientConfigService, ClientConfig } from '../../services/client-config.service';
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
  mesure: Mesure | null = null;
  currentTime = '';
  systemActive = false;
  loading = true;

  // Config client
  clientConfig: ClientConfig | null = null;
  orgName = 'RATE Dashboard';

  // Seuils (valeurs par défaut, écrasées par la config)
  co2Warning  = 1000;
  co2Critical = 1500;
  tempMin     = 18;
  tempMax     = 22;
  humMin      = 30;
  humMax      = 65;

  tempStats: Stats = { min: 0, moy: 0, max: 0 };
  humStats:  Stats = { min: 0, moy: 0, max: 0 };
  co2Stats:  Stats = { min: 0, moy: 0, max: 0 };

  private subs: Subscription[] = [];
  private platformId  = inject(PLATFORM_ID);
  private cdr         = inject(ChangeDetectorRef);
  private configSvc   = inject(ClientConfigService);

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
    scales: { x: { ticks: { maxTicksLimit: 10 } } },
  };

  constructor(private svc: MesureService) {}

  ngOnInit() {
    this.tickTime();
    // Charge la config client en premier
    this.configSvc.getConfig().subscribe({
      next: (cfg) => {
        this.clientConfig = cfg;
        this.orgName      = cfg.organisation.name;
        this.co2Warning   = cfg.thresholds.co2.warning;
        this.co2Critical  = cfg.thresholds.co2.critical;
        this.tempMin      = cfg.thresholds.temperature.min;
        this.tempMax      = cfg.thresholds.temperature.max;
        this.humMin       = cfg.thresholds.humidity.min;
        this.humMax       = cfg.thresholds.humidity.max;
        this.cdr.detectChanges();
      },
      error: () => { /* garde les valeurs par défaut */ }
    });

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

  // ─── Statut alerte CO2 ────────────────────────────────────
  get co2Status(): 'ok' | 'warning' | 'critical' {
    if (!this.mesure) return 'ok';
    if (this.mesure.co2 >= this.co2Critical) return 'critical';
    if (this.mesure.co2 >= this.co2Warning)  return 'warning';
    return 'ok';
  }

  // ─── Statut alerte température ────────────────────────────
  get tempStatus(): 'ok' | 'warning' {
    if (!this.mesure) return 'ok';
    if (this.mesure.temp < this.tempMin || this.mesure.temp > this.tempMax) return 'warning';
    return 'ok';
  }

  // ─── Statut alerte humidité ───────────────────────────────
  get humStatus(): 'ok' | 'warning' {
    if (!this.mesure) return 'ok';
    if (this.mesure.hum < this.humMin || this.mesure.hum > this.humMax) return 'warning';
    return 'ok';
  }

  private refresh() {
    this.svc.getLast().subscribe({
      next: (d) => {
        this.mesure       = d;
        this.systemActive = true;
        this.loading      = false;
        this.cdr.detectChanges();
        this.loadHistory();
      },
      error: () => {
        this.systemActive = false;
        this.loading      = false;
        this.mesure = this.getFakeMesure();
        this.cdr.detectChanges();
        this.loadHistory();
      },
    });
  }

  private loadHistory() {
    const sensorId =
      this.mesure?.sensor_id ??
      (this.mesure as any)?.sensor ??
      undefined;

    this.svc.getAll(sensorId).subscribe({
      next: (all) => {
        const filtered = sensorId
          ? all.filter((m) => (m.sensor_id ?? (m as any).sensor) === sensorId)
          : all;
        this.applyHistory(filtered.length ? filtered : this.getFakeHistory());
      },
      error: () => this.applyHistory(this.getFakeHistory()),
    });
  }

  private applyHistory(data: Mesure[]) {
    this.tempStats = this.stats(data.map((m) => m.temp));
    this.humStats  = this.stats(data.map((m) => m.hum));
    this.co2Stats  = this.stats(data.map((m) => m.co2));

    const last30 = data.slice(-30);
    this.chartLabels           = last30.map((m) => this.fmt(m.timestamp));
    this.chartDatasets[0].data = last30.map((m) => m.temp);
    this.cdr.detectChanges();
  }

  private getFakeMesure(): Mesure {
    return {
      temp: 20.4, hum: 52.1, co2: 620, motion: false,
      timestamp: new Date().toISOString(),
      outdoor_temp: 12.3, outdoor_hum: 68, wind_speed: 14.2,
    };
  }

  private getFakeHistory(): Mesure[] {
    const now = Date.now();
    return Array.from({ length: 30 }, (_, i) => {
      const ts     = new Date(now - (30 - i) * 5 * 60 * 1000);
      const hour   = ts.getHours();
      const factor = 8 <= hour && hour <= 18 ? 1 : 0.85;
      return {
        temp:         parseFloat((19 + Math.random() * 3 * factor).toFixed(2)),
        hum:          parseFloat((45 + Math.random() * 20).toFixed(1)),
        co2:          Math.round(400 + Math.random() * 400 * factor),
        motion:       Math.random() > 0.6,
        timestamp:    ts.toISOString(),
        outdoor_temp: parseFloat((10 + Math.random() * 5).toFixed(1)),
        outdoor_hum:  parseFloat((55 + Math.random() * 20).toFixed(1)),
        wind_speed:   parseFloat((5 + Math.random() * 20).toFixed(1)),
      };
    });
  }

  private stats(values: number[]): Stats {
    if (!values.length) return { min: 0, moy: 0, max: 0 };
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
