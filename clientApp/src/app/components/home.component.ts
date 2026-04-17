import { Component, inject, afterNextRender, ChangeDetectorRef } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { SensorService, Sensor, AvailableSensor } from '../services/sensor.service';
import { take } from 'rxjs/operators';

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
  availableSensors: AvailableSensor[] = [];
  loading = true;
  flaskDown = true;
  success = '';

  // Modal : ajouter une nouvelle salle
  showAddForm = false;
  addErrorMsg = '';
  addForm: Sensor = { name: '', floor: '', description: '', sensor_id: '' };

  // Modal : associer un capteur à une salle existante (clic carte sans sensor)
  showAssignModal = false;
  assignErrorMsg = '';
  selectedRoom: Sensor | null = null;
  assignSensorId = '';

  constructor() {
    afterNextRender(() => {
      this.loadSensors();
    });
  }

  // ─── Chargement ──────────────────────────────────────

  loadSensors() {
    this.loading = true;
    this.flaskDown = false;
    this.showAddForm = false;

    this.svc.getAll().pipe(take(1)).subscribe({
      next: (s) => {
        this.sensors = s;
        this.loading = false;
        this.showAddForm = s.length === 0;
        this.cdr.detectChanges();
      },
      error: () => {
        this.sensors = [];
        this.loading = false;
        this.flaskDown = true;
        this.showAddForm = false;
        this.cdr.detectChanges();
      },
    });
  }

  loadAvailableSensors() {
    this.svc.getAvailableSensors().pipe(take(1)).subscribe({
      next: (list) => {
        this.availableSensors = list;
        this.cdr.detectChanges();
      },
      error: () => {
        this.availableSensors = [];
        this.cdr.detectChanges();
      },
    });
  }

  // ─── Clic sur une carte ──────────────────────────────
  // sensor associé → /dashboard?room=id  |  pas de sensor → modal assignation

  onCardClick(room: Sensor) {
    if (room.sensor_id) {
      this.router.navigate(['/dashboard'], { queryParams: { room: room.id } });
    } else {
      this.openAssignModal(room);
    }
  }

  // ─── Modal : ajouter une nouvelle salle ──────────────

  openAddForm() {
    this.showAddForm = true;
    this.addErrorMsg = '';
    this.addForm = { name: '', floor: '', description: '', sensor_id: '' };
    this.loadAvailableSensors();
  }

  closeAddForm() {
    if (this.sensors.length === 0) return;
    this.showAddForm = false;
    this.addForm = { name: '', floor: '', description: '', sensor_id: '' };
    this.availableSensors = [];
  }

  submitAdd() {
    if (!this.addForm.name || !this.addForm.floor || !this.addForm.sensor_id) {
      this.addErrorMsg = 'Nom, étage et capteur sont requis.';
      return;
    }
    const exists = this.availableSensors.some(s => s.sensor_id === this.addForm.sensor_id);
    if (!exists) {
      this.addErrorMsg = "Ce capteur n'est pas disponible. Allumez-le puis réessayez.";
      return;
    }
    this.svc.create(this.addForm).pipe(take(1)).subscribe({
      next: () => {
        this.success = `Salle "${this.addForm.name}" ajoutée`;
        this.addErrorMsg = '';
        this.showAddForm = false;
        this.addForm = { name: '', floor: '', description: '', sensor_id: '' };
        this.availableSensors = [];
        this.loadSensors();
      },
      error: (err) => {
        this.addErrorMsg = err?.error?.error || "Erreur lors de l'ajout.";
      },
    });
  }

  // ─── Modal : associer un capteur à une salle ─────────

  openAssignModal(room: Sensor) {
    this.selectedRoom = room;
    this.assignSensorId = '';
    this.assignErrorMsg = '';
    this.showAssignModal = true;
    this.loadAvailableSensors();
  }

  closeAssignModal() {
    this.showAssignModal = false;
    this.selectedRoom = null;
    this.assignSensorId = '';
    this.availableSensors = [];
  }

  submitAssign() {
    if (!this.assignSensorId) {
      this.assignErrorMsg = 'Sélectionnez un capteur.';
      return;
    }
    const exists = this.availableSensors.some(s => s.sensor_id === this.assignSensorId);
    if (!exists) {
      this.assignErrorMsg = "Ce capteur n'est pas disponible.";
      return;
    }
    this.svc.assignSensor(this.selectedRoom!.id!, this.assignSensorId)
      .pipe(take(1))
      .subscribe({
        next: () => {
          // Redirige directement vers le dashboard de la salle
          this.router.navigate(['/dashboard'], {
            queryParams: { room: this.selectedRoom!.id }
          });
        },
        error: (err) => {
          this.assignErrorMsg = err?.error?.error || "Erreur lors de l'assignation.";
        },
      });
  }

  // ─── Suppression ─────────────────────────────────────

  delete(event: Event, id: number, name: string) {
    event.stopPropagation(); // empêche le clic de buller vers onCardClick
    if (!confirm(`Supprimer la salle "${name}" ?`)) return;
    this.svc.delete(id).pipe(take(1)).subscribe({
      next: () => this.loadSensors(),
      error: (err) => console.error('[HOME] delete error', err),
    });
  }
}