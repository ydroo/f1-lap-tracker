import fastf1
import os

# Mise en cache pour accélérer les exécutions suivantes
os.makedirs("./cache", exist_ok=True)
fastf1.Cache.enable_cache("./cache")

ANNEE    = 2023
COURSE   = "Monaco Grand Prix"
SESSION  = "R"   # R = Course, Q = Qualifications, FP1/FP2/FP3 = Essais libres
PILOTE   = "VER"
TOUR     = 40

# Chargement de la session
print(f"Chargement : {COURSE} {ANNEE} — {SESSION}")
print("(La première exécution peut prendre quelques instants...)")
session = fastf1.get_session(ANNEE, COURSE, SESSION)
session.load(telemetry=True, laps=True, weather=False, messages=False)

# Récupération du tour
tours_pilote = session.laps.pick_drivers(PILOTE)
tour = tours_pilote[tours_pilote["LapNumber"] == TOUR].iloc[0]

# Récupération des données de position
pos = tour.get_pos_data()

# Affichage
print(f"\n{PILOTE} — {COURSE} {ANNEE} — Tour {TOUR}")
print(f"Temps au tour : {tour['LapTime']}")
print(f"Points de données : {len(pos)}")
print()
print(pos[["Time", "X", "Y", "Z"]])