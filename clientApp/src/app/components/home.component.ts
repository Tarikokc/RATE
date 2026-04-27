import { Component, inject, afterNextRender, ChangeDetectorRef, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { SensorService, Sensor, AvailableSensor } from '../services/sensor.service';
import { ClientConfigService, RoomTemplate } from '../services/client-config.service';
import { take } from 'rxjs/operators';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent implements OnDestroy {
  private svc        = inject(SensorService);
  private configSvc  = inject(ClientConfigService);
  private router     = inject(Router);
  private cdr        = inject(ChangeDetectorRef);
  private pollInterval: any = null;

  sensors: Sensor[] = [];
  availableSensors: AvailableSensor[] = [];
  loading = true;
  flaskDown = false;
  success = '';

  // Nom de l'organisation (depuis config)
  orgName = 'RATE Dashboard';
  orgSubtitle = 'Système de monitoring intelligent des salles';

  // Templates de salles depuis la config (pour import rapide)
  roomTemplates: RoomTemplate[] = [];
  showImportModal = false;
  importLoading = false;
  importSuccess = '';

  // Modal : ajouter une nouvelle salle
  showAddForm = false;
  addErrorMsg = '';
  addForm: Sensor = { name: '', floor: '', description: '', sensor_id: '' };

  // Modal : associer un capteur
  showAssignModal = false;
  assignErrorMsg = '';
  selectedRoom: Sensor | null = null;
  assignSensorId = '';

  constructor() {
    afterNextRender(() => {
      // Charge la config en parallèle des salles
      this.configSvc.getConfig().subscribe({
        next: (cfg) => {
          this.orgName     = cfg.organisation.name;
          this.orgSubtitle = cfg.organisation.type === 'school'
            ? 'Monitoring qualité de l\'air — Établissement scolaire'
            : cfg.organisation.type === 'admin'
            ? 'Monitoring qualité de l\'air — Administration publique'
            : cfg.organisation.type === 'health'
            ? 'Monitoring qualité de l\'air — Établissement de santé'
            : 'Système de monitoring intelligent des salles';
          this.roomTemplates = cfg.rooms;
          this.cdr.detectChanges();
        },
        error: () => { /* garde les valeurs par défaut */ }
      });
      this.loadSensors();
    });
  }

  ngOnDestroy() { this.stopSensorPolling(); }

  // ─── Chargement ──────────────────────────────────────

  loadSensors() {
    this.loading = true;
    this.flaskDown = false;
    this.showAddForm = false;

    this.svc.getAll().pipe(take(1)).subscribe({
      next: (s) => {
        this.sensors = s;
        this.loading = false;
        if (s.length === 0) this.openAddForm();
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
      next: (list) => { this.availableSensors = list; this.cdr.detectChanges(); },
      error: ()     => { this.availableSensors = []; this.cdr.detectChanges(); },
    });
  }

  private startSensorPolling() {
    this.loadAvailableSensors();
    this.pollInterval = setInterval(() => this.loadAvailableSensors(), 5000);
  }

  private stopSensorPolling() {
    if (this.pollInterval) { clearInterval(this.pollInterval); this.pollInterval = null; }
    this.availableSensors = [];
  }

  // ─── Import salles depuis config ─────────────────────

  openImportModal() {
    this.showImportModal = true;
    this.importSuccess = '';
  }

  closeImportModal() {
    this.showImportModal = false;
  }

  importAllRooms() {
    if (!this.roomTemplates.length) return;
    this.importLoading = true;
    let done = 0;
    const total = this.roomTemplates.length;

    this.roomTemplates.forEach(t => {
      const room: Sensor = { name: t.name, floor: t.floor, description: t.description, sensor_id: '', capacity: t.capacity };
      this.svc.create(room).pipe(take(1)).subscribe({
        next: () => {
          done++;
          if (done === total) {
            this.importLoading = false;
            this.importSuccess = `${total} salles importées avec succès !`;
            this.showImportModal = false;
            this.loadSensors();
          }
        },
        error: () => {
          done++;
          if (done === total) {
            this.importLoading = false;
            this.loadSensors();
          }
        }
      });
    });
  }

  // ─── Clic carte ──────────────────────────────────────

  onCardClick(room: Sensor) {
    if (room.sensor_id) {
      this.router.navigate(['/dashboard'], { queryParams: { room: room.id } });
    } else {
      this.openAssignModal(room);
    }
  }

  // ─── Modal : ajouter une salle ───────────────────────

  openAddForm() {
    this.showAddForm = true;
    this.addErrorMsg = '';
    this.addForm = { name: '', floor: '', description: '', sensor_id: '' };
    this.startSensorPolling();
  }

  closeAddForm() {
    if (this.sensors.length === 0) return;
    this.showAddForm = false;
    this.addForm = { name: '', floor: '', description: '', sensor_id: '' };
    this.stopSensorPolling();
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
        this.stopSensorPolling();
        this.loadSensors();
      },
      error: (err) => { this.addErrorMsg = err?.error?.error || "Erreur lors de l'ajout."; },
    });
  }

  // ─── Modal : associer un capteur ─────────────────────

  openAssignModal(room: Sensor) {
    this.selectedRoom = room;
    this.assignSensorId = '';
    this.assignErrorMsg = '';
    this.showAssignModal = true;
    this.startSensorPolling();
  }

  closeAssignModal() {
    this.showAssignModal = false;
    this.selectedRoom = null;
    this.assignSensorId = '';
    this.stopSensorPolling();
  }

  submitAssign() {
    if (!this.assignSensorId) { this.assignErrorMsg = 'Sélectionnez un capteur.'; return; }
    const exists = this.availableSensors.some(s => s.sensor_id === this.assignSensorId);
    if (!exists) { this.assignErrorMsg = "Ce capteur n'est pas disponible."; return; }
    this.svc.assignSensor(this.selectedRoom!.id!, this.assignSensorId).pipe(take(1)).subscribe({
      next: () => {
        this.stopSensorPolling();
        this.router.navigate(['/dashboard'], { queryParams: { room: this.selectedRoom!.id } });
      },
      error: (err) => { this.assignErrorMsg = err?.error?.error || "Erreur lors de l'assignation."; },
    });
  }

  // ─── Suppression ─────────────────────────────────────

  delete(event: Event, id: number, name: string) {
    event.stopPropagation();
    if (!confirm(`Supprimer la salle "${name}" ?`)) return;
    this.svc.delete(id).pipe(take(1)).subscribe({
      next: () => this.loadSensors(),
      error: (err) => console.error('[HOME] delete error', err),
    });
  }
}
