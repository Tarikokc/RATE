// import {
//   Component,
//   OnDestroy,
//   OnInit,
//   AfterViewInit,
//   PLATFORM_ID,
//   inject
// } from '@angular/core';
// import { CommonModule, DecimalPipe } from '@angular/common';
// import { RouterModule } from '@angular/router';
// import { Subscription, interval } from 'rxjs';
// import { MesureService, Mesure } from '../../services/mesure.service';
// import { isPlatformBrowser } from '@angular/common';

// interface Stats { min: number; moy: number; max: number; }

// @Component({
//   selector: 'app-dashboard',
//   standalone: true,
//   imports: [CommonModule, DecimalPipe, RouterModule],
//   templateUrl: './dashboard.html',
//   styleUrl: './dashboard.css'
// })
// export class DashboardComponent implements OnInit, AfterViewInit, OnDestroy {
//   mesure: Mesure | null = null;
//   currentTime = '';
//   systemActive = false;
//   tempStats: Stats = { min: 0, moy: 0, max: 0 };
//   humStats:  Stats = { min: 0, moy: 0, max: 0 };
//   co2Stats: Stats = { min: 0, moy: 0, max: 0 };
//   private subs: Subscription[] = [];

//   constructor(private svc: MesureService) {}
//   private platformId = inject(PLATFORM_ID);

//   ngOnInit() {
//     this.tickTime();

//     if (isPlatformBrowser(this.platformId)) {
//       // JUSTE les timers ici, PAS de refresh immédiat
//       this.subs.push(interval(1000).subscribe(() => this.tickTime()));
//       this.subs.push(interval(5000).subscribe(() => this.refresh()));
//     }
//   }

//   ngAfterViewInit() {
//     if (isPlatformBrowser(this.platformId)) {
//       // Premier refresh APRES le 1er rendu → plus de NG0100
//       setTimeout(() => this.refresh(), 0);
//     }
//   }

//   private tickTime() {
//     this.currentTime = new Date().toLocaleTimeString('fr-FR');
//   }

//   // private refresh() {
//   //   this.svc.getLast().subscribe({
//   //     next: (d) => {
//   //       this.mesure = d;
//   //       this.systemActive = true;
//   //     },
//   //     error: () => {
//   //       this.systemActive = false;
//   //     }
//   //   });

//   //   this.svc.getAll().subscribe({
//   //     next: (all) => {
//   //       this.tempStats = this.stats(all.map(m => m.temp));
//   //       this.humStats  = this.stats(all.map(m => m.hum));
//   //       this.co2Stats = this.stats(all.map(m => m.co2));
//   //     }
//   //   });
//   // }
//   private refresh() {
//   this.svc.getLast().subscribe({
//     next: (d) => {
//       console.log('[DASH] last =', d);
//       this.mesure = d;
//       this.systemActive = true;
//     },
//     error: (err) => {
//       console.error('[DASH] getLast error', err);
//       this.systemActive = false;
//     }
//   });

//   this.svc.getAll().subscribe({
//     next: (all) => {
//       console.log('[DASH] all =', all);
//       this.tempStats = this.stats(all.map(m => m.temp));
//       this.humStats  = this.stats(all.map(m => m.hum));
//       this.co2Stats  = this.stats(all.map(m => m.co2));
//     },
//     error: (err) => console.error('[DASH] getAll error', err)
//   });
//   } 

//   private stats(v: number[]): Stats {
//     if (!v.length) return { min: 0, moy: 0, max: 0 };
//     return {
//       min: Math.min(...v),
//       max: Math.max(...v),
//       moy: v.reduce((a, b) => a + b, 0) / v.length
//     };
//   }

//   fmt(ts: string): string {
//     return ts ? new Date(ts).toLocaleTimeString('fr-FR') : '--:--:--';
//   }

//   ngOnDestroy() { this.subs.forEach(s => s.unsubscribe()); }
// }

import {
  Component,
  OnDestroy,
  OnInit,
  AfterViewInit,
  PLATFORM_ID,
  inject
} from '@angular/core';
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
  imports: [CommonModule, DecimalPipe, RouterModule,BaseChartDirective],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class DashboardComponent implements OnInit, AfterViewInit, OnDestroy {
  mesure: Mesure | null = null;
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
    }
  ];
  chartOptions: ChartConfiguration<'line'>['options'] = {
    responsive: true,
    scales: {
      x: { ticks: { maxTicksLimit: 10 } }
    }
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
        console.log('[DASH] last =', d);
        this.mesure = d;
        this.systemActive = true;
      },
      error: (err) => {
        console.error('[DASH] getLast error', err);
        this.systemActive = false;
      }
    });

    this.svc.getAll().subscribe({
      next: (all) => {
        console.log('[DASH] all =', all);
        this.tempStats = this.stats(all.map(m => m.temp));
        this.humStats = this.stats(all.map(m => m.hum));
        this.co2Stats = this.stats(all.map(m => m.co2));
      },
      error: (err) => {
        console.error('[DASH] getAll error', err);
      }
    });

    this.svc.getAll().subscribe({
      next: (all) => {
        this.co2Stats = this.stats(all.map(m => m.co2));
        this.tempStats = this.stats(all.map(m => m.temp));
        this.humStats  = this.stats(all.map(m => m.hum));

        const last30 = all.slice(-30);
        this.chartLabels   = last30.map(m => this.fmt(m.timestamp));
        this.chartDatasets[0].data = last30.map(m => m.temp);
      }
    });
  }

  private stats(values: number[]): Stats {
    if (!values.length) {
      return { min: 0, moy: 0, max: 0 };
    }

    return {
      min: Math.min(...values),
      max: Math.max(...values),
      moy: values.reduce((a, b) => a + b, 0) / values.length
    };
  }

  fmt(ts: string): string {
    return ts ? new Date(ts).toLocaleTimeString('fr-FR') : '--:--:--';
  }

  ngOnDestroy() {
    this.subs.forEach(s => s.unsubscribe());
  }
}
