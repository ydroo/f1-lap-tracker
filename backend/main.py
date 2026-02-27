import os
import numpy as np
import fastf1
import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from dotenv import load_dotenv
load_dotenv()

# Config

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "cache")
os.makedirs(CACHE_DIR, exist_ok=True)
fastf1.Cache.enable_cache(CACHE_DIR)

DB_CONFIG = {
	"host":     os.getenv("DB_HOST", "localhost"),
	"port":     int(os.getenv("DB_PORT", 5432)),
	"dbname":   os.getenv("DB_NAME", "f1tracker"),
	"user":     os.getenv("DB_USER", "postgres"),
	"password": os.getenv("DB_PASSWORD", ""),
}

app = FastAPI(title="F1 Lap Tracker API")

app.add_middleware(GZipMiddleware, minimum_size=1000)
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_methods=["*"],
	allow_headers=["*"],
)

# BDD helpers

def get_db():
	return psycopg2.connect(**DB_CONFIG, cursor_factory=psycopg2.extras.RealDictCursor)


def query(sql: str, params=None):
	with get_db() as conn:
		with conn.cursor() as cur:
			cur.execute(sql, params)
			return cur.fetchall()


def rotate(xy, angle):
	rot_mat = np.array([[np.cos(angle), np.sin(angle)],
						[-np.sin(angle), np.cos(angle)]])
	return np.matmul(xy, rot_mat)


# Routes BDD (instantanées)

@app.get("/years")
def get_years():
	"""Années disponibles en base."""
	rows = query("SELECT DISTINCT year FROM sessions ORDER BY year DESC")
	return [r["year"] for r in rows]


@app.get("/events/{year}")
def get_events(year: int):
	"""Circuits d'une année."""
	rows = query(
		"SELECT DISTINCT circuit, country FROM sessions WHERE year=%s ORDER BY circuit",
		(year,),
	)
	return [{"circuit": r["circuit"], "country": r["country"]} for r in rows]


@app.get("/sessions/{year}/{event}")
def get_sessions(year: int, event: str):
	"""Types de sessions disponibles pour un GP."""
	rows = query(
		"SELECT DISTINCT session FROM sessions WHERE year=%s AND circuit=%s ORDER BY session",
		(year, event),
	)
	return [r["session"] for r in rows]


@app.get("/drivers/{year}/{event}/{session}")
def get_drivers(year: int, event: str, session: str):
	"""Pilotes d'une session avec leur couleur d'écurie."""
	rows = query(
		"""
		SELECT d.code, d.full_name, d.team, d.team_color
		FROM drivers d
		JOIN sessions s ON s.id = d.session_id
		WHERE s.year=%s AND s.circuit=%s AND s.session=%s
		ORDER BY d.code
		""",
		(year, event, session),
	)
	return [dict(r) for r in rows]


@app.get("/laps/{year}/{event}/{session}/{driver}")
def get_laps(year: int, event: str, session: str, driver: str):
	"""Tours d'un pilote avec temps et composé."""
	rows = query(
		"""
		SELECT l.lap_number, l.lap_time_ms, l.compound, l.tyre_life,
			l.is_valid, l.pit_in, l.pit_out
		FROM laps l
		JOIN sessions s ON s.id = l.session_id
		WHERE s.year=%s AND s.circuit=%s AND s.session=%s
		AND l.driver_code=%s AND l.lap_time_ms IS NOT NULL
		ORDER BY l.lap_number
		""",
		(year, event, session, driver),
	)
	return [dict(r) for r in rows]


# Route FastF1 (GPS uniquement pour l'animation)

@app.get("/position/{year}/{event}/{session}/{driver}/{lap}")
def get_position(year: int, event: str, session: str, driver: str, lap: int):
	"""
	Données GPS d'un tour — appel FastF1.
	Utilisé uniquement quand l'utilisateur lance l'animation.
	"""
	try:
		sess = fastf1.get_session(year, event, session)
		sess.load(telemetry=True, weather=False, messages=False)
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Erreur FastF1 : {e}")

	# Circuit de référence — meilleur tour de la session (pick_fastest)
	try:
		circuit_info = sess.get_circuit_info()
		lap_ref = sess.laps.pick_fastest()
		pos_ref = lap_ref.get_pos_data()

		x_ref = pos_ref["X"].values.tolist()
		y_ref = pos_ref["Y"].values.tolist()

		# Virages avec offset (numéro décalé + ligne de connexion), sans rotation
		corner_points = []
		offset_vector = [500, 0]

		for _, corner in circuit_info.corners.iterrows():
			offset_angle = corner["Angle"] / 180 * np.pi
			off_x, off_y = rotate(offset_vector, offset_angle)

			corner_points.append({
				"number":  f"{int(corner['Number'])}{corner.get('Letter', '') or ''}",
				"track_x": float(corner["X"]),
				"track_y": float(corner["Y"]),
				"text_x":  float(corner["X"] + off_x),
				"text_y":  float(corner["Y"] + off_y),
			})

	except Exception:
		x_ref, y_ref, corner_points = [], [], []

	# Trajectoire du pilote pour ce tour
	try:
		driver_laps = sess.laps.pick_driver(driver)
		driver_lap  = driver_laps[driver_laps["LapNumber"] == lap].iloc[0]
		pos_data    = driver_lap.get_pos_data()
		sampled     = pos_data.iloc[::2]

		x = sampled["X"].values.tolist()
		y = sampled["Y"].values.tolist()
		t = pos_data["Time"].dt.total_seconds().tolist()[::2]
	except Exception as e:
		raise HTTPException(status_code=404, detail=f"Tour introuvable : {e}")

	# Couleur de l'écurie depuis la DB
	rows = query(
		"""
		SELECT d.team_color FROM drivers d
		JOIN sessions s ON s.id = d.session_id
		WHERE s.year=%s AND s.circuit=%s AND s.session=%s AND d.code=%s
		""",
		(year, event, session, driver),
	)
	color = rows[0]["team_color"] if rows else "#FFFFFF"

	return {
		"track":   {"x": x_ref, "y": y_ref},
		"corners": corner_points,
		"driver":  {"code": driver, "color": color, "x": x, "y": y, "t": t},
	}

# Santé

@app.get("/health")
def health():
	try:
		query("SELECT 1")
		return {"status": "ok", "db": "connected"}
	except Exception as e:
		return {"status": "error", "db": str(e)}

if __name__ == "__main__":
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=8000)