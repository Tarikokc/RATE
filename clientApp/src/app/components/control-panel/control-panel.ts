import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule } from '@angular/router';
import { MesureService, Mesure } from '../../services/mesure.service';

type Tab = 'systeme' | 'alertes' | 'automation' | 'historique';

@Component({
  selector: 'app-control-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './control-panel.html',
  styleUrl: './control-panel.css'
})
export class ControlPanelComponent {
  activeTab: Tab = 'systeme';
  mode: 'auto' | 'manuel' = 'auto';
  recording = true;
  autoArchive = false;
  desktopNotifs = false;
  soundAlerts = false;
  systemActive = false;
  lastMesure: Mesure | null = null;

  tabs = [
    { id: 'systeme'    as Tab, label: 'Système',    icon: '⚙️' },
    { id: 'alertes'    as Tab, label: 'Alertes',    icon: '🔔' },
    { id: 'automation' as Tab, label: 'Automation', icon: '🖥️' },
    { id: 'historique' as Tab, label: 'Historique', icon: '📋' },
  ];

  constructor(private svc: MesureService) {
    this.svc.getLast().subscribe({
      next: (m) => { this.lastMesure = m; this.systemActive = true; },
      error: ()  => { this.systemActive = false; }
    });
  }

  fmt(ts?: string) { return ts ? new Date(ts).toLocaleTimeString('fr-FR') : '--:--:--'; }

  exportCSV() {
    this.svc.getAll().subscribe(all => {
      const csv = ['timestamp,temp,hum,pres,motion',
        ...all.map(m => `${m.timestamp},${m.temp},${m.hum},${m.pres},${m.motion}`)
      ].join('\n');
      this.download(new Blob([csv], { type: 'text/csv' }), 'rate-measures.csv');
    });
  }

  exportJSON() {
    this.svc.getAll().subscribe(all => {
      this.download(new Blob([JSON.stringify(all, null, 2)], { type: 'application/json' }), 'rate-measures.json');
    });
  }

  private download(blob: Blob, name: string) {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = name;
    a.click();
  }
}
