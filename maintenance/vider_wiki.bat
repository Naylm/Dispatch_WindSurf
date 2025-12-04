@echo off
chcp 65001 >nul
cls

echo ====================================================================
echo   🗑️  VIDER LE WIKI
echo ====================================================================
echo.
echo   ⚠️  ATTENTION : Ce script va supprimer TOUTES les données du Wiki !
echo.
echo   Cela inclut :
echo      • Toutes les catégories
echo      • Toutes les sous-catégories
echo      • Tous les articles
echo      • Tous les votes et l'historique
echo.
echo   Utilisez ce script uniquement si vous voulez repartir à zéro.
echo.
echo ====================================================================
echo.

pause

REM Vérifier si Python est installé
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ ERREUR : Python n'est pas installé
    pause
    exit /b 1
)

REM Activer l'environnement virtuel si disponible
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

REM Exécuter le script de nettoyage
python clear_wiki_categories.py

echo.
echo ====================================================================
pause
