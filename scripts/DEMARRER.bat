@echo off
chcp 65001 >nul
cls

echo ====================================================================
echo   🚀 DISPATCHMANAGER V1.2
echo ====================================================================
echo.

REM Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERREUR : Python n'est pas installé ou n'est pas dans le PATH
    echo.
    echo Veuillez installer Python 3.7+ depuis https://www.python.org
    pause
    exit /b 1
)

REM Vérifier si on est dans le bon dossier (vérifier le dossier parent ou courant)
if exist "app.py" (
    echo ✅ Fichier app.py trouvé dans le dossier courant
    set APP_PATH=app.py
    set VENV_PATH=venv\Scripts\activate.bat
) else if exist "..\app.py" (
    echo ✅ Fichier app.py trouvé dans le dossier parent
    set APP_PATH=..\app.py
    set VENV_PATH=..\venv\Scripts\activate.bat
) else (
    echo ❌ ERREUR : Fichier app.py introuvable
    echo.
    echo Veuillez exécuter ce script depuis le dossier DispatchManagerV1.2
    echo Ou depuis le dossier DispatchManagerV1.2\scripts
    pause
    exit /b 1
)

REM Tuer les anciens processus Python de l'application
echo 🔄 Vérification des processus existants...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5000.*LISTENING"') do (
    echo    Fermeture du processus %%a...
    taskkill /F /PID %%a >nul 2>&1
)
timeout /t 1 /nobreak >nul
echo ✅ Port 5000 disponible
echo.

REM Activer l'environnement virtuel si disponible
if exist "%VENV_PATH%" (
    echo ✅ Activation de l'environnement virtuel...
    call "%VENV_PATH%"
) else (
    echo ⚠️  Environnement virtuel non trouvé, utilisation de Python système
)

REM Démarrer l'application
echo ✅ Démarrage de l'application...
echo 🌐 Accès : http://localhost:5000
echo.
echo Appuyez sur CTRL+C pour arrêter le serveur
echo ====================================================================
echo.

python "%APP_PATH%"

pause
