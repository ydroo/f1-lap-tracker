@echo off
echo +-----F1 LAP TRACKER v2.0-----+
echo.

cd backend
echo [1/3] Installation des dependances...
pip install -r dependances.txt >nul 2>&1

echo [2/3] Lancement du serveur API...
start /B python main.py

echo Attente du demarrage du serveur...
timeout /t 3 /nobreak >nul

echo [3/3] Ouverture de l'interface...
cd ../frontend
start http://localhost:3000
python -m http.server 3000

echo.
echo Application arretee.
pause