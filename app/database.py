import sqlite3
import os
import json
from flask import g
from app.config import Config

DB_PATH = Config.DB_PATH

CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'client.config.json')


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA journal_mode=WAL")
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")

    conn.executescript("""
        CREATE TABLE IF NOT EXISTS rooms (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            capacity    INTEGER DEFAULT 10,
            floor       TEXT    DEFAULT 'RDC',
            description TEXT    DEFAULT '',
            sensor_id   TEXT    DEFAULT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS sensors (
            sensor_id TEXT PRIMARY KEY,
            last_seen TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS reservations (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            room_id        INTEGER NOT NULL,
            user_name      TEXT    NOT NULL,
            title          TEXT    NOT NULL,
            start_datetime TEXT    NOT NULL,
            end_datetime   TEXT    NOT NULL,
            people_count   INTEGER DEFAULT 1,
            created_at     TEXT    DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS measures (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            sensor_id TEXT    NOT NULL,
            room_id   INTEGER,
            temp      REAL,
            hum       REAL,
            co2       REAL,
            motion    INTEGER DEFAULT 0,
            timestamp TEXT    NOT NULL,
            FOREIGN KEY (room_id) REFERENCES rooms(id) ON DELETE SET NULL
        );

        CREATE INDEX IF NOT EXISTS idx_measures_sensor  ON measures(sensor_id);
        CREATE INDEX IF NOT EXISTS idx_measures_room_ts ON measures(room_id, timestamp);
    """)

    # Seed rooms from client.config.json if the table is empty
    count = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
    if count == 0:
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                config = json.load(f)
            rooms = config.get('rooms', [])
            for r in rooms:
                conn.execute(
                    "INSERT INTO rooms (name, capacity, floor, description, sensor_id) VALUES (?,?,?,?,NULL)",
                    (
                        r.get('name', 'Salle'),
                        r.get('capacity', 10),
                        r.get('floor', 'RDC'),
                        r.get('description', ''),
                    )
                )
            conn.commit()
            print(f"[DB] {len(rooms)} salles importées depuis client.config.json")
        except Exception as e:
            print(f"[DB] Seed rooms skipped: {e}")

    conn.close()
