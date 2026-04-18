import { Routes } from '@angular/router';
import { HomeComponent }       from './components/home.component';
import { DashboardComponent }  from './components/dashboard/dashboard';
import { ControlPanelComponent } from './components/control-panel/control-panel';
import { sensorGuard }         from './sensor.guard';

export const routes: Routes = [
  { path: '',              component: HomeComponent },
  { path: 'dashboard',     component: DashboardComponent},
  { path: 'control-panel', component: ControlPanelComponent },
  { path: '**',            redirectTo: '' }
];
