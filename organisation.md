# Gestion de Projet - Solution IoT (RATE)

**Équipe :** Emilien, Randy, Anthony, Tarik  
**Projet :** Système de monitoring environnemental connecté (ESP8266 + Flask/Docker)  
**Date :** 16 Décembre 2025

---

## 1. Organisation de l’équipe (Rôles & Responsabilités)

Afin d'optimiser les compétences de chacun et assurer le bon déroulement du projet, l'équipe est structurée selon les pôles suivants :

### 👨‍💼 Emilien – Chef de Projet & Product Owner
*   **Pilotage :** Coordination globale, suivi du planning (Gantt) et respect des délais.
*   **Documentation :** Rédaction du cahier des charges, rapports de suivi et documentation finale.
*   **Qualité :** Validation fonctionnelle des livrables par rapport aux besoins du projet (RATE).

### 👨‍💻 Tarik – Lead Tech IoT & Backend
*   **Embarqué :** Développement du firmware ESP8266 (C++), câblage des capteurs (BME280, PIR).
*   **Backend :** Conception de l’API REST (Flask), gestion des flux de données (JSON) et stockage.
*   **Architecture :** Choix des protocoles de communication (HTTP/MQTT).

### 🛠️ Randy – Ingénieur DevOps & Infrastructure
*   **Système :** Installation et sécurisation du Raspberry Pi (OS, SSH, Réseau).
*   **Déploiement :** Mise en place de l'environnement conteneurisé (Docker / Docker Compose).
*   **Intégration :** Configuration du broker MQTT (Mosquitto) et future migration Home Assistant.

### 🎨 Anthony – Développeur Frontend & Data Viz
*   **Interface :** Développement du Dashboard Web de visualisation (HTML/CSS/JS).
*   **Visualisation :** Intégration des graphiques d'historique et affichage temps réel.
*   **UX/UI :** Ergonomie de la solution et design du boîtier (si applicable).

---

## 2. Planning Prévisionnel

Le projet est découpé en 4 phases (Sprints) :

### Phase 1 : Conception & Architecture (Semaines 1-2)
*   [x] Définition de l'architecture technique (ESP8266 ↔ Serveur).
*   [x] Choix du matériel (NodeMCU, BME280, PIR).
*   [x] POC : Première communication "Hello World" en WiFi.

### Phase 2 : Développement "Core" (Semaines 3-4) — *État actuel*
*   [x] Intégration complète des capteurs (Température, Humidité, Pression, Mouvement).
*   [x] Développement de l'API Flask (Réception & Stockage NDJSON).
*   [x] Interface Web de consultation "Live" avec auto-refresh.

### Phase 3 : Industrialisation & DevOps (Semaines 5-6)
*   [ ] Configuration du Raspberry Pi (Serveur de prod).
*   [ ] Dockerisation de l'application Flask et du serveur Web.
*   [ ] Mise en place de la persistance des données et tests de robustesse.

### Phase 4 : Finalisation & Livraison (Semaine 7)
*   [ ] Tests d'intégration complets (Bout en bout).
*   [ ] Finalisation de la documentation technique et utilisateur.
*   [ ] Préparation de la soutenance et démo.

---

## 3. Répartition des tâches (Matrice RACI Simplifiée)

| Module / Tâche | Responsable Principal | Support | État |
| :--- | :--- | :--- | :--- |
| **Hardware & Embarqué** | **Tarik** | Anthony | ✅ Terminé |
| *Câblage & Code C++* | | | |
| **Backend & API** | **Tarik** | Randy | ✅ Terminé |
| *Serveur Python Flask* | | | |
| **Infrastructure** | **Randy** | Emilien | 📅 À faire |
| *Raspberry Pi & Docker* | | | |
| **Frontend & UI** | **Anthony** | Tarik | 🔄 En cours |
| *Dashboard Web* | | | |
| **Gestion & Doc** | **Emilien** | Tous | 🔄 Continu |
| *Suivi & Rapport* | | | |

---

## 4. Architecture Technique

### Schéma de flux de données
Le système repose sur une architecture IoT centralisée où les microcontrôleurs (Edge) remontent les informations vers un serveur central (Fog/Cloud).

`[Capteurs BME280/PIR]` → `(I2C/GPIO)` → `[ESP8266 NodeMCU]` → `(WiFi / HTTP POST)` → `[Serveur Flask API]` → `(JSON)` → `[Stockage NDJSON]`

### Choix technologiques
*   **Protocole :** HTTP REST (Simple & Robuste) pour le prototype.
*   **Format de données :** JSON Standardisé.
    ```
    { "sensor": "esp8266-1", "temp": 26.2, "hum": 54.5, "motion": 1, "timestamp": "..." }
    ```
*   **Stockage :** Fichier NDJSON (Append-only) pour la performance et la simplicité de sauvegarde.

### Spécifications Matérielles (Pinout ESP8266)
*   **D1 (GPIO5) :** SCL (BME280)
*   **D2 (GPIO4) :** SDA (BME280)
*   **D5 (GPIO14) :** SIG (PIR Motion)
*   **Alimentation :** 3.3V (via NodeMCU)

---

## 5. Analyse des Risques & Mitigations

| Risque Identifié | Impact | Probabilité | Stratégie d'atténuation (Mitigation) |
| :--- | :--- | :--- | :--- |
| **Perte de connexion WiFi** | Critique | Moyenne | Routine de reconnexion automatique (`WiFi.reconnect()`) implémentée dans la boucle principale. |
| **Défaillance Capteur** | Majeur | Faible | Vérification de l'adresse I2C au démarrage. Envoi d'un statut d'erreur si capteur absent. |
| **Indisponibilité Raspberry Pi** | Moyen | Moyenne | Architecture portable (Docker/Python) permettant de basculer le serveur sur n'importe quel PC en 5 minutes. |
| **Sécurité des données** | Faible | Faible | Flux en clair (HTTP) acceptable sur réseau local isolé (Hotspot/VLAN). HTTPS envisagé pour la V2. |

---

## 6. Liste du Matériel & Budget

Le projet respecte une contrainte "Low-Cost" :

*   **Microcontrôleur :** 1x ESP8266 NodeMCU V3 (~5€)
*   **Capteurs :**
    *   1x BME280 (Temp/Hum/Pres) (~4€)
    *   1x PIR HC-SR501 (Mouvement) (~2€)
*   **Serveur :** 1x Raspberry Pi 3/4 + Carte SD 32Go (~50€ - *Matériel école*)
*   **Divers :** Breadboard, câbles (~3€)
*   **Total estimé :** < 65€

---

## 7. Conclusion & Prochaines Étapes

À date, la **Phase 2** est validée avec succès. La chaîne d'acquisition est fonctionnelle : les données environnementales sont capturées, transmises et visualisées en temps réel via une interface web fluide.

**Objectifs de la semaine prochaine :**
1.  Réception et configuration du Raspberry Pi (Randy).
2.  Mise en conteneur Docker de l'application Flask (Randy/Tarik).
3.  Amélioration esthétique du Dashboard avec graphiques historiques (Anthony).


scp -r dist/ pi@TON_IP_PI:/home/pi/RATE/clientApp/
