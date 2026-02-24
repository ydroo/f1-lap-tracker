#!/bin/bash

echo "+-----F1 LAP TRACKER v2.0-----+"
echo ""

cd backend

echo "[1/3] Installation des dépendances..."
pip install -r dependances.txt > /dev/null 2>&1

echo "[2/3] Lancement du serveur API..."
python main.py &
BACKEND_PID=$!

echo "Attente du démarrage du serveur..."
sleep 3

echo "[3/3] Lancement du serveur frontend..."
cd ../frontend

# Détection de l'OS et ouverture du navigateur
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open http://localhost:3000
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v xdg-open > /dev/null; then
        xdg-open http://localhost:3000
    fi
fi

echo ""
echo "  Application lancée !"
echo "  - API : http://localhost:8000"
echo "  - Docs : http://localhost:8000/docs"
echo "  - Frontend : http://localhost:3000"
echo ""
echo "Appuyez sur Ctrl+C pour arrêter"
echo ""

# Lancer le serveur frontend
python3 -m http.server 3000

# Cleanup à la fermeture
trap "kill $BACKEND_PID 2>/dev/null; exit" INT TERM
wait