import { Mesure } from './mesure.service';

export function buildHistory(all: Mesure[], limit = 20): Mesure[] {
  return [...all]
    .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
    .slice(0, limit);
}

export function getSeverity(m: Mesure): 'ok' | 'warn' | 'danger' {
  if (m.co2 >= 1200 || m.temp <= 16 || m.temp >= 28 || m.hum <= 25 || m.hum >= 70) {
    return 'danger';
  }

  if (m.co2 >= 800 || m.temp <= 18 || m.temp >= 25 || m.hum <= 35 || m.hum >= 60) {
    return 'warn';
  }

  return 'ok';
}

export function getSeverityLabel(level: 'ok' | 'warn' | 'danger'): string {
  if (level === 'danger') return 'Critique';
  if (level === 'warn') return 'À surveiller';
  return 'OK';
}