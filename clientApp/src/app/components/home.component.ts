// import { Component, OnInit, inject, PLATFORM_ID } from '@angular/core';
// import { CommonModule, isPlatformBrowser } from '@angular/common';
// import { FormsModule } from '@angular/forms';
// import { Router, RouterModule } from '@angular/router';
// import { SensorService, Sensor } from '../services/sensor.service';
// import { take } from 'rxjs/operators';

// @Component({
//   selector: 'app-home',
//   standalone: true,
//   imports: [CommonModule, FormsModule, RouterModule],
//   templateUrl: './home.component.html',
//   styleUrl: './home.component.css'
// })
// export class HomeComponent implements OnInit {
//   private svc        = inject(SensorService);
//   private router     = inject(Router);
//   private platformId = inject(PLATFORM_ID);

//   sensors: Sensor[] = [];
//   loading  = true;
//   showForm = false;
//   errorMsg = '';
//   success  = '';

//   form: Sensor = { name: '', floor: '', description: '', sensor_id: '' };

//   ngOnInit() {
//     if (isPlatformBrowser(this.platformId)) {
//       this.loadSensors();
//     }
//   }

//   loadSensors() {
//     this.loading = true;
//     this.svc.getAll().pipe(take(1)).subscribe({
//       next:  s  => { this.sensors = s; this.loading = false; },
//       error: () => { this.sensors = []; this.loading = false; }
//     });
//   }

//   openForm()  { this.showForm = true; this.errorMsg = ''; this.success = ''; }
//   closeForm() { this.showForm = false; this.resetForm(); }

//   submit() {
//     if (!this.form.name || !this.form.sensor_id || !this.form.floor) {
//       this.errorMsg = 'Nom, étage et sensor_id sont requis.';
//       return;
//     }
//     this.svc.create(this.form).pipe(take(1)).subscribe({
//       next: () => {
//         this.success = `Capteur "${this.form.name}" ajouté !`;
//         this.resetForm();
//         this.showForm = false;
//         this.loadSensors();
//       },
//       error: () => { this.errorMsg = 'Erreur lors de l\'ajout.'; }
//     });
//   }

//   delete(id: number, name: string) {
//     if (!confirm(`Supprimer le capteur "${name}" ?`)) return;
//     this.svc.delete(id).pipe(take(1)).subscribe(() => this.loadSensors());
//   }

//   goToDashboard() { this.router.navigate(['/dashboard']); }

//   private resetForm() {
//     this.form = { name: '', floor: '', description: '', sensor_id: '' };
//   }
// }

import { Component, AfterViewInit, inject, PLATFORM_ID } from '@angular/core';
import { CommonModule, isPlatformBrowser } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { SensorService, Sensor } from '../services/sensor.service';
import { take } from 'rxjs/operators';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent implements AfterViewInit {
  private svc = inject(SensorService);
  private router = inject(Router);
  private platformId = inject(PLATFORM_ID);

  sensors: Sensor[] = [];
  loading = false;
  flaskDown = false;
  showForm = false;
  errorMsg = '';
  success = '';

  form: Sensor = {
    name: '',
    floor: '',
    description: '',
    sensor_id: '',
  };

  ngAfterViewInit() {
    if (isPlatformBrowser(this.platformId)) {
      setTimeout(() => this.loadSensors(), 0);
    }
  }
  loadSensors() {
    console.log('[HOME] loadSensors start');
    this.loading = true;
    this.flaskDown = false;
    this.showForm = false; // important

    this.svc
      .getAll()
      .pipe(take(1))
      .subscribe({
        next: (s) => {
          console.log('[HOME] sensors =', s);
          this.sensors = s;
          this.loading = false;
          this.flaskDown = false;
          this.showForm = s.length === 0;
        },
        error: (err) => {
          console.error('[HOME] getAll error', err);
          this.sensors = [];
          this.loading = false;
          this.flaskDown = true;
          this.showForm = false;
        },
      });
  }
  //   loadSensors() {
  //     console.log('[HOME] loadSensors start');
  //     this.loading = true;
  //     this.flaskDown = false;

  //     this.svc.getAll().pipe(take(1)).subscribe({
  //       next: (s) => {
  //         console.log('[HOME] sensors =', s);
  //         this.sensors = s;
  //         this.loading = false;
  //         this.flaskDown = false;
  //         this.showForm = s.length === 0;
  //       },
  //       error: (err) => {
  //         console.error('[HOME] getAll error', err);
  //         this.loading = false;
  //         this.flaskDown = true;
  //         this.showForm = true;
  //       }
  //     });
  //   }

  openForm() {
    this.showForm = true;
    this.errorMsg = '';
    this.success = '';
  }

  closeForm() {
    if (this.sensors.length === 0) return;
    this.showForm = false;
    this.resetForm();
  }

  submit() {
    if (!this.form.name || !this.form.floor || !this.form.sensor_id) {
      this.errorMsg = 'Nom, étage et sensor_id sont requis.';
      return;
    }

    this.svc
      .create(this.form)
      .pipe(take(1))
      .subscribe({
        next: () => {
          this.success = `Capteur "${this.form.name}" ajouté`;
          this.errorMsg = '';
          this.resetForm();
          this.loadSensors();
        },
        error: (err) => {
          console.error('[HOME] create error', err);
          this.errorMsg = 'Erreur lors de l’ajout du capteur.';
        },
      });
  }

  delete(id: number, name: string) {
    if (!confirm(`Supprimer le capteur "${name}" ?`)) return;

    this.svc
      .delete(id)
      .pipe(take(1))
      .subscribe({
        next: () => this.loadSensors(),
        error: (err) => console.error('[HOME] delete error', err),
      });
  }

  goToDashboard() {
    this.router.navigate(['/dashboard']);
  }

  private resetForm() {
    this.form = {
      name: '',
      floor: '',
      description: '',
      sensor_id: '',
    };
  }
}
