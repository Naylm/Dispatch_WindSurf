# Script PowerShell pour créer l'utilisateur Melvin
Write-Host ""
Write-Host "╔════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║   Création utilisateur Melvin          ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

docker exec dispatch_manager python scripts/create_user_melvin.py

Write-Host ""
Write-Host "✅ Commande exécutée !" -ForegroundColor Green
Write-Host ""
Write-Host "Identifiants créés :" -ForegroundColor Yellow
Write-Host "   Username: Melvin" -ForegroundColor Cyan
Write-Host "   Password: Admin" -ForegroundColor Cyan
Write-Host "   Rôle: admin" -ForegroundColor Cyan
Write-Host ""


