"""
Ajoute les organisations secondaires (Mairie + Médiathèque).
Le Lycée Jean Moulin est créé automatiquement au boot par database.py.

Lancer depuis la racine :
    python -m app.scripts.seed_orgs
"""
import sqlite3, os
from datetime import datetime, timedelta, date

DB_PATH = os.getenv("DB_PATH", "data/rate.db")
conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = ON")


# ─── Utilitaires ──────────────────────────────────────────────────────────────

def dt(d: date, h: int, m: int = 0) -> str:
    return datetime(d.year, d.month, d.day, h, m).isoformat()

today  = date.today()
monday = today - timedelta(days=today.weekday())
days   = [monday + timedelta(days=i) for i in range(5)]  # lun→ven


# ─── Nettoyage des orgas secondaires uniquement ───────────────────────────────
# Le Lycée (créé par database.py) est préservé

conn.execute("DELETE FROM reservations WHERE user_name LIKE 'Seed%'")
conn.execute("""
    DELETE FROM rooms WHERE org_id IN (
        SELECT id FROM organisations
        WHERE name NOT IN ('Lycée Jean Moulin')
    )
""")
conn.execute("DELETE FROM organisations WHERE name NOT IN ('Lycée Jean Moulin')")
conn.commit()


# ─── Organisations secondaires ────────────────────────────────────────────────

orgs_data = [
    {
        "name":    "Mairie du 5ème Arrondissement",
        "type":    "admin",
        "address": "21 place du Panthéon, 75005 Paris",
        "contact": "contact@mairie5.paris.fr",
    },
    {
        "name":    "Médiathèque Marguerite Yourcenar",
        "type":    "library",
        "address": "41 rue d'Alleray, 75015 Paris",
        "contact": "mediatheque.yourcenar@paris.fr",
    },
]

org_ids = {}

# Récupère l'id du Lycée (déjà en BDD)
row = conn.execute(
    "SELECT id FROM organisations WHERE name='Lycée Jean Moulin'"
).fetchone()
if row:
    org_ids["Lycée Jean Moulin"] = row[0]

# Insère les nouvelles orgas
for o in orgs_data:
    cur = conn.execute(
        "INSERT INTO organisations (name, type, address, contact) VALUES (?,?,?,?)",
        (o["name"], o["type"], o["address"], o["contact"])
    )
    org_ids[o["name"]] = cur.lastrowid

conn.commit()


# ─── Salles ───────────────────────────────────────────────────────────────────

rooms_data = {
    "Mairie du 5ème Arrondissement": [
        ("Salle du Conseil",       "1", "Salle du conseil municipal", 60),
        ("Salle des Mariages",     "0", "Célébrations civiles",       40),
        ("Salle de Réunion A",     "1", "Réunions internes",          20),
        ("Salle de Réunion B",     "1", "Réunions internes",          15),
        ("Bureau des Associations","2", "Permanences associatives",   10),
        ("Salle de Presse",        "0", "Conférences de presse",      30),
    ],
    "Médiathèque Marguerite Yourcenar": [
        ("Grande Salle de Lecture", "0", "Lecture publique",       80),
        ("Salle de Travail 1",      "1", "Travail en groupe",      15),
        ("Salle de Travail 2",      "1", "Travail en groupe",      15),
        ("Salle de Travail 3",      "1", "Travail en groupe",      15),
        ("Salle de Conférence",     "0", "Conférences & ateliers", 60),
        ("Espace Multimédia",       "1", "Postes informatiques",   25),
    ],
}

room_ids = {}
for org_name, rooms in rooms_data.items():
    oid = org_ids[org_name]
    for name, floor, desc, cap in rooms:
        cur = conn.execute(
            "INSERT INTO rooms (name, floor, description, capacity, org_id) VALUES (?,?,?,?,?)",
            (name, floor, desc, cap, oid)
        )
        room_ids[(org_name, name)] = cur.lastrowid

conn.commit()


# ─── Réservations ─────────────────────────────────────────────────────────────

def R(org, room, user, title, day, h_start, h_end, people=10):
    rid = room_ids.get((org, room))
    if not rid:
        return
    conn.execute("""
        INSERT INTO reservations
            (room_id, user_name, title, start_datetime, end_datetime, people_count)
        VALUES (?,?,?,?,?,?)
    """, (rid, f"Seed:{user}", title,
          dt(day, h_start), dt(day, h_end), people))


# ── Mairie du 5ème ────────────────────────────────────────────────────────────
MA = "Mairie du 5ème Arrondissement"
R(MA, "Salle du Conseil",       "Secrétariat", "Conseil municipal",          days[0], 18, 21, 45)
R(MA, "Salle de Presse",        "Direction",   "Point presse mensuel",       days[0], 11, 12, 20)
R(MA, "Salle de Réunion A",     "DRH",         "Commission urbanisme",       days[1],  9, 11, 12)
R(MA, "Salle de Réunion A",     "DAF",         "Réunion budget",             days[3], 14, 16, 10)
R(MA, "Salle de Réunion B",     "DSI",         "Point projets numériques",   days[2], 10, 12,  8)
R(MA, "Salle de Réunion B",     "Cabinet",     "Réunion de cabinet",         days[0],  9, 10,  6)
for h in [10, 11, 14, 15]:
    R(MA, "Salle des Mariages", "Officier",    "Cérémonie civile",           days[4],  h, h+1, 25)
for d in days:
    R(MA, "Bureau des Associations", "Service", "Permanence associative",    d, 9, 12, 5)


# ── Médiathèque Marguerite Yourcenar ─────────────────────────────────────────
ME = "Médiathèque Marguerite Yourcenar"
for d in days:
    for salle in ["Salle de Travail 1", "Salle de Travail 2", "Salle de Travail 3"]:
        R(ME, salle, "Usager A", "Travail en groupe", d,  9, 12, 6)
        R(ME, salle, "Usager B", "Travail en groupe", d, 14, 17, 5)
    R(ME, "Espace Multimédia", "Animateur", "Atelier numérique", d, 10, 12, 20)

R(ME, "Salle de Conférence", "Médiathèque", "Conférence : Littérature contemporaine", days[1], 18, 20, 50)
R(ME, "Salle de Conférence", "Médiathèque", "Club de lecture adultes",               days[3], 17, 19, 30)
R(ME, "Salle de Conférence", "Médiathèque", "Heure du conte — jeunesse",             days[2], 10, 11, 40)


conn.commit()
conn.close()

# ─── Résumé ───────────────────────────────────────────────────────────────────
print("✅ Seed terminé !")
print(f"   → {len(orgs_data)} organisations secondaires créées")
rooms_total = sum(len(v) for v in rooms_data.values())
print(f"   → {rooms_total} salles créées")

conn2 = sqlite3.connect(DB_PATH)
nb_res = conn2.execute("SELECT COUNT(*) FROM reservations WHERE user_name LIKE 'Seed%'").fetchone()[0]
conn2.close()
print(f"   → {nb_res} réservations insérées")