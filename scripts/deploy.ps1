# deploy.ps1 - Script de déploiement automatique sur serveur Ubuntu
# Usage: .\deploy.ps1 -Server "user@agartha.cc"
#        .\deploy.ps1 -Server "user@agartha.cc" -FirstDeploy
#        .\deploy.ps1 -Server "user@agartha.cc" -SkipBackup

param(
    [string]$Server = "user@agartha.cc",  # À adapter avec votre serveur
    [string]$Path = "/opt/dispatch",       # Chemin sur le serveur
    [switch]$FirstDeploy,                  # Premier déploiement
    [switch]$SkipBackup                    # Sauter le backup (non recommandé)
)

$ErrorActionPreference = "Stop"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Déploiement Dispatch Manager" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Serveur    : $Server" -ForegroundColor White
Write-Host "Chemin     : $Path" -ForegroundColor White
Write-Host "Mode       : $(if ($FirstDeploy) { 'Premier déploiement' } else { 'Mise à jour' })" -ForegroundColor White
Write-Host ""

# ========================================
# 1. Vérification Git
# ========================================
Write-Host "[1/6] Vérification Git..." -ForegroundColor Yellow

# Vérifier que nous sommes dans un repo git
$gitCheck = git rev-parse --git-dir 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Erreur: Ce dossier n'est pas un repository Git" -ForegroundColor Red
    exit 1
}

# Vérifier les modifications non commitées
$gitStatus = git status --porcelain
if ($gitStatus) {
    Write-Host "⚠ Modifications non commitées détectées:" -ForegroundColor Red
    Write-Host $gitStatus -ForegroundColor Yellow
    $continue = Read-Host "Continuer quand même ? (y/N)"
    if ($continue -ne "y") {
        Write-Host "Déploiement annulé" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✓ Aucune modification en attente" -ForegroundColor Green
}

# ========================================
# 2. Push vers GitHub
# ========================================
Write-Host "`n[2/6] Push vers GitHub..." -ForegroundColor Yellow

try {
    git push origin master 2>&1 | Out-String | Write-Host
    if ($LASTEXITCODE -ne 0) {
        throw "Erreur lors du push"
    }
    Write-Host "✓ Code poussé sur GitHub" -ForegroundColor Green
} catch {
    Write-Host "✗ Erreur lors du push Git: $_" -ForegroundColor Red
    Write-Host "Astuce: Vérifiez votre connexion réseau et vos credentials Git" -ForegroundColor Yellow
    exit 1
}

# ========================================
# 3. Test de connexion SSH
# ========================================
Write-Host "`n[3/6] Test de connexion SSH..." -ForegroundColor Yellow

$sshTest = ssh -o ConnectTimeout=5 -o BatchMode=yes $Server "echo 'OK'" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Impossible de se connecter au serveur $Server" -ForegroundColor Red
    Write-Host "Erreur: $sshTest" -ForegroundColor Yellow
    Write-Host "`nAstuces de dépannage:" -ForegroundColor Cyan
    Write-Host "  - Vérifiez que votre clé SSH est configurée: ssh-add -l" -ForegroundColor White
    Write-Host "  - Testez la connexion manuellement: ssh $Server" -ForegroundColor White
    Write-Host "  - Vérifiez que le serveur est accessible: ping $(($Server -split '@')[1])" -ForegroundColor White
    exit 1
}
Write-Host "✓ Connexion SSH établie" -ForegroundColor Green

# ========================================
# 4. Déploiement sur le serveur
# ========================================
Write-Host "`n[4/6] Déploiement sur le serveur..." -ForegroundColor Yellow

if ($FirstDeploy) {
    # ====================================
    # Premier déploiement
    # ====================================
    Write-Host "Mode: Premier déploiement" -ForegroundColor Cyan

    $deployScript = @"
set -e
echo ""
echo "=== PREMIER DÉPLOIEMENT ==="
echo ""

# Créer le dossier avec les bonnes permissions
echo "→ Création de la structure..."
sudo mkdir -p $Path
sudo chown \$USER:\$USER $Path

# Clone du repository
echo "→ Clone du repository GitHub..."
cd $Path
git clone https://github.com/Naylm/DispatchDockerWorking.git .

# Créer le dossier pour les backups
mkdir -p backups

echo ""
echo "✓ Repository cloné avec succès"
echo ""
echo "⚠ IMPORTANT: Vous devez maintenant:"
echo "  1. Créer le fichier .env avec les secrets de production"
echo "  2. Vérifier les certificats SSL"
echo "  3. Lancer: docker compose up -d"
echo ""
"@

    ssh $Server $deployScript

    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Erreur lors du premier déploiement" -ForegroundColor Red
        exit 1
    }

    Write-Host "`n✓ Premier déploiement terminé" -ForegroundColor Green
    Write-Host "`n⚠ PROCHAINES ÉTAPES SUR LE SERVEUR:" -ForegroundColor Yellow
    Write-Host "   ssh $Server" -ForegroundColor Cyan
    Write-Host "   cd $Path" -ForegroundColor Cyan
    Write-Host "   nano .env    # Créer le fichier avec les secrets" -ForegroundColor Cyan
    Write-Host "   docker compose up -d" -ForegroundColor Cyan
    exit 0

} else {
    # ====================================
    # Mise à jour normale
    # ====================================
    Write-Host "Mode: Mise à jour" -ForegroundColor Cyan

    $backupCmd = if ($SkipBackup) {
        "echo '⚠ Backup skipped (non recommandé)'"
    } else {
        @"
echo '→ Backup de la base de données...'
timestamp=\$(date +%Y%m%d_%H%M%S)
docker compose exec -T postgres pg_dump -U dispatch_user dispatch > backups/backup_\$timestamp.sql
if [ \$? -eq 0 ]; then
    echo "✓ Backup créé: backups/backup_\$timestamp.sql"
else
    echo "✗ Erreur lors du backup"
    exit 1
fi
"@
    }

    $deployScript = @"
set -e
cd $Path

echo ""
echo "=== MISE À JOUR DISPATCH ==="
echo ""

# Backup de la BDD
$backupCmd

# Pull des dernières modifications
echo ""
echo "→ Récupération des dernières modifications..."
git fetch origin
git reset --hard origin/master
git_commit=\$(git rev-parse --short HEAD)
echo "✓ Code mis à jour (commit: \$git_commit)"

# Rebuild du conteneur app
echo ""
echo "→ Rebuild du conteneur..."
docker compose down
docker compose build --no-cache app

# Redémarrage des services
echo ""
echo "→ Démarrage des services..."
docker compose up -d

# Attente du démarrage
echo ""
echo "→ Attente du démarrage des services (10s)..."
sleep 10

# Vérification
echo ""
echo "=== VÉRIFICATION ==="
docker compose ps

echo ""
echo "→ Test du endpoint health..."
curl -f http://localhost/health > /dev/null 2>&1
if [ \$? -eq 0 ]; then
    echo "✓ Application répond correctement"
else
    echo "⚠ L'application ne répond pas au health check"
    echo "   Consultez les logs: docker compose logs app"
fi

echo ""
echo "✓ Déploiement terminé avec succès"
echo ""
"@

    ssh $Server $deployScript

    if ($LASTEXITCODE -ne 0) {
        Write-Host "`n✗ Erreur lors du déploiement" -ForegroundColor Red
        Write-Host "`nPour revenir en arrière:" -ForegroundColor Yellow
        Write-Host "  ssh $Server" -ForegroundColor Cyan
        Write-Host "  cd $Path" -ForegroundColor Cyan
        Write-Host "  git log --oneline -5" -ForegroundColor Cyan
        Write-Host "  git reset --hard <COMMIT_PRÉCÉDENT>" -ForegroundColor Cyan
        Write-Host "  docker compose down && docker compose up -d --build" -ForegroundColor Cyan
        exit 1
    }
}

# ========================================
# 5. Vérification de l'application
# ========================================
Write-Host "`n[5/6] Vérification de l'application..." -ForegroundColor Yellow

Start-Sleep -Seconds 2

# Déterminer l'URL (adapter si nécessaire)
$url = if ($Server -like "*agartha.cc*") {
    "https://agartha.cc/health"
} else {
    $serverIp = ($Server -split '@')[1]
    "http://$serverIp/health"
}

try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 10 -ErrorAction Stop
    if ($response.StatusCode -eq 200) {
        Write-Host "✓ Application accessible sur: $url" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠ L'application ne répond pas encore" -ForegroundColor Yellow
    Write-Host "   URL testée: $url" -ForegroundColor White
    Write-Host "   Cela peut prendre quelques secondes de plus..." -ForegroundColor White
}

# ========================================
# 6. Résumé
# ========================================
Write-Host "`n[6/6] Résumé du déploiement" -ForegroundColor Yellow

$commitInfo = git log -1 --pretty=format:"%h - %s (%an, %ar)"
Write-Host "Commit déployé: $commitInfo" -ForegroundColor White

Write-Host "`n========================================" -ForegroundColor Green
Write-Host " ✓ DÉPLOIEMENT TERMINÉ AVEC SUCCÈS" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Application : $(if ($Server -like '*agartha.cc*') { 'https://agartha.cc' } else { 'http://' + ($Server -split '@')[1] })" -ForegroundColor Cyan
Write-Host "Serveur     : $Server" -ForegroundColor White
Write-Host ""
Write-Host "Commandes utiles:" -ForegroundColor Yellow
Write-Host "  Voir les logs     : ssh $Server 'cd $Path && docker compose logs -f app'" -ForegroundColor White
Write-Host "  Status            : ssh $Server 'cd $Path && docker compose ps'" -ForegroundColor White
Write-Host "  Redémarrer        : ssh $Server 'cd $Path && docker compose restart app'" -ForegroundColor White
Write-Host ""
