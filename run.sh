#!/bin/bash
echo "+-----F1 LAP TRACKER v2.0-----+"
echo ""

cd backend
echo "[1/3] Installation des dependances..."
pip install -r dependances.txt > /dev/null 2>&1

echo "[2/3] Lancement du serveur API (port 8000)..."
python3 main.py &
BACKEND_PID=$!

echo "Attente du demarrage du serveur..."
sleep 3

echo "[3/3] Ouverture de l'interface (port 3000)..."
cd ../frontend

# Ouverture du navigateur
if [[ "$OSTYPE" == "darwin"* ]]; then
	open http://localhost:3000
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
	xdg-open http://localhost:3000 2>/dev/null
fi

echo ""
echo "  Application lancee !"
echo "  - API      : http://localhost:8000"
echo "  - Docs     : http://localhost:8000/docs"
echo "  - Frontend : http://localhost:3000"
echo ""
echo "Appuyez sur Ctrl+C pour arreter"
echo ""

# Cleanup au Ctrl+C
trap "echo ''; echo 'Arret...'; kill $BACKEND_PID 2>/dev/null; exit" INT TERM

python3 -m http.server 3000