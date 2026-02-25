import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { Subject, Subscription } from 'rxjs';
import { takeUntil, take, finalize } from 'rxjs/operators'; 
import { MesureService, Mesure } from '../../services/mesure.service';
import { ReservationService, Room, Reservation } from '../../services/reservation.service';

type Tab = 'systeme' | 'alertes' | 'automation' | 'historique' | 'reservations';

@Component({
  selector: 'app-control-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './control-panel.html',
  styleUrl: './control-panel.css'
})
export class ControlPanelComponent implements OnInit, OnDestroy {

  // ── Tabs ─────────────────────────────────────────
  activeTab: Tab = 'systeme';
  tabs = [
    { id: 'systeme'      as Tab, label: 'Système',      icon: '⚙️' },
    { id: 'alertes'      as Tab, label: 'Alertes',      icon: '🔔' },
    { id: 'automation'   as Tab, label: 'Automation',   icon: '🖥️' },
    { id: 'historique'   as Tab, label: 'Historique',   icon: '📋' },
    { id: 'reservations' as Tab, label: 'Réservations', icon: '📅' },
  ];

  // ── Système ──────────────────────────────────────
  mode: 'auto' | 'manuel' = 'auto';
  recording = true; autoArchive = false;
  desktopNotifs = false; soundAlerts = false;
  systemActive = false;
  lastMesure: Mesure | null = null;

  // ── Réservations ─────────────────────────────────
  rooms: Room[] = [];
  reservations: Reservation[] = [];
  selectedRoomId: number | null = null;
  weekStart: Date = this.getMonday(new Date());
  weekDays: Date[] = [];
  hours = Array.from({ length: 14 }, (_, i) => i + 7);
  showModal = false;
  selectedSlot: { date: Date; hour: number } | null = null;
  form = { title: '', user_name: '', people_count: 1, duration: 60 };
  errorMsg = '';
  resLoading = false;

  // ── Subscriptions ─────────────────────────────────
  private resSub?: Subscription;
  private destroy$ = new Subject<void>();

  constructor(private svc: MesureService, private resSvc: ReservationService) {}

  ngOnInit() {
    this.svc.getLast().pipe(take(1)).subscribe({  // 👈
      next:  m => { this.lastMesure = m; this.systemActive = true; },
      error: () => { this.systemActive = false; }
    });
    this.buildWeek();
    this.resSvc.getRooms().pipe(take(1), takeUntil(this.destroy$)).subscribe(r => {  
      this.rooms = r;
      if (r.length) { this.selectedRoomId = r[0].id; this.loadRes(); }
    });
  }

  ngOnDestroy() {
    this.resSub?.unsubscribe();
    this.destroy$.next();
    this.destroy$.complete();
  }

  // ── Système helpers ───────────────────────────────
  fmt(ts?: string) { return ts ? new Date(ts).toLocaleTimeString('fr-FR') : '--:--:--'; }

  exportCSV() {
    this.svc.getAll().pipe(take(1)).subscribe(all => { 
      const csv = ['timestamp,temp,hum,pres,motion',
        ...all.map(m => `${m.timestamp},${m.temp},${m.hum},${m.co2},${m.motion}`)
      ].join('\n');
      this.download(new Blob([csv], { type: 'text/csv' }), 'rate-measures.csv');
    });
  }

  exportJSON() {
    this.svc.getAll().pipe(take(1)).subscribe(all => {  // 👈
      this.download(new Blob([JSON.stringify(all, null, 2)], { type: 'application/json' }), 'rate-measures.json');
    });
  }

  private download(blob: Blob, name: string) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob); a.download = name; a.click();
  }

  // ── Réservations helpers ──────────────────────────
  getMonday(d: Date): Date {
    const date = new Date(d);
    const day  = date.getDay();
    date.setDate(date.getDate() - day + (day === 0 ? -6 : 1));
    date.setHours(0, 0, 0, 0);
    return date;
  }

  buildWeek() {
    this.weekDays = Array.from({ length: 7 }, (_, i) => {
      const d = new Date(this.weekStart);
      d.setDate(d.getDate() + i);
      return d;
    });
  }

  prevWeek() { this.weekStart.setDate(this.weekStart.getDate() - 7); this.buildWeek(); this.loadRes(); }
  nextWeek() { this.weekStart.setDate(this.weekStart.getDate() + 7); this.buildWeek(); this.loadRes(); }

  loadRes() {
    if (!this.selectedRoomId) return;

    this.resSub?.unsubscribe();
    this.resLoading = true;

    this.resSub = this.resSvc.getReservations(undefined, this.selectedRoomId)
      .pipe(
        take(1),                                     
        finalize(() => this.resLoading = false)      
      )
      .subscribe({
        next:  r  => { this.reservations = r; },
        error: () => { this.reservations = []; }
      });
  }

  onRoomChange() { this.loadRes(); }

  sameDay(a: Date, b: Date) {
    return a.getFullYear() === b.getFullYear()
        && a.getMonth()    === b.getMonth()
        && a.getDate()     === b.getDate();
  }

  getResAt(day: Date, h: number): Reservation | undefined {
    return this.reservations.find(r => {
      const s = new Date(r.start_datetime);
      return this.sameDay(s, day) && s.getHours() === h;
    });
  }

  isOccupied(day: Date, h: number): boolean {
    return this.reservations.some(r => {
      const s  = new Date(r.start_datetime), e = new Date(r.end_datetime);
      const sS = new Date(day); sS.setHours(h, 0, 0, 0);
      const sE = new Date(day); sE.setHours(h + 1, 0, 0, 0);
      return this.sameDay(s, day) && s < sE && e > sS;
    });
  }

  getDuration(r: Reservation) {
    return (new Date(r.end_datetime).getTime() - new Date(r.start_datetime).getTime()) / 60000;
  }

  isToday(d: Date) { return this.sameDay(d, new Date()); }

  getWeekLabel() {
    const s = this.weekDays[0], e = this.weekDays[6];
    return `${s.getDate()} ${s.toLocaleString('fr-FR', { month: 'short' })} – ${e.getDate()} ${e.toLocaleString('fr-FR', { month: 'short', year: 'numeric' })}`;
  }

  getDayLabel(d: Date) {
    return d.toLocaleString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' });
  }

  openModal(day: Date, h: number) {
    if (this.isOccupied(day, h) || !this.selectedRoomId) return;
    this.selectedSlot = { date: new Date(day), hour: h };
    this.form = { title: '', user_name: '', people_count: 1, duration: 60 };
    this.errorMsg = '';
    this.showModal = true;
  }

  submit() {
    if (!this.selectedSlot || !this.selectedRoomId) return;
    if (!this.form.title || !this.form.user_name) { this.errorMsg = 'Tous les champs sont requis.'; return; }
    const start = new Date(this.selectedSlot.date);
    start.setHours(this.selectedSlot.hour, 0, 0, 0);
    const end = new Date(start);
    end.setMinutes(end.getMinutes() + this.form.duration);
    this.resSvc.createReservation({
      room_id:        this.selectedRoomId,
      user_name:      this.form.user_name,
      title:          this.form.title,
      start_datetime: start.toISOString(),
      end_datetime:   end.toISOString(),
      people_count:   this.form.people_count
    }).pipe(take(1)).subscribe({  // 👈
      next:  () =>  { this.showModal = false; this.loadRes(); },
      error: (e) => { this.errorMsg = e.error?.error ?? 'Erreur serveur'; }
    });
  }

  deleteRes(id: number, ev: Event) {
    ev.stopPropagation();
    if (confirm('Supprimer cette réservation ?'))
      this.resSvc.deleteReservation(id).pipe(take(1)).subscribe(() => this.loadRes());  
  }
}
