from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import fastf1
import fastf1.plotting
import numpy as np
import os
from typing import List, Dict, Any
from pydantic import BaseModel

# Configuration du cache FastF1
os.makedirs("./cache", exist_ok=True)
fastf1.Cache.enable_cache("./cache")

app = FastAPI(title="F1 Lap Tracker API")

# CORS pour permettre au frontend d'appeler l'API
app.add_middleware(
	CORSMiddleware,
	allow_origins=["*"],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Models Pydantic pour la validation des réponses
class EventInfo(BaseModel):
	name: str
	location: str
	country: str

class DriverInfo(BaseModel):
	code: str
	full_name: str
	team: str
	color: str

class LapInfo(BaseModel):
	lap_number: int
	lap_time: str
	compound: str
	is_fastest: bool

class PositionData(BaseModel):
	x: List[float]
	y: List[float]
	circuit_x: List[float]
	circuit_y: List[float]
	corners: List[Dict[str, Any]]
	driver_color: str
	lap_time: str

@app.get("/")
async def root():
	return {
		"message": "F1 Lap Tracker API",
		"version": "2.0.0",
		"endpoints": {
			"years": "/years",
			"events": "/events/{year}",
			"drivers": "/drivers/{year}/{event}/{session}",
			"laps": "/laps/{year}/{event}/{session}/{driver}",
			"position": "/position/{year}/{event}/{session}/{driver}/{lap}"
		}
	}

@app.get("/years", response_model=List[int])
async def get_years():
	"""Retourne la liste des années disponibles (2018-2025)"""
	return list(range(2018, 2026))

@app.get("/events/{year}", response_model=List[EventInfo])
async def get_events(year: int):
	"""Retourne la liste des événements (courses) pour une année donnée"""
	try:
		schedule = fastf1.get_event_schedule(year)
		events = []
		for _, event in schedule.iterrows():
			# On ne garde que les événements de type "Race"
			if event.get('EventFormat') != 'testing':
				events.append(EventInfo(
					name=event['EventName'],
					location=event.get('Location', ''),
					country=event.get('Country', '')
				))
		return events
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des événements: {str(e)}")

@app.get("/drivers/{year}/{event}/{session}", response_model=List[DriverInfo])
async def get_drivers(year: int, event: str, session: str):
	"""Retourne la liste des pilotes pour une session donnée"""
	try:
		sess = fastf1.get_session(year, event, session)
		sess.load(laps=True, telemetry=False, weather=False, messages=False)
		
		drivers_info = []
		drivers_seen = set()
		
		for driver_code in sess.laps['Driver'].dropna().unique():
			if driver_code in drivers_seen:
				continue
			drivers_seen.add(driver_code)
			
			# Récupération des infos du pilote
			driver_laps = sess.laps.pick_drivers(driver_code)
			if len(driver_laps) > 0:
				first_lap = driver_laps.iloc[0]
				team = first_lap.get('Team', 'Unknown')
				
				# Couleur de l'écurie
				try:
					color = fastf1.plotting.get_driver_color(driver_code, sess)
				except:
					color = "#FFFFFF"
				
				# Nom complet du pilote
				try:
					full_name = first_lap.get('Driver', driver_code)
				except:
					full_name = driver_code
				
				drivers_info.append(DriverInfo(
					code=driver_code,
					full_name=full_name,
					team=team,
					color=color
				))
		
		return sorted(drivers_info, key=lambda x: x.code)
		
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des pilotes: {str(e)}")

@app.get("/laps/{year}/{event}/{session}/{driver}", response_model=List[LapInfo])
async def get_laps(year: int, event: str, session: str, driver: str):
	"""Retourne la liste des tours valides pour un pilote"""
	try:
		sess = fastf1.get_session(year, event, session)
		sess.load(laps=True, telemetry=False, weather=False, messages=False)
		
		driver_laps = sess.laps.pick_drivers(driver)
		valid_laps = driver_laps[driver_laps["LapTime"].notna()]
		
		if len(valid_laps) == 0:
			return []
		
		# Trouver le tour le plus rapide
		fastest_lap_idx = valid_laps["LapTime"].idxmin()
		
		laps_info = []
		for _, lap in valid_laps.iterrows():
			lap_time_str = str(lap['LapTime']).split()[-1] if lap['LapTime'] else "N/A"
			
			laps_info.append(LapInfo(
				lap_number=int(lap['LapNumber']),
				lap_time=lap_time_str,
				compound=lap.get('Compound', '—'),
				is_fastest=(lap.name == fastest_lap_idx)
			))
		
		return sorted(laps_info, key=lambda x: x.lap_number)
		
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des tours: {str(e)}")

@app.get("/position/{year}/{event}/{session}/{driver}/{lap}", response_model=PositionData)
async def get_position_data(year: int, event: str, session: str, driver: str, lap: int):
	"""Retourne les données de position pour un tour spécifique"""
	try:
		sess = fastf1.get_session(year, event, session)
		sess.load(telemetry=True, laps=True, weather=False, messages=False)
		
		# Récupération du tour du pilote
		driver_laps = sess.laps.pick_drivers(driver)
		target_lap = driver_laps[driver_laps["LapNumber"] == lap]
		
		if len(target_lap) == 0:
			raise HTTPException(status_code=404, detail=f"Tour {lap} non trouvé pour {driver}")
		
		lap_data = target_lap.iloc[0]
		lap_time_str = str(lap_data['LapTime']).split()[-1] if lap_data['LapTime'] else "N/A"
		
		# Position du pilote
		pos = lap_data.get_pos_data()
		
		# Tour de référence du circuit (tour le plus rapide de la session)
		fastest_lap = sess.laps.pick_fastest()
		pos_ref = fastest_lap.get_pos_data()
		
		# Informations du circuit
		circuit_info = sess.get_circuit_info()
		
		# Fonction de rotation
		def rotate(xy, angle):
			rot_mat = np.array([[np.cos(angle), np.sin(angle)],
								[-np.sin(angle), np.cos(angle)]])
			return np.matmul(xy, rot_mat)
		
		track_angle = circuit_info.rotation / 180 * np.pi
		
		# Rotation du circuit de référence
		track = pos_ref.loc[:, ("X", "Y")].to_numpy()
		rotated_track = rotate(track, track_angle)
		
		# Rotation de la trajectoire du pilote
		pilot_track = pos.loc[:, ("X", "Y")].to_numpy()
		rotated_pilot = rotate(pilot_track, track_angle)
		
		# Sous-échantillonnage pour l'animation (::2)
		rotated_pilot_sampled = rotated_pilot[::2]
		
		# Conversion en listes pour JSON
		x_pilot = rotated_pilot_sampled[:, 0].tolist()
		y_pilot = rotated_pilot_sampled[:, 1].tolist()
		x_circuit = rotated_track[:, 0].tolist()
		y_circuit = rotated_track[:, 1].tolist()
		
		# Virages
		corners = []
		offset_vector = [500, 0]
		for _, corner in circuit_info.corners.iterrows():
			offset_angle = corner["Angle"] / 180 * np.pi
			offset_x, offset_y = rotate(offset_vector, offset_angle)
			text_x = corner["X"] + offset_x
			text_y = corner["Y"] + offset_y
			text_x_rot, text_y_rot = rotate([text_x, text_y], track_angle)
			track_x, track_y = rotate([corner["X"], corner["Y"]], track_angle)
			
			corners.append({
				"number": f"{corner['Number']}{corner.get('Letter', '')}",
				"track_x": float(track_x),
				"track_y": float(track_y),
				"text_x": float(text_x_rot),
				"text_y": float(text_y_rot)
			})
		
		# Couleur du pilote
		try:
			color = fastf1.plotting.get_driver_color(driver, sess)
		except:
			color = "#FFFFFF"
		
		return PositionData(
			x=x_pilot,
			y=y_pilot,
			circuit_x=x_circuit,
			circuit_y=y_circuit,
			corners=corners,
			driver_color=color,
			lap_time=lap_time_str
		)
		
	except HTTPException:
		raise
	except Exception as e:
		raise HTTPException(status_code=500, detail=f"Erreur lors de la récupération des données: {str(e)}")

if __name__ == "__main__":
	import uvicorn
	uvicorn.run(app, host="0.0.0.0", port=8000)