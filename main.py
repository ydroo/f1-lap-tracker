import fastf1
import plotly.graph_objects as go
import numpy as np
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

ANNEE   = int(saisie_annee)          if saisie_annee   else 2023
COURSE  =     saisie_course          if saisie_course  else "Monaco Grand Prix"
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

tour_rapide = tours_valides.loc[tours_valides["LapTime"].idxmin()]
print(f"\nTour le plus rapide : Tour {int(tour_rapide['LapNumber']):>3}  |  {tour_rapide['LapTime']}  |  {tour_rapide.get('Compound', '—')}")

saisie_tour = input(f"\nNuméro de tour                           [{int(tour_rapide['LapNumber'])}] : ")
TOUR = int(saisie_tour) if saisie_tour else int(tour_rapide['LapNumber'])

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

# Animation
print("\nPréparation de l'animation...")

# Tour le plus rapide de toute la session (tous pilotes) comme référence du circuit
lap_ref = session.laps.pick_fastest()
pos_ref = lap_ref.get_pos_data()
circuit_info = session.get_circuit_info()

# Fonction de rotation des coordonnées (identique à la doc FastF1)
def rotate(xy, angle):
	rot_mat = np.array([[np.cos(angle), np.sin(angle)],
						[-np.sin(angle), np.cos(angle)]])
	return np.matmul(xy, rot_mat)

# Angle de rotation du circuit en radians
track_angle = circuit_info.rotation / 180 * np.pi

track = pos_ref.loc[:, ("X", "Y")].to_numpy()
rotated_track = rotate(track, track_angle)

# Fermeture de la boucle du circuit de référence
rotated_track = np.vstack([rotated_track, rotated_track[0]])

pilot_track = pos.loc[:, ("X", "Y")].to_numpy()
rotated_pilot = rotate(pilot_track, track_angle)

# Sous-échantillonnage pour fluidité (::1 = plus précis, animation plus lente. ::3 = perte de précision, animation fluide)
# ::1 compte tous les points de données (~ 300) pour l'animation, ::2 la moitié, etc...
pos_anim = rotated_pilot[::2]
x = pos_anim[:, 0].tolist()
y = pos_anim[:, 1].tolist()

# Fermeture de la boucle de la trajectoire du pilote
x = x + [x[0]]
y = y + [y[0]]

trace_circuit = go.Scatter(
	x=rotated_track[:, 0],
	y=rotated_track[:, 1],
	mode="lines",
	line=dict(color="rgba(255,255,255,0.15)", width=8),
	name="Circuit",
	hoverinfo="skip",
)

# Numéros de virages
traces_virages = []
offset_vector = [500, 0]
for _, virage in circuit_info.corners.iterrows():
	txt = f"{virage['Number']}{virage['Letter']}"
	offset_angle = virage["Angle"] / 180 * np.pi
	offset_x, offset_y = rotate(offset_vector, offset_angle)
	text_x = virage["X"] + offset_x
	text_y = virage["Y"] + offset_y
	text_x, text_y = rotate([text_x, text_y], track_angle)
	track_x, track_y = rotate([virage["X"], virage["Y"]], track_angle)

	# Ligne entre le circuit et le numéro
	traces_virages.append(go.Scatter(
		x=[track_x, text_x], y=[track_y, text_y],
		mode="lines",
		line=dict(color="grey", width=1),
		hoverinfo="skip",
		showlegend=False,
	))
	# Numéro
	traces_virages.append(go.Scatter(
		x=[text_x], y=[text_y],
		mode="markers+text",
		marker=dict(color="grey", size=16),
		text=[txt],
		textfont=dict(color="white", size=8),
		textposition="middle center",
		hoverinfo="skip",
		showlegend=False,
	))

# Point de la voiture
point_voiture = go.Scatter(
	x=[x[0]], y=[y[0]],
	mode="markers",
	marker=dict(color="white", size=10, symbol="circle"),
	name=PILOTE,
)

# Tracé parcouru (se dessine progressivement)
trace_parcouru = go.Scatter(
	x=[x[0]], y=[y[0]],
	mode="lines",
	line=dict(color="red", width=2),
	name=f"{PILOTE} — Tour {TOUR}",
)

# Données statiques (circuit + virages)
data_statique = [trace_circuit] + traces_virages

# Construction des frames d'animation
frames = []
for i in range(1, len(x) + 1):
	frames.append(go.Frame(
		data=data_statique + [
			go.Scatter(x=x[:i], y=y[:i], mode="lines", line=dict(color="red", width=2)),
			go.Scatter(x=[x[i-1]], y=[y[i-1]], mode="markers", marker=dict(color="white", size=10)),
		],
		name=str(i),
	))

fig = go.Figure(
	data=data_statique + [trace_parcouru, point_voiture],
	frames=frames,
)

fig.update_layout(
	title=f"{PILOTE} — {COURSE} {ANNEE} — Tour {TOUR}",
	xaxis=dict(visible=False),
	yaxis=dict(visible=False, scaleanchor="x"),
	plot_bgcolor="#111111",
	paper_bgcolor="#111111",
	font=dict(color="white"),
	showlegend=False,
	# Boutons play / pause
	updatemenus=[dict(
		type="buttons",
		showactive=False,
		y=-0.08,
		x=0.5,
		xanchor="center",
		buttons=[
			dict(
				label="▶  Play",
				method="animate",
				args=[None, dict(frame=dict(duration=30, redraw=True), fromcurrent=True)],
			),
			dict(
				label="⏸  Pause",
				method="animate",
				args=[[None], dict(frame=dict(duration=0, redraw=False), mode="immediate")],
			),
		],
	)],
	# Slider de progression
	sliders=[dict(
		currentvalue=dict(visible=False),
		pad=dict(t=40),
		steps=[
			dict(method="animate", args=[[str(i)], dict(mode="immediate", frame=dict(duration=0))], label="")
			for i in range(1, len(x) + 1)
		],
	)],
)

print("Ouverture de l'animation dans le navigateur...")
fig.show()