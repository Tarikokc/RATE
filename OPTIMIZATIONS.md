# Optimisations — branche `optimize/perf-improvements`

Cette branche applique les améliorations de performance identifiées sur `develop` sans modifier le comportement existant.

## Ce qui a changé

### 🔴 Priorité haute

#### 1. Mesures stockées dans SQLite (`server.py`)
- Suppression du fichier `measures.ndjson` : les mesures sont désormais dans une table `measures` de `rate.db`.
- Index `idx_measures_room_ts` sur `(room_id, timestamp DESC)` pour des lectures rapides.
- `read_measures()` supporte maintenant `limit` et `room_id` pour éviter de tout charger en mémoire.
- `/api/all` expose les paramètres `?limit=N&offset=M` pour la pagination.
- `/api/predict` n'interroge plus que les 12 dernières mesures de la salle via `LIMIT`.

#### 2. Suppression des `print()` de debug (`server.py`)
- Les 5 `print()` de `/api/last` (debug 1→5) ont été supprimés.

### 🟡 Priorité moyenne

#### 3. Connexion SQLite mutualisée par requête (`server.py`)
- `db()` utilise maintenant `flask.g` pour partager une unique connexion par cycle de requête HTTP.
- `@app.teardown_appcontext` ferme la connexion automatiquement en fin de requête.
- Résultat : plus d'ouverture/fermeture à chaque appel de fonction.

#### 4. Cache météo déjà présent (`weather.py`)
- `weather.py` disposait déjà d'un cache mémoire de 10 minutes — aucune modification nécessaire.

#### 5. Double appel HTTP corrigé (`dashboard.ts`)
- `getAll()` n'est plus appelé deux fois dans `refresh()` : la logique stats + graphique est centralisée dans `applyData()`.

### 🟢 Nice-to-have

#### 6. Flag `usingFakeData` dans le dashboard (`dashboard.ts`)
- Nouveau champ `usingFakeData: boolean` exposé dans le composant.
- Positionné à `true` quand `getAll()` renvoie un tableau vide ou une erreur.
- Permet d'afficher un badge "Données simulées" dans le template HTML.

#### 7. Pagination sur `/api/all`
- `GET /api/all?limit=100&offset=0` disponible pour limiter la charge réseau.

## Ce qui n'a PAS changé
- Logique métier chauffage (`heating_decision`)
- Routes salles et réservations (comportement identique, connexion `g.db` transparente)
- `weather.py` (non modifié)
- `heating_controller.py` (non modifié)
- Code Arduino / sketch

## Migration données existantes
Si un fichier `measures.ndjson` existe déjà en production, importer les données :
```python
import json, sqlite3
with open('measures.ndjson') as f:
    rows = [json.loads(l) for l in f if l.strip()]
# puis appeler append_measure(row) pour chaque row
```
