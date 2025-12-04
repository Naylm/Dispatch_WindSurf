# ============================================
# Script PowerShell - Dispatch Manager
# ============================================
# Équivalent du Makefile pour Windows
# Usage: .\dispatch.ps1 <commande>

param(
    [Parameter(Position=0)]
    [string]$Command = "help",
    
    [Parameter(Position=1)]
    [string]$File = ""
)

function Show-Help {
    Write-Host ""
    Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║   Dispatch Manager - Docker Helper    ║" -ForegroundColor Cyan
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Commandes disponibles :" -ForegroundColor Green
    Write-Host "  help         " -NoNewline -ForegroundColor Cyan
    Write-Host "- Afficher cette aide"
    Write-Host "  init         " -NoNewline -ForegroundColor Cyan
    Write-Host "- Installation complète (première fois)"
    Write-Host "  up           " -NoNewline -ForegroundColor Cyan
    Write-Host "- Démarrer tous les services"
    Write-Host "  down         " -NoNewline -ForegroundColor Cyan
    Write-Host "- Arrêter tous les services"
    Write-Host "  restart      " -NoNewline -ForegroundColor Cyan
    Write-Host "- Redémarrer tous les services"
    Write-Host "  build        " -NoNewline -ForegroundColor Cyan
    Write-Host "- Construire les images Docker"
    Write-Host "  logs         " -NoNewline -ForegroundColor Cyan
    Write-Host "- Afficher les logs (CTRL+C pour quitter)"
    Write-Host "  logs-app     " -NoNewline -ForegroundColor Cyan
    Write-Host "- Logs de l'application uniquement"
    Write-Host "  logs-nginx   " -NoNewline -ForegroundColor Cyan
    Write-Host "- Logs Nginx uniquement"
    Write-Host "  logs-db      " -NoNewline -ForegroundColor Cyan
    Write-Host "- Logs PostgreSQL uniquement"
    Write-Host "  ps           " -NoNewline -ForegroundColor Cyan
    Write-Host "- Afficher l'état des conteneurs"
    Write-Host "  shell        " -NoNewline -ForegroundColor Cyan
    Write-Host "- Shell interactif (app)"
    Write-Host "  shell-db     " -NoNewline -ForegroundColor Cyan
    Write-Host "- Shell PostgreSQL (psql)"
    Write-Host "  backup       " -NoNewline -ForegroundColor Cyan
    Write-Host "- Sauvegarder la base de données"
    Write-Host "  restore      " -NoNewline -ForegroundColor Cyan
    Write-Host "- Restaurer la base (Usage: .\dispatch.ps1 restore backup.sql)"
    Write-Host "  clean        " -NoNewline -ForegroundColor Cyan
    Write-Host "- Nettoyer conteneurs et volumes"
    Write-Host "  rebuild      " -NoNewline -ForegroundColor Cyan
    Write-Host "- Reconstruire et redémarrer"
    Write-Host "  status       " -NoNewline -ForegroundColor Cyan
    Write-Host "- Afficher l'état complet"
    Write-Host "  debug-login  " -NoNewline -ForegroundColor Cyan
    Write-Host "- Diagnostiquer problèmes de connexion"
    Write-Host "  reset-admin  " -NoNewline -ForegroundColor Cyan
    Write-Host "- Réinitialiser mot de passe admin"
    Write-Host ""
}

function Invoke-Init {
    Write-Host ""
    Write-Host "🎯 Initialisation de Dispatch Manager..." -ForegroundColor Cyan
    
    if (!(Test-Path .env)) {
        Write-Host "📝 Création du fichier .env..." -ForegroundColor Yellow
        Copy-Item .env.example .env
        Write-Host "⚠️  N'oubliez pas de modifier .env avec vos valeurs !" -ForegroundColor Yellow
    }
    
    Write-Host "🔨 Construction des images..." -ForegroundColor Green
    docker-compose build
    
    Write-Host "🚀 Démarrage des services..." -ForegroundColor Green
    docker-compose up -d
    
    Write-Host ""
    Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║  ✅ Installation terminée !            ║" -ForegroundColor Green
    Write-Host "╠════════════════════════════════════════╣" -ForegroundColor Green
    Write-Host "║  🌐 Application : http://localhost     ║" -ForegroundColor Green
    Write-Host "║  📋 Voir les logs : .\dispatch.ps1 logs║" -ForegroundColor Green
    Write-Host "║  ⏸️  Arrêter : .\dispatch.ps1 down     ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
}

switch ($Command.ToLower()) {
    "help" {
        Show-Help
    }
    "init" {
        Invoke-Init
    }
    "build" {
        Write-Host "🔨 Construction des images Docker..." -ForegroundColor Green
        docker-compose build
    }
    "up" {
        Write-Host "🚀 Démarrage de l'application..." -ForegroundColor Green
        docker-compose up -d
        Write-Host "✅ Application disponible sur http://localhost" -ForegroundColor Green
    }
    "down" {
        Write-Host "⏸️  Arrêt de l'application..." -ForegroundColor Yellow
        docker-compose down
    }
    "restart" {
        Write-Host "🔄 Redémarrage de l'application..." -ForegroundColor Yellow
        docker-compose restart
    }
    "logs" {
        Write-Host "📋 Logs en temps réel..." -ForegroundColor Cyan
        docker-compose logs -f
    }
    "logs-app" {
        Write-Host "📋 Logs Flask/Gunicorn..." -ForegroundColor Cyan
        docker-compose logs -f app
    }
    "logs-nginx" {
        Write-Host "📋 Logs Nginx..." -ForegroundColor Cyan
        docker-compose logs -f nginx
    }
    "logs-db" {
        Write-Host "📋 Logs PostgreSQL..." -ForegroundColor Cyan
        docker-compose logs -f postgres
    }
    "ps" {
        Write-Host "📊 État des conteneurs :" -ForegroundColor Cyan
        docker-compose ps
    }
    "shell" {
        Write-Host "🐚 Shell interactif (app)..." -ForegroundColor Cyan
        docker-compose exec app /bin/bash
    }
    "shell-db" {
        Write-Host "🐚 Shell PostgreSQL (psql)..." -ForegroundColor Cyan
        docker-compose exec postgres psql -U dispatch_user -d dispatch
    }
    "backup" {
        Write-Host "💾 Sauvegarde de la base de données..." -ForegroundColor Green
        if (!(Test-Path backups)) {
            New-Item -ItemType Directory -Path backups | Out-Null
        }
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        docker exec dispatch_postgres pg_dump -U dispatch_user dispatch > "backups/backup_$timestamp.sql"
        Write-Host "✅ Backup créé dans backups/backup_$timestamp.sql" -ForegroundColor Green
    }
    "restore" {
        if ($File -eq "") {
            Write-Host "❌ Erreur : Spécifiez le fichier" -ForegroundColor Red
            Write-Host "Usage: .\dispatch.ps1 restore backup.sql" -ForegroundColor Yellow
            exit 1
        }
        Write-Host "⚠️  Restauration de $File..." -ForegroundColor Yellow
        Get-Content $File | docker exec -i dispatch_postgres psql -U dispatch_user dispatch
        Write-Host "✅ Restauration terminée" -ForegroundColor Green
    }
    "clean" {
        Write-Host "🧹 Nettoyage Docker..." -ForegroundColor Yellow
        docker-compose down -v
        docker system prune -f
        Write-Host "✅ Nettoyage terminé" -ForegroundColor Green
    }
    "rebuild" {
        Write-Host "🔄 Reconstruction complète..." -ForegroundColor Yellow
        docker-compose down
        docker-compose build
        docker-compose up -d
        Write-Host "✅ Reconstruction terminée" -ForegroundColor Green
    }
    "status" {
        Write-Host ""
        Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
        Write-Host "║     État de Dispatch Manager           ║" -ForegroundColor Cyan
        Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Conteneurs :" -ForegroundColor Green
        docker-compose ps
        Write-Host ""
        Write-Host "Volumes :" -ForegroundColor Green
        docker volume ls | Select-String "dispatch"
        Write-Host ""
        Write-Host "Réseau :" -ForegroundColor Green
        docker network ls | Select-String "dispatch"
    }
    "debug-login" {
        Write-Host "🔍 Diagnostic des comptes..." -ForegroundColor Cyan
        docker-compose exec app python debug_login.py
    }
    "reset-admin" {
        Write-Host "🔑 Réinitialisation du mot de passe admin..." -ForegroundColor Yellow
        docker-compose exec app python reset_admin_password.py
        Write-Host ""
        Write-Host "✅ Vous pouvez maintenant vous connecter avec :" -ForegroundColor Green
        Write-Host "   Username: admin" -ForegroundColor Cyan
        Write-Host "   Password: admin" -ForegroundColor Cyan
    }
    default {
        Write-Host "❌ Commande inconnue : $Command" -ForegroundColor Red
        Write-Host ""
        Show-Help
        exit 1
    }
}
