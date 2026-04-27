# RATE — Room Automation & Temperature Engine

> Plateforme IoT de supervision de salles connectées — mesures environnementales, gestion des réservations et aide à la décision de chauffage, déployable sur Raspberry Pi.

![Python](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.x-000000?style=flat-square&logo=flask&logoColor=white)
![Angular](https://img.shields.io/badge/Angular-19-DD0031?style=flat-square&logo=angular&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=flat-square&logo=sqlite&logoColor=white)
![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-A22846?style=flat-square&logo=raspberrypi&logoColor=white)

---

## Sommaire

- [Vue d'ensemble](#vue-densemble)
- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Structure du projet](#structure-du-projet)
- [Stack technique](#stack-technique)
- [Installation locale](#installation-locale)
- [Configuration](#configuration)
- [Lancer le projet](#lancer-le-projet)
- [Frontend Angular](#frontend-angular)
- [Référence API](#référence-api)
- [Logique de chauffage](#logique-de-chauffage)
- [Déploiement Raspberry Pi](#déploiement-raspberry-pi)
- [Branches et workflow](#branches-et-workflow)

---

## Vue d'ensemble

RATE centralise la supervision de salles équipées de capteurs environnementaux. Le système collecte les données en temps réel, les expose via une API REST, affiche un dashboard Angular et décide automatiquement s'il faut déclencher le chauffage avant une réservation.

L'objectif est une base propre, légère et déployable en un script sur une Raspberry Pi — sans infrastructure lourde, sans cloud obligatoire.

---

## Fonctionnalités

- **Collecte des mesures** — réception des données capteurs (temp, humidité, CO2, mouvement) via POST
- **Historisation** — stockage SQLite, requêtes filtrées par capteur, salle ou limite
- **Gestion des salles** — création, association capteur/salle, statut en temps réel
- **Gestion des réservations** — réservation en cours, prochaine réservation imminente
- **Décision de chauffage** — moteur de décision basé sur la température courante, la cible et les réservations
- **Prédiction** — endpoint ML pour l'anticipation de la température (`/api/predict`)
- **Météo externe** — intégration Open-Meteo pour données météorologiques locales
- **Dashboard Angular** — interface de visualisation et de supervision
- **Déploiement embarqué** — scripts clés en main pour Raspberry Pi (systemd + Nginx)

---

## Architecture

```
Capteurs / microcontrôleurs (Arduino, ESP)
              │
              │  POST /api/measures
              ▼
        ┌─────────────┐
        │  Flask API  │  ◄── app/routes/*.py (Blueprints)
        │             │
        │  app/        │  ◄── config, database, services, helpers
        └──────┬──────┘
               │
               ▼
          SQLite (data/rate.db)
               │
       ┌───────┴────────┐
       │                │
       ▼                ▼
  Logique chauffage   Prédiction ML
  heating_controller  routes/predict
       │
       ▼
  Dashboard Angular
  (clientApp/dist/ servi par Flask)
       │
       ▼
  Gunicorn + Nginx
  Raspberry Pi — accessible sur le réseau local
```

---

## Structure du projet

```
RATE/
├── server.py                  # Point d'entrée Flask — init, blueprints, serve Angular
│
├── app/
│   ├── config.py              # Configuration centralisée via .env
│   ├── database.py            # Accès SQLite via flask.g, init_db, schema
│   ├── time_helper.py         # now_local(), to_local() — datetime standardisé Europe/Paris
│   ├── weather.py             # Intégration Open-Meteo
│   ├── heating_controller.py  # Moteur de décision chauffage
│   ├── measures_service.py    # Service de lecture des mesures
│   ├── routes/
│   │   ├── measures.py        # POST /api/measures — GET /api/measures — /api/last — /api/all
│   │   ├── rooms.py           # CRUD salles, statut, association capteur
│   │   ├── sensors.py         # Liste des capteurs actifs
│   │   ├── reservations.py    # Gestion des réservations
│   │   ├── heating.py         # GET /api/heating/decision/<room_id>
│   │   └── predict.py         # GET /api/predict — inférence modèle TFLite
│   └── scripts/               # Scripts utilitaires (import, migration...)
│
├── clientApp/
│   ├── src/                   # Sources Angular (components, services, models)
│   ├── dist/                  # Build de production (servi par Flask en prod)
│   └── angular.json           # Config Angular CLI
│
├── data/                      # Fichiers runtime — rate.db (ignoré par git, structure gardée)
├── logs/                      # Logs Gunicorn (access.log, error.log)
│
├── pi/
│   ├── install.sh             # Installation complète Raspberry Pi (1 seule fois)
│   ├── update.sh              # Mise à jour après git pull
│   ├── rate.service           # Service systemd Gunicorn
│   └── rate.nginx             # Config Nginx reverse proxy
│
├── sketch_dec16a/             # Code Arduino / ESP (capteurs)
├── .env.example               # Template de configuration
├── requirements.txt           # Dépendances Python
└── DEPLOY_PI.md               # Guide de déploiement détaillé Raspberry Pi
```

---

## Stack technique

### Backend
| Composant | Rôle |
|---|---|
| Python 3.9+ | Langage principal |
| Flask 3.x | Framework API REST |
| SQLite | Base de données embarquée |
| flask-cors | Gestion CORS |
| python-dotenv | Configuration via `.env` |
| pytz | Gestion des fuseaux horaires |
| open-meteo (openmeteo-requests) | Données météo en temps réel |
| TFLite Runtime | Inférence modèle ML embarqué |
| numpy | Calculs numériques |
| Gunicorn | Serveur WSGI production |

### Frontend
| Composant | Rôle |
|---|---|
| Angular 19 | Framework frontend |
| TypeScript | Langage frontend |
| CSS | Styles |

### Infrastructure
| Composant | Rôle |
|---|---|
| Nginx | Reverse proxy, port 80 |
| systemd | Démarrage automatique |
| Raspberry Pi OS | Cible de déploiement |

---

## Installation locale

### Prérequis

- Python 3.9 ou supérieur
- Node.js 20+ (pour le frontend uniquement)
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
```

**Windows**
```bash
venv\Scripts\activate
```

**Linux / macOS**
```bash
source venv/bin/activate
```

### 3. Dépendances Python

```bash
pip install -r requirements.txt
```

> Sur une machine sans Raspberry Pi, `tflite-runtime` peut échouer.
> Dans ce cas, commentez la ligne dans `requirements.txt` pour le dev local.

### 4. Dossiers nécessaires

```bash
mkdir -p data logs
```

### 5. Configuration

```bash
cp .env.example .env
```

Éditez `.env` selon votre environnement (voir section [Configuration](#configuration)).

---

## Configuration

Toute la configuration passe par le fichier `.env` à la racine. La classe `Config` dans `app/config.py` charge ces valeurs avec des valeurs par défaut.

```env
# Mode d'exécution : dev ou prod
FLASK_ENV=dev
FLASK_HOST=0.0.0.0
FLASK_PORT=5000

# URL de base utilisée par le frontend Angular pour les appels API
API_URL=http://127.0.0.1:5000

# Chemin de la base SQLite
DB_PATH=data/rate.db

# Paramètres chauffage
TARGET_TEMP=20.0       # Température cible en °C
HEAT_ADVANCE_MIN=60    # Marge d'anticipation avant réservation (minutes)
DEG_PER_HOUR=2.5       # Vitesse estimée de montée en température (°C/h)
TEMP_TOLERANCE=0.5     # Tolérance autour de la cible

# Coordonnées GPS pour la météo Open-Meteo
WEATHER_LATITUDE=48.8566
WEATHER_LONGITUDE=2.3522
```

---

## Lancer le projet

### Backend uniquement

```bash
python server.py
```

L'API est disponible sur `http://localhost:5000`.

### Backend + Frontend (développement)

**Terminal 1 — Backend**
```bash
python server.py
```

**Terminal 2 — Frontend**
```bash
cd clientApp
ng serve
```

Le frontend dev est disponible sur `http://localhost:4200` avec proxy vers le backend configuré dans `proxy.conf.json`.

---

## Frontend Angular

### Installation des dépendances

```bash
cd clientApp
npm install
```

### Lancement en développement

```bash
ng serve
```

### Build de production

```bash
ng build --configuration production
```

Le build génère les fichiers statiques dans `clientApp/dist/client-app/browser/`.
Ce dossier est servi directement par Flask en production via `server.py`.

> Le `dist/` est commité dans le repo pour éviter d'avoir besoin de Node.js sur la Raspberry Pi.

---

## Référence API

### Mesures

#### `POST /api/measures`
Reçoit une mesure envoyée par un capteur.

```json
{
  "sensor_id": "SENSOR_01",
  "temp": 21.4,
  "hum": 45.0,
  "co2": 612,
  "motion": true
}
```

Réponse : `{ "ok": true }` — `200 OK`

---

#### `GET /api/measures`
Historique des mesures, avec filtres optionnels.

| Paramètre | Type | Description |
|---|---|---|
| `sensor_id` | string | Filtrer par capteur |
| `room_id` | integer | Filtrer par salle |
| `limit` | integer | Nombre de résultats |

```bash
GET /api/measures?sensor_id=SENSOR_01&limit=50
```

---

#### `GET /api/last`
Retourne la dernière mesure connue, enrichie des données météo.

#### `GET /api/all`
Retourne toutes les mesures sans filtre.

#### `GET /api/weather`
Retourne les données météo en temps réel (Open-Meteo).

---

### Salles

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/api/rooms` | Liste toutes les salles |
| `POST` | `/api/rooms` | Crée une nouvelle salle |
| `GET` | `/api/rooms/<id>` | Détail d'une salle |
| `PATCH` | `/api/rooms/<id>` | Met à jour une salle |
| `DELETE` | `/api/rooms/<id>` | Supprime une salle |
| `GET` | `/api/rooms/status` | Statut en temps réel de toutes les salles |

---

### Capteurs

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/api/sensors` | Liste les capteurs actifs et leur `last_seen` |

---

### Réservations

| Méthode | Endpoint | Description |
|---|---|---|
| `GET` | `/api/reservations` | Liste les réservations |
| `POST` | `/api/reservations` | Crée une réservation |
| `DELETE` | `/api/reservations/<id>` | Supprime une réservation |

---

### Chauffage

#### `GET /api/heating/decision/<room_id>`
Retourne la décision de chauffage pour une salle donnée.

```json
{
  "status": "PRECHAUFFAGE",
  "label": "Préchauffage",
  "color": "orange",
  "action": "HEAT_ON",
  "detail": "18.5°C → 20.0°C — résa dans 45 min (36 min de chauffe)"
}
```

---

### Prédiction ML

#### `GET /api/predict`
Prédit la température future à partir du modèle TFLite embarqué.

---

## Logique de chauffage

Le moteur `heating_controller.py` évalue l'état thermique d'une salle en croisant la température courante, la réservation active et la prochaine réservation.

### États possibles

| Status | Label | Couleur | Action | Condition |
|---|---|---|---|---|
| `SURCHAUFFE` | Surchauffe ⚠️ | Rouge | `HEAT_OFF` | Temp > cible + 5°C |
| `CIBLE_ATTEINTE` | Cible atteinte | Vert | — | Temp ≥ cible − tolérance |
| `EN_CHAUFFE` | En chauffe | Orange | `HEAT_ON` | Résa en cours, temp insuffisante |
| `PRECHAUFFAGE` | Préchauffage | Orange | `HEAT_ON` | Résa imminente, délai critique |
| `ATTENTE` | Chauffe dans X min | Jaune | `WAIT` | Résa imminente, encore du temps |
| `STANDBY` | Standby | Gris | — | Aucune réservation |

### Paramètres du calcul

```
minutes_needed = (TARGET_TEMP - current_temp) / DEG_PER_HOUR × 60
```

Le préchauffage se déclenche quand :
```
minutes_until ≤ minutes_needed + 10
```

---

## Déploiement Raspberry Pi

Le dossier `pi/` contient tous les fichiers nécessaires. Voir aussi `DEPLOY_PI.md` pour le guide complet.

### Installation initiale (une seule fois)

```bash
git clone https://github.com/Tarikokc/RATE.git /home/pi/RATE
cd /home/pi/RATE
git checkout develop
bash pi/install.sh
```

`install.sh` prend tout en charge :
- Installation de Nginx
- Création du virtualenv et installation des dépendances
- Génération du `.env` avec l'IP de la Pi
- Installation et activation du service systemd
- Configuration du reverse proxy Nginx
- Vérification finale

### Mise à jour après un push

```bash
cd /home/pi/RATE
bash pi/update.sh
```

### Accès à l'application

```
http://IP_DE_LA_RASPBERRY_PI
```

### Architecture de déploiement

```
Réseau local
      │
  Nginx :80
  ┌────┴────┐
/api/*      /*
  │          │
Flask:5000  Angular dist/
  │
SQLite
```

Gunicorn écoute sur `127.0.0.1:5000` (non exposé directement).
Nginx fait le pont depuis le port 80 et route `/api/*` vers Flask et `/*` vers le frontend.

### Commandes utiles sur la Pi

```bash
# Statut des services
sudo systemctl status rate nginx

# Logs en direct
sudo journalctl -u rate -f
tail -f /home/pi/RATE/logs/error.log

# Redémarrage manuel
sudo systemctl restart rate
```

---

## Branches et workflow

| Branche | Rôle |
|---|---|
| `feature/*` | Développement d'une fonctionnalité |
| `develop` | Intégration — branche principale de travail |
| `main` | Production stable — merge après validation Pi |

### Workflow recommandé

```
feature/* ──► develop ──► validation Raspberry Pi ──► main (tag vX.X.X)
```

```bash
# Tagger une version stable
git tag v1.0.0
git push origin v1.0.0
```
