"""
Script de population de la base de données F1 Tracker.
À lancer une seule fois — reprend là où il s'est arrêté si interrompu.

Usage :
    python populate_db.py
    python populate_db.py --year 2023          # Une seule année
    python populate_db.py --year 2023 --event Monaco  # Un seul GP
"""

import time
import os
import sys
import argparse
import logging
import fastf1
import psycopg2
from psycopg2.extras import execute_batch
from datetime import datetime

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

# Config

DB_CONFIG = {
    "host":     os.getenv("DB_HOST", "localhost"),
    "port":     int(os.getenv("DB_PORT", 5432)),
    "dbname":   os.getenv("DB_NAME", "f1tracker"),
    "user":     os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD", ""),   # à remplir ou via variable d'env
}

YEARS = list(range(2018, 2025))

SESSION_TYPES = ["FP1", "FP2", "FP3", "Q", "SQ", "S", "R"]

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")

# Logging 

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("populate_db.log", encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)

def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def apply_schema(conn):
    schema_path = os.path.join(os.path.dirname(__file__), "script_creation.sql")
    with open(schema_path, "r", encoding="utf-8") as f:
        sql = f.read()
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    log.info("Schéma appliqué.")


def session_exists(conn, year, circuit, session_type):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT id FROM sessions WHERE year=%s AND circuit=%s AND session=%s",
            (year, circuit, session_type),
        )
        row = cur.fetchone()
        return row[0] if row else None

# Population

def process_session(conn, year: int, event_name: str, country: str, session_type: str):
    """Charge une session FastF1 et insère les données en DB."""

    # Déjà en base ?
    if session_exists(conn, year, event_name, session_type):
        log.info(f"  ↳ {year} {event_name} {session_type} — déjà en base, skip")
        return

    log.info(f"  ↳ {year} {event_name} {session_type} — chargement...")

    try:
        sess = fastf1.get_session(year, event_name, session_type)
        sess.load(telemetry=False, weather=False, messages=False)
    except Exception as e:
        log.warning(f"    Impossible de charger : {e}")
        return

    laps_df = sess.laps
    if laps_df is None or laps_df.empty:
        log.warning("    Aucun tour trouvé, skip")
        return

    with conn.cursor() as cur:
        # 1. Insérer la session
        event_date = sess.event.get("EventDate", None)
        if hasattr(event_date, "date"):
            event_date = event_date.date()

        cur.execute(
            """
            INSERT INTO sessions (year, circuit, country, session, date)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (year, circuit, session) DO NOTHING
            RETURNING id
            """,
            (year, event_name, country, session_type, event_date),
        )
        row = cur.fetchone()
        if row is None:
            # Conflit → récupère l'id existant
            cur.execute(
                "SELECT id FROM sessions WHERE year=%s AND circuit=%s AND session=%s",
                (year, event_name, session_type),
            )
            session_id = cur.fetchone()[0]
        else:
            session_id = row[0]

        # 2. Pilotes
        drivers_data = []
        for drv in sess.drivers:
            try:
                info = sess.get_driver(drv)
                drivers_data.append((
                    session_id,
                    str(info.get("Abbreviation", drv))[:4],
                    str(info.get("FullName", "")),
                    str(info.get("TeamName", "")),
                    "#" + str(info.get("TeamColor", "FFFFFF")),
                ))
            except Exception:
                pass

        execute_batch(
            cur,
            """
            INSERT INTO drivers (session_id, code, full_name, team, team_color)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (session_id, code) DO NOTHING
            """,
            drivers_data,
        )

        # 3. Tours
        laps_data = []
        for _, lap in laps_df.iterrows():
            try:
                lt = lap["LapTime"]
                lt_ms = int(lt.total_seconds() * 1000) if hasattr(lt, "total_seconds") else None
            except Exception:
                lt_ms = None

            laps_data.append((
                session_id,
                str(lap.get("Driver", ""))[:4],
                int(lap.get("LapNumber", 0)),
                lt_ms,
                str(lap.get("Compound", "")) or None,
                int(lap.get("TyreLife", 0)) if lap.get("TyreLife") == lap.get("TyreLife") else None,
                bool(lap.get("IsPersonalBest", False)) or (lap.get("Deleted", False) is False),
                lap.get("PitInTime") is not None and lap.get("PitInTime") == lap.get("PitInTime"),
                lap.get("PitOutTime") is not None and lap.get("PitOutTime") == lap.get("PitOutTime"),
            ))

        execute_batch(
            cur,
            """
            INSERT INTO laps
                (session_id, driver_code, lap_number, lap_time_ms,
                 compound, tyre_life, is_valid, pit_in, pit_out)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id, driver_code, lap_number) DO NOTHING
            """,
            laps_data,
        )

    conn.commit()
    log.info(f"{len(laps_data)} tours insérés")


def populate(year_filter=None, event_filter=None):
    fastf1.Cache.enable_cache(CACHE_DIR)

    conn = get_connection()
    apply_schema(conn)

    years = [year_filter] if year_filter else YEARS

    for year in years:
        log.info(f"\n{'─'*60}")
        log.info(f"Année {year}")
        log.info(f"{'─'*60}")

        try:
            schedule = fastf1.get_event_schedule(year, include_testing=False)
        except Exception as e:
            log.error(f"Impossible de récupérer le calendrier {year} : {e}")
            continue

        for _, event in schedule.iterrows():
            event_name = event.get("EventName", "")
            country    = event.get("Country", "")

            if event_filter and event_filter.lower() not in event_name.lower():
                continue

            log.info(f"\n{event_name} ({country})")

            for stype in SESSION_TYPES:
                try:
                    process_session(conn, year, event_name, country, stype)
                except Exception as e:
                    log.error(f"  Erreur inattendue {stype} : {e}")
                    conn.rollback()
                finally:
                    time.sleep(8)

    conn.close()
    log.info("\nPopulation terminée !")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Population de la DB F1 Tracker")
    parser.add_argument("--year",  type=int, help="Limiter à une seule année")
    parser.add_argument("--event", type=str, help="Limiter à un seul GP (ex: Monaco)")
    args = parser.parse_args()

    populate(year_filter=args.year, event_filter=args.event)