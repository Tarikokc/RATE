"""
Insère des réservations réalistes pour le Lycée Jean Moulin.
Lancer depuis la racine :
    python -m app.scripts.seed_lycee_resa
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

# ─── Récupère le Lycée et ses salles ──────────────────────────────────────────

lycee = conn.execute(
    "SELECT id FROM organisations WHERE name='Lycée Jean Moulin'"
).fetchone()

if not lycee:
    print("❌ Lycée Jean Moulin introuvable en BDD. Lance d'abord le serveur pour init_db().")
    conn.close()
    exit(1)

lycee_id = lycee[0]

rooms = conn.execute(
    "SELECT id, name FROM rooms WHERE org_id=?", (lycee_id,)
).fetchall()

if not rooms:
    print("❌ Aucune salle trouvée pour le Lycée. Vérifie client.config.json.")
    conn.close()
    exit(1)

room_ids = {r[1]: r[0] for r in rooms}
print(f"[Lycée] Salles trouvées : {list(room_ids.keys())}")

# ─── Nettoyage des anciennes resa seed du Lycée ───────────────────────────────

room_id_list = list(room_ids.values())
placeholders = ','.join('?' * len(room_id_list))
conn.execute(
    f"DELETE FROM reservations WHERE user_name LIKE 'Seed%' AND room_id IN ({placeholders})",
    room_id_list
)
conn.commit()

# ─── Helpers ─────────────────────────────────────────────────────────────────

def R(room_name, user, title, day, h_start, h_end, people=15):
    rid = room_ids.get(room_name)
    if not rid:
        print(f"  ⚠️  Salle '{room_name}' introuvable, ignorée.")
        return
    conn.execute("""
        INSERT INTO reservations
            (room_id, user_name, title, start_datetime, end_datetime, people_count)
        VALUES (?,?,?,?,?,?)
    """, (rid, f"Seed:{user}", title, dt(day, h_start), dt(day, h_end), people))

# ─── Emploi du temps réaliste ─────────────────────────────────────────────────
# Utilise les 2 premières salles pour les cours, les autres pour réunions/CDI

room_names = list(room_ids.keys())

# Salle 1 — cours principaux
if len(room_names) >= 1:
    s1 = room_names[0]
    cours_s1 = [
        ("Mme Leroy",   "Cours Mathématiques – Terminale B",    8,  10, 30),
        ("M. Bernard",  "Cours Histoire-Géo – Première A",      10, 12, 28),
        ("Mme Dupont",  "Cours Philosophie – Terminale A",      14, 16, 32),
        ("M. Martin",   "Cours Sciences – Seconde C",           16, 18, 25),
    ]
    for day in days:
        for user, title, h1, h2, people in cours_s1:
            R(s1, user, title, day, h1, h2, people)

# Salle 2 — cours secondaires
if len(room_names) >= 2:
    s2 = room_names[1]
    cours_s2 = [
        ("M. Garnier",  "Cours Français – Seconde B",           8,  10, 27),
        ("Mme Petit",   "Cours Anglais – Terminale C",          10, 12, 24),
        ("M. Moreau",   "Cours Physique-Chimie – Première B",   14, 16, 22),
        ("Mme Richard", "Cours SES – Terminale ES",             16, 18, 29),
    ]
    for day in days:
        for user, title, h1, h2, people in cours_s2:
            R(s2, user, title, day, h1, h2, people)

# Salle 3 — salle polyvalente / TD
if len(room_names) >= 3:
    s3 = room_names[2]
    R(s3, "M. Bernard",    "TD Méthodologie – Terminale",        days[0],  8, 10, 15)
    R(s3, "Mme Leroy",     "Colle Mathématiques",                days[0], 14, 16, 12)
    R(s3, "M. Garnier",    "Atelier Écriture",                   days[1],  9, 11, 14)
    R(s3, "Mme Petit",     "Préparation Grand Oral",             days[1], 14, 16, 10)
    R(s3, "M. Moreau",     "TP Chimie – Première",               days[2],  8, 12, 18)
    R(s3, "Mme Richard",   "Conférence orientation post-bac",    days[2], 14, 17, 35)
    R(s3, "M. Martin",     "TD Sciences – Seconde",              days[3],  8, 10, 16)
    R(s3, "Mme Dupont",    "Dissertation Philosophie",           days[3], 14, 16, 20)
    R(s3, "Direction",     "Réunion parents d'élèves",           days[4], 17, 19, 40)

# Salle 4 — salle de réunion / administration
if len(room_names) >= 4:
    s4 = room_names[3]
    R(s4, "Direction",     "Conseil de classe Terminale A",      days[0],  9, 11,  8)
    R(s4, "Direction",     "Conseil de classe Première B",       days[0], 14, 16,  8)
    R(s4, "Proviseur",     "Réunion équipe pédagogique",         days[1],  8, 10, 12)
    R(s4, "CPE",           "Suivi disciplinaire",                days[1], 10, 12,  4)
    R(s4, "Proviseur",     "Réunion de direction",               days[2], 14, 16,  6)
    R(s4, "AED",           "Formation assistants éducation",     days[3],  9, 11,  8)
    R(s4, "Direction",     "Conseil de classe Seconde C",        days[3], 14, 16,  8)
    R(s4, "Proviseur",     "Entretien recrutement",              days[4],  9, 12,  3)

# Salle 5+ — CDI / salle informatique
if len(room_names) >= 5:
    s5 = room_names[4]
    for day in [days[0], days[2], days[4]]:
        R(s5, "Documentaliste", "Permanence CDI – Recherche documentaire", day,  8, 12, 20)
        R(s5, "Documentaliste", "Permanence CDI – Après-midi",             day, 13, 17, 18)
    for day in [days[1], days[3]]:
        R(s5, "M. Martin",      "Cours Informatique – Seconde",            day,  9, 11, 24)
        R(s5, "Mme Petit",      "Atelier Numérique – Première",            day, 14, 16, 20)

conn.commit()

# ─── Résumé ───────────────────────────────────────────────────────────────────
nb = conn.execute(
    f"SELECT COUNT(*) FROM reservations WHERE user_name LIKE 'Seed%' AND room_id IN ({placeholders})",
    room_id_list
).fetchone()[0]
conn.close()

print(f"\n✅ Seed Lycée terminé !")
print(f"   → {len(room_names)} salles utilisées")
print(f"   → {nb} réservations insérées")