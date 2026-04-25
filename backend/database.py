import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "data/rate.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys = ON")  # active les FK (CASCADE DELETE, etc.)
    return conn

def init_db():
    with get_db() as conn:
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