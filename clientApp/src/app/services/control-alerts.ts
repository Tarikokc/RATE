import { Mesure } from './mesure.service';

export type AlertLevel = 'ok' | 'warn' | 'danger';

export interface AlertItem {
  label: string;
  value: string;
  level: AlertLevel;
  message: string;
}

export function buildAlerts(m: Mesure | null): AlertItem[] {
  if (!m) return [];

  const alerts: AlertItem[] = [];

  if (m.co2 >= 1200) {
    alerts.push({
      label: 'CO2',
      value: `${Math.round(m.co2)} ppm`,
      level: 'danger',
      message: 'Niveau critique, aération immédiate recommandée.'
    });
  } else if (m.co2 >= 800) {
    alerts.push({
      label: 'CO2',
      value: `${Math.round(m.co2)} ppm`,
      level: 'warn',
      message: 'Qualité de l’air moyenne, ventilation conseillée.'
    });
  } else {
    alerts.push({
      label: 'CO2',
      value: `${Math.round(m.co2)} ppm`,
      level: 'ok',
      message: 'Qualité de l’air correcte.'
    });
  }

  if (m.temp <= 16 || m.temp >= 28) {
    alerts.push({
      label: 'Température',
      value: `${m.temp.toFixed(1)} °C`,
      level: 'danger',
      message: 'Température hors plage de confort.'
    });
  } else if (m.temp <= 18 || m.temp >= 25) {
    alerts.push({
      label: 'Température',
      value: `${m.temp.toFixed(1)} °C`,
      level: 'warn',
      message: 'Température à surveiller.'
    });
  } else {
    alerts.push({
      label: 'Température',
      value: `${m.temp.toFixed(1)} °C`,
      level: 'ok',
      message: 'Température stable.'
    });
  }

  if (m.hum <= 25 || m.hum >= 70) {
    alerts.push({
      label: 'Humidité',
      value: `${m.hum.toFixed(1)} %`,
      level: 'danger',
      message: 'Humidité hors plage recommandée.'
    });
  } else if (m.hum <= 35 || m.hum >= 60) {
    alerts.push({
      label: 'Humidité',
      value: `${m.hum.toFixed(1)} %`,
      level: 'warn',
      message: 'Humidité à surveiller.'
    });
  } else {
    alerts.push({
      label: 'Humidité',
      value: `${m.hum.toFixed(1)} %`,
      level: 'ok',
      message: 'Humidité correcte.'
    });
  }

  alerts.push({
    label: 'Mouvement',
    value: m.motion ? 'Détecté' : 'Aucun',
    level: m.motion ? 'warn' : 'ok',
    message: m.motion ? 'Présence détectée dans la salle.' : 'Aucune présence détectée.'
  });

  return alerts;
}