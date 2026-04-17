import {Component, inject, afterNextRender, ChangeDetectorRef} from '@angular/core';
import {FormsModule} from '@angular/forms';
import {Router} from '@angular/router';
import {SensorService, Sensor} from '../services/sensor.service';
import {take} from 'rxjs/operators';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent {
  private svc = inject(SensorService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);

  sensors: Sensor[] = [];
  loading = true;
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

  constructor() {
    afterNextRender(() => {
      this.loadSensors();
    });
    console.log(this.sensors.length);
    console.log(this.sensors);
  }

  loadSensors() {
    this.loading = true;
    this.flaskDown = false;
    this.showForm = false;

    this.svc
      .getAll()
      .pipe(take(1))
      .subscribe({
        next: (s) => {
          console.log('[HOME] sensors =', s);
          this.sensors = s;
          this.loading = false;
          this.showForm = s.length === 0;
          this.cdr.detectChanges();
        },
        error: (err) => {
          console.error('[HOME] getAll error', err);
          this.sensors = [];
          this.loading = false;
          this.flaskDown = true;
          this.showForm = false;
          this.cdr.detectChanges();
        },
      });
  }

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
      this.errorMsg = "Nom, étage et sensor_id sont requis.";
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
          this.errorMsg = "Erreur lors de l’ajout du capteur.";
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
