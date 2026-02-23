import fastf1
import plotly.graph_objects as go
import os

# Mise en cache pour accélérer les exécutions suivantes
os.makedirs("./cache", exist_ok=True)
fastf1.Cache.enable_cache("./cache")

print("╔══════════════════════════════╗")
print("║        F1 LAP TRACKER        ║")
print("╚══════════════════════════════╝")
print()

ANNEE   = int(input("Année          (ex: 2023)                : "))
COURSE  =     input("Course         (ex: Monaco Grand Prix)   : ")
SESSION =     input("Session        (R / Q / FP1 / FP2 / FP3) : ").upper()
PILOTE  =     input("Pilote         (ex: VER, HAM, LEC)       : ").upper()
TOUR    = int(input("Numéro de tour (ex: 40)                  : "))

# Chargement de la session
print(f"\nChargement : {COURSE} {ANNEE} {SESSION}")
print("(La première exécution peut prendre quelques instants...)")
session = fastf1.get_session(ANNEE, COURSE, SESSION)
session.load(telemetry=True, laps=True, weather=False, messages=False)

# Récupération du tour
tours_pilote = session.laps.pick_drivers(PILOTE)
tour = tours_pilote[tours_pilote["LapNumber"] == TOUR].iloc[0]

# Récupération des données de position
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