from __future__ import annotations
import os, sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH=Path(os.getenv('DATABASE_PATH','/data/hausmonitor.db'))
SCHEMA='''
CREATE TABLE IF NOT EXISTS campaigns(
 id INTEGER PRIMARY KEY AUTOINCREMENT, measured_at TEXT NOT NULL,
 air_temp REAL, wall_temp_sw REAL, wall_temp_so REAL, groundwater REAL,
 weather TEXT, light_mode TEXT, notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS readings(
 id INTEGER PRIMARY KEY AUTOINCREMENT, campaign_id INTEGER NOT NULL,
 point TEXT NOT NULL, sequence INTEGER NOT NULL, value REAL NOT NULL,
 UNIQUE(campaign_id,point,sequence),
 FOREIGN KEY(campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE);
CREATE TABLE IF NOT EXISTS crack_points(
 id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE,
 location TEXT, description TEXT, active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS crack_measurements(
 id INTEGER PRIMARY KEY AUTOINCREMENT, crack_point_id INTEGER NOT NULL,
 measured_at TEXT NOT NULL, air_temp REAL, value REAL NOT NULL,
 photo_path TEXT, notes TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP,
 FOREIGN KEY(crack_point_id) REFERENCES crack_points(id) ON DELETE CASCADE);
CREATE INDEX IF NOT EXISTS idx_readings_campaign ON readings(campaign_id);
CREATE INDEX IF NOT EXISTS idx_crack_measurements_point_date ON crack_measurements(crack_point_id,measured_at);
'''

def init_db():
 DB_PATH.parent.mkdir(parents=True,exist_ok=True)
 with sqlite3.connect(DB_PATH) as con:
  con.execute('PRAGMA foreign_keys=ON'); con.executescript(SCHEMA)

@contextmanager
def connection():
 con=sqlite3.connect(DB_PATH); con.row_factory=sqlite3.Row; con.execute('PRAGMA foreign_keys=ON')
 try:
  yield con; con.commit()
 finally: con.close()
