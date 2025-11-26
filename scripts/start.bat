@echo off
REM ============================================
REM Script de démarrage rapide - Windows
REM Dispatch Manager Docker
REM ============================================

echo.
echo ========================================
echo   Dispatch Manager - Demarrage
echo ========================================
echo.

REM Vérifier si Docker est installé
docker --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Docker n'est pas installe ou pas dans le PATH
    echo Installez Docker Desktop depuis https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Vérifier si docker-compose est installé
docker-compose --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERREUR] Docker Compose n'est pas installe
    echo Installez Docker Desktop qui inclut Docker Compose
    pause
    exit /b 1
)

echo [OK] Docker est installe
echo.

REM Vérifier si .env existe, sinon le créer
if not exist .env (
    echo [INFO] Creation du fichier .env...
    copy .env.example .env >nul 2>&1
    echo [ATTENTION] N'oubliez pas de modifier .env avec vos valeurs !
    echo.
)

echo [INFO] Demarrage des conteneurs Docker...
docker-compose up -d

if %errorlevel% neq 0 (
    echo.
    echo [ERREUR] Echec du demarrage
    echo Verifiez les logs avec : docker-compose logs
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Installation terminee !
echo ========================================
echo.
echo  Application disponible sur : http://localhost
echo.
echo  Commandes utiles :
echo    - Voir les logs     : docker-compose logs -f
echo    - Arreter           : docker-compose down
echo    - Redemarrer        : docker-compose restart
echo.
echo ========================================
echo.

pause
