import fastf1
import plotly.graph_objects as go
import pandas as pd
import os

# Mise en cache pour accélérer les exécutions suivantes
os.makedirs("./cache", exist_ok=True)
fastf1.Cache.enable_cache("./cache")

print("╔══════════════════════════════╗")
print("║        F1 LAP TRACKER        ║")
print("╚══════════════════════════════╝")
print()

saisie_annee   = input("Année          (ex: 2023)                [2023] : ")
saisie_course  = input("Course         (ex: Monaco Grand Prix)   [Monaco Grand Prix] : ")
saisie_session = input("Session        (R / Q / FP1 / FP2 / FP3) [R] : ")
saisie_pilote  = input("Pilote         (ex: VER, HAM, LEC)       [VER] : ")

ANNEE   = int(saisie_annee)        if saisie_annee   else 2023
COURSE  =     saisie_course        if saisie_course  else "Monaco Grand Prix"
SESSION =     saisie_session.upper() if saisie_session else "R"
PILOTE  =     saisie_pilote.upper()  if saisie_pilote  else "VER"

# Chargement de la session
print(f"\nChargement : {COURSE} {ANNEE} {SESSION}")
print("(La première exécution peut prendre quelques instants...)")
session = fastf1.get_session(ANNEE, COURSE, SESSION)
session.load(telemetry=True, laps=True, weather=False, messages=False)
tours_pilote = session.laps.pick_drivers(PILOTE)

# Affichage des tours disponibles (on exclut les tours sans temps, ex: crash ou VSC)
tours_valides = tours_pilote[tours_pilote["LapTime"].notna()]
print(f"\nTours disponibles pour {PILOTE} à {COURSE} {ANNEE}:")
for _, t in tours_valides.iterrows():
    print(f"  Tour {int(t['LapNumber']):>3}  |  {t['LapTime']}  |  {t.get('Compound', '—')}")

premier_tour_valide = int(tours_valides.iloc[0]["LapNumber"])
saisie_tour = input(f"\nNuméro de tour                           [{premier_tour_valide}] : ")
TOUR = int(saisie_tour) if saisie_tour else premier_tour_valide

# Vérification que le tour saisi est bien valide
if TOUR not in tours_valides["LapNumber"].values:
    print(f"\nErreur : le tour {TOUR} n'est pas disponible pour {PILOTE} à {COURSE} {ANNEE}.")
    exit()

tour = tours_pilote[tours_pilote["LapNumber"] == TOUR].iloc[0]
pos = tour.get_pos_data()

# Affichage terminal
print(f"\n{PILOTE} — {COURSE} {ANNEE} — Tour {TOUR}")
print(f"Temps au tour : {tour['LapTime']}")
print(f"Points de données : {len(pos)}")
print()
print(pos[["Time", "X", "Y", "Z"]])

# Affichage graphique de la trajectoire
print("\nOuverture du graphique dans le navigateur...")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=pos["X"],
    y=pos["Y"],
    mode="lines",
    line=dict(color="red", width=2),
    name=f"{PILOTE} — Tour {TOUR}",
))

fig.update_layout(
    title=f"{PILOTE} — {COURSE} {ANNEE} — Tour {TOUR}",
    xaxis=dict(visible=False),
    yaxis=dict(visible=False, scaleanchor="x"),  # garde les proportions du circuit
    plot_bgcolor="#111111",
    paper_bgcolor="#111111",
    font=dict(color="white"),
)

fig.show()