import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { ReservationService, Room, Reservation } from '../services/reservation.service';

@Component({
  selector: 'app-reservations',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './reservations.html',
  styleUrl: './reservations.css'
})
export class ReservationsComponent implements OnInit {
  rooms: Room[] = [];
  reservations: Reservation[] = [];
  selectedRoomId: number | null = null;

  weekStart: Date = this.getMonday(new Date());
  weekDays: Date[] = [];
  hours = Array.from({ length: 14 }, (_, i) => i + 7); // 7h → 20h

  showModal = false;
  selectedSlot: { date: Date; hour: number } | null = null;
  form = { title: '', user_name: '', people_count: 1, duration: 60 };
  errorMsg = '';
  loading = false;

  constructor(private svc: ReservationService) {}

  ngOnInit() {
    this.buildWeek();
    this.svc.getRooms().subscribe(r => {
      this.rooms = r;
      if (r.length) { this.selectedRoomId = r[0].id; this.load(); }
    });
  }

  // ── Week navigation ──────────────────────────────
  getMonday(d: Date): Date {
    const date = new Date(d);
    const day = date.getDay();
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

  prevWeek() { this.weekStart.setDate(this.weekStart.getDate() - 7); this.buildWeek(); this.load(); }
  nextWeek() { this.weekStart.setDate(this.weekStart.getDate() + 7); this.buildWeek(); this.load(); }

  // ── Data ─────────────────────────────────────────
  load() {
    if (!this.selectedRoomId) return;
    this.loading = true;
    // Load all reservations for the room, filter client-side for the week
    this.svc.getReservations(undefined, this.selectedRoomId).subscribe({
      next: r => { this.reservations = r; this.loading = false; },
      error: () => { this.loading = false; }
    });
  }

  onRoomChange() { this.load(); }

  // ── Calendar helpers ─────────────────────────────
  sameDay(a: Date, b: Date): boolean {
    return a.getFullYear() === b.getFullYear() &&
           a.getMonth()    === b.getMonth()    &&
           a.getDate()     === b.getDate();
  }

  getResAt(day: Date, hour: number): Reservation | undefined {
    return this.reservations.find(r => {
      const s = new Date(r.start_datetime);
      return this.sameDay(s, day) && s.getHours() === hour;
    });
  }

  isOccupied(day: Date, hour: number): boolean {
    return this.reservations.some(r => {
      const s = new Date(r.start_datetime);
      const e = new Date(r.end_datetime);
      const slotS = new Date(day); slotS.setHours(hour, 0, 0, 0);
      const slotE = new Date(day); slotE.setHours(hour + 1, 0, 0, 0);
      return this.sameDay(s, day) && s < slotE && e > slotS;
    });
  }

  isContinuation(day: Date, hour: number): boolean {
    const res = this.reservations.find(r => {
      const s = new Date(r.start_datetime);
      const e = new Date(r.end_datetime);
      const slotS = new Date(day); slotS.setHours(hour, 0, 0, 0);
      return this.sameDay(s, day) && s < slotS && e > slotS;
    });
    return !!res;
  }

  getResForContinuation(day: Date, hour: number): Reservation | undefined {
    return this.reservations.find(r => {
      const s = new Date(r.start_datetime);
      const e = new Date(r.end_datetime);
      const slotS = new Date(day); slotS.setHours(hour, 0, 0, 0);
      return this.sameDay(s, day) && s < slotS && e > slotS;
    });
  }

  getDuration(r: Reservation): number {
    return (new Date(r.end_datetime).getTime() - new Date(r.start_datetime).getTime()) / 60000;
  }

  getSpanHeight(r: Reservation): string {
    return `${(this.getDuration(r) / 60) * 100}%`;
  }

  isToday(d: Date): boolean { return this.sameDay(d, new Date()); }

  getWeekLabel(): string {
    const s = this.weekDays[0], e = this.weekDays[6];
    return `${s.getDate()} ${s.toLocaleString('fr-FR', { month: 'short' })} – ${e.getDate()} ${e.toLocaleString('fr-FR', { month: 'short', year: 'numeric' })}`;
  }

  getDayLabel(d: Date): string {
    return d.toLocaleString('fr-FR', { weekday: 'short', day: 'numeric', month: 'short' });
  }

  toISODate(d: Date): string {
    return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  }

  // ── Modal ────────────────────────────────────────
  openModal(day: Date, hour: number) {
    if (this.isOccupied(day, hour) || !this.selectedRoomId) return;
    this.selectedSlot = { date: new Date(day), hour };
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

    this.svc.createReservation({
      room_id: this.selectedRoomId,
      user_name: this.form.user_name,
      title: this.form.title,
      start_datetime: start.toISOString(),
      end_datetime: end.toISOString(),
      people_count: this.form.people_count
    }).subscribe({
      next: () => { this.showModal = false; this.load(); },
      error: (e) => { this.errorMsg = e.error?.error ?? 'Erreur serveur'; }
    });
  }

  deleteRes(id: number, ev: Event) {
    ev.stopPropagation();
    if (confirm('Supprimer cette réservation ?')) {
      this.svc.deleteReservation(id).subscribe(() => this.load());
    }
  }
}
