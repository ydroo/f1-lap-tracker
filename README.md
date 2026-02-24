# F1 Lap Tracker

![Python](https://img.shields.io/badge/Python-3.8+-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Data](https://img.shields.io/badge/Data-FastF1-red)

Outil pour traquer les positions d'une voiture de Formule 1 tour par tour suivant une course donnée. Base d'un projet de simulation de trajectoire en cours de développement.
L'idée de ce projet m'est venue après avoir découvert la librairie FastF1(https://docs.fastf1.dev/).

## Démo

```
╔══════════════════════════════╗
║        F1 LAP TRACKER        ║
╚══════════════════════════════╝

Année          (ex: 2023)                [2023] :
Course         (ex: Monaco Grand Prix)   [Monaco Grand Prix] :
Session        (R / Q / FP1 / FP2 / FP3) [R] :
Pilote         (ex: VER, HAM, LEC)       [VER] :

Tours disponibles pour VER à Monaco Grand Prix 2023:
  Tour   1  |  0 days 00:01:24.238000  |  MEDIUM
  Tour   2  |  0 days 00:01:19.367000  |  MEDIUM
  ...
⚡ Tour le plus rapide : Tour  23  |  0 days 00:01:16.604000  |  MEDIUM

Numéro de tour  [23] :
```
Les valeurs notés entre crochets ici sont les valeurs par défaut, elle sont retenu si l'input est vide.
Le programme ouvre ensuite une animation dans le navigateur avec le tracé du circuit, les numéros de virages et le point de la voiture qui se déplace (pas du tout en temps réel).

![Demo F1 Lap Tracker](demo.gif)

## Installation

```bash
# Cloner le projet 
git clone https://github.com/ydroo/f1-lap-tracker.git
cd f1-lap-tracker

# Installer les dépendances (l'application vérifie et installe les dépendances si nécessaire à la première éxécution)
pip install -r dependances.txt

# Lancer
python main.py
```

Ou double-cliquer sur `run.bat` (Windows) / `./run.sh` (Linux/macOS) — installe les dépendances et lance le programme automatiquement.

## Objectif du projet

Ce projet a pour but de :

- Explorer les données télémétriques F1
- Manipuler des données temporelles complexes
- Visualiser des trajectoires dynamiques
- Préparer une future simulation temps réel

Il s'agit d'une base pour un futur simulateur d'analyse de performance.

## Fonctionnalités

- Saisie interactive avec valeurs par défaut (appuyer sur Entrée pour les utiliser)
- Affichage des tours disponibles avec temps au tour et composé de pneu
- Tour le plus rapide mis en avant automatiquement
- Tracé du circuit basé sur le tour le plus rapide de la session
- Numéros de virages annotés autour du circuit
- Animation avec boutons Play/Pause et slider de progression
- Couleur officielle de l'écurie pour le tracé du pilote

## Limitations actuelles

- Animation non synchronisée au temps réel du tour
- Un seul pilote à la fois
- Pas d'analyse télémétrique détaillée (vitesse, DRS, etc.)
- Interface de saisie uniquement au terminal

## Données

La librairie utilisée, FastF1, récupère les données directement depuis le flux officiel F1. Les données sont disponibles de **2018 à aujourd'hui** pour les sessions suivantes :

| Code | Session |
|------|---------|
| `R`  | Course |
| `Q`  | Qualifications |
| `FP1` / `FP2` / `FP3` | Essais libres |

> La première exécution pour une session donnée peut prendre quelques instants - l'application télécharge et met en cache les données localement dans un sous-dossier `./cache/`.

## Structure

```
f1-lap-tracker/
├── main.py            # Script principal
├── dependances.txt    # Dépendances Python
├── run.bat            # Lancement Windows
├── run.sh             # Lancement Linux/macOS
├── README.md
├── LICENSE
└── cache/             # Données FastF1 (ignoré par git)
```
Attention ! Le sous-dossier `./cache/` peut s'avérer être très volumineux après avoir exploré de nombreux circuits et pilotes avec l'application. Pensez à le nettoyer pour libérer de l'espace sur votre appareil.

## Prochaines étapes (ordre non exhaustif)

- Interface web avec Dash (remplacement du terminal)
- Mode multi-pilotes sur le même tour
- Onglets de statistiques (temps au tour, télémétrie, etc...)
- Déploiement en ligne
- Simulation en temps réel : Si le tour exploré a été effectué en 1min30, faire une animation de durée identique ou accélérée.
- Afficher le circuit correspondant en arrière plan du tracé, avec les détails et affichages nécessaires
- Etc...

## Licence

MIT — voir [LICENSE](LICENSE)
