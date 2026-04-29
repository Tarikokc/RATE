# RATE — Room Automation & Temperature Engine

> Plateforme IoT de supervision et d'automatisation de salles connectées — mesures environnementales en temps réel, gestion des réservations, décision intelligente de chauffage et déploiement embarqué sur Raspberry Pi.

[![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask&logoColor=white)](https://flask.palletsprojects.com)
[![Angular](https://img.shields.io/badge/Angular-19-DD0031?style=flat-square&logo=angular&logoColor=white)](https://angular.io)
[![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-A22846?style=flat-square&logo=raspberrypi&logoColor=white)](https://raspberrypi.org)
[![ESP8266](https://img.shields.io/badge/ESP8266-IoT-blue?style=flat-square)](https://www.espressif.com)

---

## Sommaire

- [Vue d'ensemble](#vue-densemble)
- [Fonctionnalités](#fonctionnalités)
- [Architecture système](#architecture-système)
- [Structure du projet](#structure-du-projet)
- [Stack technique](#stack-technique)
- [Installation locale](#installation-locale)
- [Configuration (.env)](#configuration-env)
- [Lancer le projet](#lancer-le-projet)
- [Frontend Angular](#frontend-angular)
- [Référence API complète](#référence-api-complète)
- [Moteur de chauffage](#moteur-de-chauffage)
- [Boucle d'automatisation (Heating Loop)](#boucle-dautomatisation-heating-loop)
- [Firmware ESP8266](#firmware-esp8266)
- [Déploiement Raspberry Pi](#déploiement-raspberry-pi)
- [Branches et workflow Git](#branches-et-workflow-git)

---

## Vue d'ensemble

RATE centralise la supervision de salles équipées de capteurs environnementaux (ESP8266 + SCD40). Le système :

1. **Collecte** les mesures (température, humidité, CO2, mouvement) envoyées par les capteurs via HTTP
2. **Stocke** les données dans SQLite avec horodatage UTC
3. **Analyse** et décide automatiquement si une salle doit être préchauffée avant une réservation
4. **Contrôle** les relais physiques (GPIO sur Raspberry Pi) pour allumer/éteindre le chauffage
5. **Expose** une API REST consommée par un dashboard Angular

L'ensemble est **déployable en un script** sur une Raspberry Pi — sans cloud, sans infrastructure lourde.

---

## Fonctionnalités

### Supervision
- 📡 Réception des mesures capteurs en temps réel (temp, humidité, CO2, mouvement)
- 📊 Dashboard Angular avec historique, alertes et statut des salles
- 🌤️ Intégration météo Open-Meteo (données extérieures en temps réel)
- 🔮 Prédiction ML de température (`/api/predict` — modèle TFLite embarqué)

### Réservations
- 📅 Gestion complète des réservations par salle (CRUD)
- 🗓️ Vue planning hebdomadaire dans le panneau de contrôle Angular
- ⚡ Chargement instantané — cache in-memory, zéro requête HTTP au clic

### Automatisation du chauffage
- 🔥 Moteur de décision : STANDBY / PRECHAUFFAGE / EN_CHAUFFE / CIBLE_ATTEINTE / SURCHAUFFE
- ⏰ Boucle APScheduler toutes les 5 minutes (évaluation de toutes les salles)
- 🎛️ Contrôle GPIO physique des relais (avec fallback mock sur PC)
- 📡 L'ESP interroge l'état de son relais après chaque envoi de mesure
- 🧪 Mode simulation intégré dans le firmware ESP (fakeTemp monte/descend selon relais)

### Infrastructure
- 🐍 API Flask avec Blueprints modulaires
- 📦 Déploiement Gunicorn + Nginx sur Raspberry Pi
- 🔄 Scripts `install.sh` / `update.sh` clés en main
- 🕐 Gestion rigoureuse des fuseaux horaires (stockage UTC, comparaisons UTC-safe)

---

## Architecture système

```
┌─────────────────────────────────────────────────────────────────┐
│                        Réseau local WiFi                         │
│                                                                   │
│  ┌─────────────────┐          ┌──────────────────────────────┐  │
│  │   ESP8266        │          │      Raspberry Pi             │  │
│  │                 │          │                               │  │
│  │  SCD40 Sensor   │          │  ┌─────────┐  ┌──────────┐  │  │
│  │  (CO2/Temp/Hum) │──POST──► │  │  Nginx  │  │ systemd  │  │  │
│  │  PIR Motion     │          │  │  :80    │  │ rate.svc │  │  │
│  │                 │◄─relay─  │  └────┬────┘  └────┬─────┘  │  │
│  │  [FAKE mode]    │   state  │       │              │        │  │
│  │  fakeTemp ↑↓   │          │  ┌────▼──────────────▼─────┐ │  │
│  └─────────────────┘          │  │     Flask API :5000      │ │  │
│                                │  │                          │ │  │
│  ┌─────────────────┐          │  │  ┌────────────────────┐  │ │  │
│  │  Navigateur     │          │  │  │  Heating Loop       │  │ │  │
│  │  Angular UI     │◄────────►│  │  │  (APScheduler 5min)│  │ │  │
│  │  Dashboard      │          │  │  │  → GPIO relais      │  │ │  │
│  │  Planning       │          │  │  └────────────────────┘  │ │  │
│  │  Contrôle       │          │  │                          │ │  │
│  └─────────────────┘          │  │  SQLite (data/rate.db)   │ │  │
│                                │  └──────────────────────────┘ │  │
│                                └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Structure du projet

```
RATE/
├── server.py                    # Point d'entrée Flask — init DB, blueprints, serve Angular, démarrage scheduler
│
├── app/
│   ├── config.py                # Configuration centralisée via .env (TARGET_TEMP, DEG_PER_HOUR...)
│   ├── database.py              # Accès SQLite, init_db(), schéma des tables
│   ├── time_helper.py           # now_local(), to_local() — datetime standardisé Europe/Paris
│   ├── weather.py               # Intégration Open-Meteo
│   ├── measures_service.py      # get_last_temp_for_room() et autres lectures mesures
│   ├── heating_controller.py    # Moteur de décision chauffage (_parse_dt UTC-safe, états)
│   ├── heating_loop.py          # Boucle APScheduler + contrôle GPIO + relay_state.json
│   ├── gpio_mock.py             # Mock RPi.GPIO pour développement sur PC
│   └── routes/
│       ├── measures.py          # POST /api/measures, GET /api/measures, /api/last, /api/all
│       ├── rooms.py             # CRUD /api/rooms, /api/rooms/status
│       ├── sensors.py           # GET /api/sensors
│       ├── reservations.py      # CRUD /api/reservations
│       ├── heating.py           # /api/heating/* (decision, state, sensor-state, trigger)
│       └── predict.py           # GET /api/predict — inférence TFLite
│
├── clientApp/
│   ├── src/app/
│   │   ├── components/
│   │   │   ├── dashboard/       # Vue temps réel + graphiques
│   │   │   ├── control-panel/   # Planning réservations + automation + alertes
│   │   │   └── home/            # Vue d'accueil
│   │   └── services/            # ReservationService, MesureService, HeatingService...
│   └── dist/                    # Build production (servi par Flask, commité dans le repo)
│
├── sketch_dec16a/               # Firmware Arduino/ESP8266 (SCD40 + PIR + relay state)
│
├── pi/
│   ├── install.sh               # Installation complète Pi (1 seule fois)
│   ├── update.sh                # Mise à jour après git pull
│   ├── rate.service             # Service systemd Gunicorn (Group=gpio pour les relais)
│   └── rate.nginx               # Config Nginx reverse proxy
│
├── data/
│   └── relay_state.json         # État courant des relais par room_id (runtime)
├── logs/                        # access.log, error.log (Gunicorn)
├── .env.example                 # Template de configuration
├── requirements.txt             # Dépendances Python
├── DEPLOY_PI.md                 # Guide de déploiement détaillé
└── organisation.md              # Notes d'organisation du projet
```

---

## Stack technique

### Backend

| Composant | Version | Rôle |
|---|---|---|
| Python | 3.9+ | Langage principal |
| Flask | 3.x | Framework API REST |
| SQLite | — | Base de données embarquée |
| APScheduler | 3.x | Boucle de chauffage toutes les 5 min |
| pytz | — | Gestion timezone Europe/Paris |
| flask-cors | — | CORS pour le frontend dev |
| python-dotenv | — | Configuration via `.env` |
| Gunicorn | — | Serveur WSGI production |
| openmeteo-requests | — | Données météo Open-Meteo |
| TFLite Runtime | — | Inférence modèle ML embarqué |
| RPi.GPIO | — | Contrôle GPIO (Raspberry Pi uniquement) |

### Frontend

| Composant | Version | Rôle |
|---|---|---|
| Angular | 19 | Framework SPA |
| TypeScript | 5.x | Langage frontend |
| RxJS | — | Gestion asynchrone |

### Matériel

| Composant | Rôle |
|---|---|
| ESP8266 (NodeMCU) | Microcontrôleur WiFi — envoi des mesures |
| SCD40 | Capteur CO2 / Température / Humidité (I2C) |
| PIR | Détecteur de mouvement |
| Raspberry Pi | Serveur embarqué + contrôle GPIO relais |

### Infrastructure

| Composant | Rôle |
|---|---|
| Nginx | Reverse proxy, port 80 |
| systemd | Démarrage automatique du service |
| Raspberry Pi OS | Cible de déploiement production |

---

## Installation locale

### Prérequis

- Python 3.9+
- Node.js 20+ (frontend uniquement)
- Git

### 1. Cloner le dépôt

```bash
git clone https://github.com/Tarikokc/RATE.git
cd RATE
git checkout develop
```

### 2. Environnement virtuel Python

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Dépendances Python

```bash
pip install -r requirements.txt
```

> Sur PC sans Raspberry Pi, `RPi.GPIO` est absent : le système bascule automatiquement sur `app/gpio_mock.py`. Pas d'action requise.

> `tflite-runtime` peut échouer sur certaines architectures. Commentez la ligne dans `requirements.txt` si vous n'utilisez pas la prédiction ML.

### 4. Dossiers nécessaires

```bash
mkdir -p data logs
```

### 5. Configuration

```bash
cp .env.example .env
# Éditez .env selon votre environnement
```

---

## Configuration (.env)

```env
# Mode d'exécution
FLASK_ENV=dev
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# URL de base — utilisée par Angular pour les appels API
API_URL=http://127.0.0.1:5000

# Base de données
DB_PATH=data/rate.db

# Chauffage — paramètres du moteur de décision
TARGET_TEMP=20.0        # Température cible en °C
HEAT_ADVANCE_MIN=60     # Anticipation avant réservation (minutes)
DEG_PER_HOUR=6.0        # Vitesse estimée de montée en °C/h
TEMP_TOLERANCE=0.5      # Tolérance autour de la cible

# Météo Open-Meteo (coordonnées GPS)
WEATHER_LATITUDE=48.8566
WEATHER_LONGITUDE=2.3522
```

---

## Lancer le projet

### Backend

```bash
python server.py
```

Au démarrage, Flask :
1. Initialise la base SQLite (`init_db()`)
2. Enregistre tous les Blueprints
3. Lance le **heating scheduler** (APScheduler, toutes les 5 min)
4. Exécute un **premier run immédiat** de la boucle de chauffage

API disponible sur `http://localhost:5000`.

### Backend + Frontend (développement)

```bash
# Terminal 1 — Backend
python server.py

# Terminal 2 — Frontend
cd clientApp
ng serve
```

Frontend dev sur `http://localhost:4200` avec proxy vers le backend via `proxy.conf.json`.

### Forcer un cycle de chauffage (test)

```bash
# Linux / macOS
curl -X POST http://localhost:5000/api/heating/trigger

# Windows PowerShell
Invoke-WebRequest -Uri http://localhost:5000/api/heating/trigger -Method POST -UseBasicParsing
```

---

## Frontend Angular

```bash
cd clientApp
npm install

# Développement
ng serve

# Production
ng build --configuration production
```

Le build (`clientApp/dist/`) est **servi directement par Flask** en production. Il est commité dans le repo pour éviter d'avoir besoin de Node.js sur la Raspberry Pi.

### Panneau de contrôle — Planning des réservations

Les réservations sont chargées **en parallèle au démarrage** pour toutes les salles et mises en cache in-memory. Le clic sur une salle est **instantané** (zéro requête HTTP), seules les créations et suppressions déclenchent un rechargement ciblé de la salle concernée.

---

## Référence API complète

### Mesures

| Méthode | Endpoint | Description |
|---|---|---|
| `POST` | `/api/measures` | Reçoit une mesure depuis un capteur |
| `GET` | `/api/measures` | Liste les mesures (filtres : `sensor_id`, `room_id`, `limit`) |
| `GET` | `/api/last` | Dernière mesure + données météo |
| `GET` | `/api/all` | Toutes les mesures (export) |
| `GET` | `/api/weather` | Données météo Open-Meteo en temps réel |

**Body POST `/api/measures` :**
```json
{
  "sensor_id": "esp8266-cce70f",
  "temp": 18.4,
  "hum": 47.2,
  "co2": 612,
  "motion": 1
}
```

---

### Salles

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/api/rooms` | Liste toutes les salles |
| `POST` | `/api/rooms` | Crée une salle |
| `GET` | `/api/rooms/<id>` | Détail d'une salle |
| `PATCH` | `/api/rooms/<id>` | Modifie une salle (nom, étage, `sensor_id`...) |
| `DELETE` | `/api/rooms/<id>` | Supprime une salle |
| `GET` | `/api/rooms/status` | Statut temps réel de toutes les salles |

---

### Capteurs

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/api/sensors` | Liste les capteurs actifs et leur `last_seen` |

---

### Réservations

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/api/reservations` | Liste les réservations (filtre : `room_id`) |
| `POST` | `/api/reservations` | Crée une réservation |
| `DELETE` | `/api/reservations/<id>` | Supprime une réservation |

**Body POST `/api/reservations` :**
```json
{
  "room_id": 4,
  "user_name": "Tarik",
  "title": "Cours Python",
  "start_datetime": "2026-04-30T08:00:00.000Z",
  "end_datetime": "2026-04-30T10:00:00.000Z",
  "people_count": 25
}
```

> ⚠️ Les datetimes sont stockés et comparés en **UTC**. Le frontend Angular envoie des ISO strings avec `Z` (UTC). Le moteur de chauffage convertit en heure locale Paris pour l'affichage.

---

### Chauffage

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/api/heating/decision` | Décision de chauffage pour **toutes** les salles |
| `GET` | `/api/heating/state` | État courant des relais par `room_id` |
| `GET` | `/api/heating/sensor-state?sensor_id=XXX` | État du relais pour un `sensor_id` (utilisé par l'ESP) |
| `POST` | `/api/heating/trigger` | Force un run immédiat de la boucle |

**Exemple réponse `/api/heating/decision` :**
```json
[
  {
    "room": "Salle 201",
    "current_temp": 14.8,
    "decision": {
      "status": "PRECHAUFFAGE",
      "label": "Préchauffage",
      "color": "orange",
      "action": "HEAT_ON",
      "detail": "14.8°C → 20.0°C — résa dans 18 min (86 min de chauffe)"
    }
  }
]
```

**Exemple réponse `/api/heating/sensor-state?sensor_id=esp8266-cce70f` :**
```json
{ "on": true }
```

---

### Prédiction ML

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/api/predict` | Prédit la température future (modèle TFLite) |

---

## Moteur de chauffage

Le fichier `app/heating_controller.py` évalue l'état thermique d'une salle en croisant :
- La **température courante** (dernière mesure du capteur associé)
- La **réservation en cours** (si la salle est occupée maintenant)
- La **prochaine réservation** (dans les 2 heures à venir)

### États et transitions

| Status | Label | Couleur | Action GPIO | Condition |
|---|---|---|---|---|
| `SURCHAUFFE` | Surchauffe ⚠️ | 🔴 Rouge | `HEAT_OFF` | Temp > cible + 5°C |
| `CIBLE_ATTEINTE` | Cible atteinte | 🟢 Vert | — | Temp ≥ cible − tolérance |
| `EN_CHAUFFE` | En chauffe | 🟠 Orange | `HEAT_ON` | Résa en cours, temp insuffisante |
| `PRECHAUFFAGE` | Préchauffage | 🟠 Orange | `HEAT_ON` | Résa imminente, délai critique |
| `ATTENTE` | Chauffe dans X min | 🟡 Jaune | `WAIT` | Résa imminente, encore du temps |
| `STANDBY` | Standby | ⚫ Gris | — | Aucune réservation |

### Calcul du préchauffage

```
minutes_needed = ((TARGET_TEMP - current_temp) / DEG_PER_HOUR) × 60

PRECHAUFFAGE si : minutes_until ≤ minutes_needed + 10
ATTENTE      si : minutes_until  > minutes_needed + 10
```

### Gestion UTC

Tous les datetimes en base sont stockés en **UTC** (format `2026-04-29T21:00:00.000Z`). La fonction `_parse_dt()` dans `heating_controller.py` normalise chaque datetime avant comparaison :

```python
def _parse_dt(raw: str) -> datetime:
    # 1. Remplace 'Z' par '+00:00' pour Python
    # 2. Localise en UTC si naive
    # 3. Convertit en heure Paris via to_local()
    ...
```

La boucle `run_once()` dans `heating_loop.py` compare en UTC pur avec `replace(start_datetime,'Z','')` côté SQL.

---

## Boucle d'automatisation (Heating Loop)

Fichier : `app/heating_loop.py`

### Fonctionnement

1. **Démarrage** : `start_scheduler()` est appelé depuis `server.py` au lancement de Flask
2. **Fréquence** : toutes les **5 minutes** via APScheduler (+ run immédiat au démarrage)
3. **Pour chaque salle** :
   - Récupère la dernière température (via `sensor_id`)
   - Cherche la réservation en cours et la prochaine (requêtes UTC-safe)
   - Appelle `heating_decision()` pour obtenir l'action
   - Si `HEAT_ON` → active le relais GPIO + sauvegarde dans `relay_state.json`
   - Si `HEAT_OFF` → désactive le relais GPIO

### GPIO

```python
# Mapping room_id → broche GPIO BCM (à adapter selon câblage)
ROOM_PINS = {
    1: 17,  # Salle 101
    2: 27,  # Salle 102
    3: 22,  # Salle 103
}
```

Sur une machine sans Raspberry Pi, `RPi.GPIO` est remplacé automatiquement par `app/gpio_mock.py` (aucun changement de code nécessaire).

### État des relais

L'état courant est maintenu en mémoire (`_relay_state: dict[int, bool]`) et persisté dans `data/relay_state.json` après chaque changement. L'ESP interroge cet état via `/api/heating/sensor-state`.

### Commandes de test

```bash
# Forcer un run immédiat
curl -X POST http://localhost:5000/api/heating/trigger

# Voir l'état des relais
curl http://localhost:5000/api/heating/state

# Voir l'état pour un capteur spécifique
curl "http://localhost:5000/api/heating/sensor-state?sensor_id=esp8266-cce70f"
```

---

## Firmware ESP8266

Dossier : `sketch_dec16a/`

### Matériel requis

- NodeMCU ESP8266
- SCD40 (I2C sur D5/D6)
- Capteur PIR (sur D2)

### Fonctionnement

Toutes les **5 secondes**, l'ESP :
1. Lit le SCD40 (CO2, température, humidité)
2. Lit le PIR (mouvement)
3. **POST** `/api/measures` avec les données
4. **GET** `/api/heating/sensor-state?sensor_id=XXX` pour connaître l'état du relais

### Mode simulation (FAKE)

Si le SCD40 n'est pas détecté, l'ESP bascule automatiquement en mode simulation :

```cpp
if (body.indexOf("true") != -1) {
    fakeTemp += 0.12;  // 🔥 relais ON  → +~1.4°C/min
} else {
    fakeTemp -= 0.04;  // ❄️ relais OFF → -~0.5°C/min
}
fakeTemp = constrain(fakeTemp, 13.0, 35.0);
```

Cela permet de valider l'ensemble du pipeline (API → heating loop → GPIO → ESP) sans capteur physique.

### Associer un capteur à une salle

```bash
sqlite3 data/rate.db "UPDATE rooms SET sensor_id = 'esp8266-cce70f' WHERE id = 4;"
```

---

## Déploiement Raspberry Pi

Voir aussi : [`DEPLOY_PI.md`](DEPLOY_PI.md)

### Installation initiale (une seule fois)

```bash
git clone https://github.com/Tarikokc/RATE.git /home/pi/RATE
cd /home/pi/RATE
git checkout develop
bash pi/install.sh
```

`install.sh` prend tout en charge :
- Mise à jour système et installation de Nginx
- Création du virtualenv et installation des dépendances Python (dont `apscheduler`)
- Build du frontend Angular
- Génération automatique du `.env` avec l'IP de la Pi
- Installation et activation du service systemd (`rate.service`)
- Configuration du reverse proxy Nginx
- Vérification finale de l'API

### Mise à jour après un push

```bash
cd /home/pi/RATE
bash pi/update.sh
```

### Service systemd

Le service `rate.service` dans `pi/` doit inclure `Group=gpio` pour l'accès aux broches GPIO :

```ini
[Service]
User=pi
Group=gpio
WorkingDirectory=/home/pi/RATE
EnvironmentFile=/home/pi/RATE/.env
ExecStart=/home/pi/RATE/venv/bin/gunicorn \
    --bind 127.0.0.1:5000 \
    --workers 2 \
    --timeout 60 \
    server:app
Restart=always
```

### Architecture de déploiement

```
Réseau local
     │
 Nginx :80
 ┌────┴────┐
 /api/*    /*
   │        │
Flask:5000  Angular dist/
   │
 SQLite + APScheduler
   │
 GPIO relais
```

### Commandes utiles

```bash
# Statut
sudo systemctl status rate nginx

# Logs en direct
sudo journalctl -u rate -f
tail -f /home/pi/RATE/logs/error.log

# Redémarrage
sudo systemctl restart rate

# Forcer un cycle de chauffage
curl -X POST http://localhost/api/heating/trigger
```

---

## Branches et workflow Git

| Branche | Rôle |
|---|---|
| `feature/*` | Développement d'une fonctionnalité isolée |
| `feat/heating-simulation` | Boucle de chauffage + GPIO + simulation ESP |
| `develop` | Intégration — branche principale de travail ✅ |
| `fix-pi` | Correctifs spécifiques Raspberry Pi |
| `main` | Production stable — merge après validation Pi |

### Workflow GitFlow

```
feat/* ──► develop ──► validation Pi ──► main
                              │
                         tag vX.X.X
```

```bash
# Merger une feature dans develop
git checkout develop
git merge feat/ma-feature
git push origin develop

# Passer en production
git checkout main
git merge develop
git push origin main

# Tagger une version stable
git tag v1.1.0
git push origin v1.1.0
```

---

<div align="center">

Fait avec ❤️ — IoT, Flask, Angular & Raspberry Pi

</div>
