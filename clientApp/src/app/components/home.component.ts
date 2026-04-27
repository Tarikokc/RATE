import { Component, inject, ChangeDetectorRef, OnInit, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { take } from 'rxjs/operators';
import { SensorService, Sensor, AvailableSensor } from '../services/sensor.service';
import { ClientConfigService } from '../services/client-config.service';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css',
})
export class HomeComponent implements OnInit, OnDestroy {
  private svc = inject(SensorService);
  private configSvc = inject(ClientConfigService);
  private router = inject(Router);
  private cdr = inject(ChangeDetectorRef);
  private pollInterval: any = null;

  sensors: Sensor[] = [];
  availableSensors: AvailableSensor[] = [];
  loading = true;
  flaskDown = false;
  success = '';

  orgName = 'RATE Dashboard';
  orgSubtitle = 'Système de monitoring intelligent des salles';

  showAssignModal = false;
  assignErrorMsg = '';
  selectedRoom: Sensor | null = null;
  assignSensorId = '';

  ngOnInit() {
    this.loadConfig();
    this.loadSensors();
  }

  ngOnDestroy() {
    this.stopSensorPolling();
  }

  private loadConfig() {
    this.configSvc.getConfig().pipe(take(1)).subscribe({
      next: (config) => {
        this.orgName = config.organisation.name;
        const type = config.organisation.type;
        this.orgSubtitle =
          type === 'school'  ? 'Monitoring qualité de l\u2019air \u2014 Établissement scolaire' :
          type === 'admin'   ? 'Monitoring qualité de l\u2019air \u2014 Administration publique' :
          type === 'health'  ? 'Monitoring qualité de l\u2019air \u2014 Établissement de santé' :
          'Système de monitoring intelligent des salles';
        this.cdr.detectChanges();
      },
      error: () => {}
    });
  }

  loadSensors() {
    this.loading = true;
    this.flaskDown = false;
    this.svc.getAll().pipe(take(1)).subscribe({
      next: (s) => {
        this.sensors = s ?? [];
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: () => {
        this.sensors = [];
        this.loading = false;
        this.flaskDown = true;
        this.cdr.detectChanges();
      },
    });
  }

  loadAvailableSensors() {
    this.svc.getAvailableSensors().pipe(take(1)).subscribe({
      next: (list) => { this.availableSensors = list; this.cdr.detectChanges(); },
      error: () => { this.availableSensors = []; this.cdr.detectChanges(); },
    });
  }

  private startSensorPolling() {
    this.loadAvailableSensors();
    this.pollInterval = setInterval(() => this.loadAvailableSensors(), 5000);
  }

  private stopSensorPolling() {
    if (this.pollInterval) {
      clearInterval(this.pollInterval);
      this.pollInterval = null;
    }
    this.availableSensors = [];
  }

  onCardClick(room: Sensor) {
    if (room.sensor_id) {
      this.router.navigate(['/dashboard'], { queryParams: { room: room.id } });
    } else {
      this.openAssignModal(room);
    }
  }

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
    if (!this.assignSensorId) {
      this.assignErrorMsg = 'Sélectionnez un capteur.';
      return;
    }
    const exists = this.availableSensors.some((s) => s.sensor_id === this.assignSensorId);
    if (!exists) {
      this.assignErrorMsg = "Ce capteur n'est pas disponible.";
      return;
    }
    this.svc.assignSensor(this.selectedRoom!.id!, this.assignSensorId).pipe(take(1)).subscribe({
      next: () => {
        this.stopSensorPolling();
        this.router.navigate(['/dashboard'], { queryParams: { room: this.selectedRoom!.id } });
      },
      error: (err) => {
        this.assignErrorMsg = err?.error?.error || "Erreur lors de l'assignation.";
      },
    });
  }

  delete(event: Event, id: number, name: string) {
    event.stopPropagation();
    if (!confirm(`Supprimer la salle "${name}" ?`)) return;
    this.svc.delete(id).pipe(take(1)).subscribe({
      next: () => this.loadSensors(),
      error: (err) => console.error('[HOME] delete error', err),
    });
  }
}
