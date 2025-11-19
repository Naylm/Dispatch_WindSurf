@echo off
chcp 65001 >nul
cls

echo ====================================================================
echo   🚀 DISPATCHMANAGER V1.2 - DÉMARRAGE SÉCURISÉ
echo ====================================================================
echo.
echo   📋 Ce script va :
echo      1. Vérifier l'intégrité de la base de données
echo      2. Créer un backup automatique
echo      3. Démarrer l'application
echo.
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

REM Vérifier si on est dans le bon dossier
if not exist "app.py" (
    echo ❌ ERREUR : Fichier app.py introuvable
    echo.
    echo Veuillez exécuter ce script depuis le dossier DispatchManagerV1.2
    pause
    exit /b 1
)

REM Vérifier si on est dans le bon dossier pour le script de démarrage avec backup
if not exist "start_with_backup.py" (
    echo ❌ ERREUR : Fichier start_with_backup.py introuvable
    echo.
    echo Veuillez exécuter ce script depuis le dossier DispatchManagerV1.2
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
if exist "venv\Scripts\activate.bat" (
    echo 🔧 Activation de l'environnement virtuel...
    call venv\Scripts\activate.bat
    echo ✅ Environnement virtuel activé
    echo.
)

REM Démarrer avec backup automatique
echo 🚀 Démarrage de l'application avec backup automatique...
echo.
python start_with_backup.py

pause
