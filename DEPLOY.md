# Guide de DÃ©ploiement - Dispatch Manager

Guide complet pour dÃ©ployer Dispatch Manager sur un serveur Ubuntu en production avec mises Ã  jour Ã  chaud.

## ðŸ“‹ Table des matiÃ¨res

- [Architecture](#architecture)
- [PrÃ©requis](#prÃ©requis)
- [Premier dÃ©ploiement](#premier-dÃ©ploiement)
- [Mises Ã  jour](#mises-Ã -jour)
- [Gestion des secrets](#gestion-des-secrets)
- [Commandes utiles](#commandes-utiles)
- [DÃ©pannage](#dÃ©pannage)
- [Rollback](#rollback)

---

## ðŸ— Architecture

```
â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”         â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
â”‚              â”‚  Push   â”‚          â”‚  Pull   â”‚                â”‚
â”‚  PC Local    â”œâ”€â”€â”€â”€â”€â”€â”€â”€>â”‚  GitHub  â”‚<â”€â”€â”€â”€â”€â”€â”€â”€â”‚ Serveur Ubuntu â”‚
â”‚  (Windows)   â”‚         â”‚          â”‚         â”‚    (Docker)    â”‚
â”‚              â”‚         â”‚          â”‚         â”‚                â”‚
â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜         â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
       â”‚                                               â”‚
       â”‚ .\deploy.ps1                                  â”‚
       â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
                        SSH
```

**Services dÃ©ployÃ©s** :
- **PostgreSQL 15** : Base de donnÃ©es (port interne 5432)
- **Flask + Gunicorn** : Application web (port interne 5000)
- **Nginx** : Reverse proxy + HTTPS (ports 80/443)

---

## âœ… PrÃ©requis

### Sur votre PC Windows

- [x] Git installÃ© et configurÃ©
- [x] PowerShell 5.1+ (inclus dans Windows 10/11)
- [x] ClÃ© SSH configurÃ©e pour le serveur
- [x] AccÃ¨s au repository GitHub

### Sur le serveur Ubuntu

- [x] Ubuntu 24.04 LTS
- [x] Docker et Docker Compose installÃ©s
- [x] AccÃ¨s SSH avec clÃ© publique
- [x] Nom de domaine configurÃ© (ex: agartha.cc)
- [x] Certificats SSL prÃ©sents
- [x] Ports 80 et 443 ouverts

**VÃ©rifier Docker sur le serveur** :
```bash
ssh user@agartha.cc
docker --version
docker compose version
```

---

## ðŸš€ Premier dÃ©ploiement

### Ã‰tape 1 : PrÃ©parer le serveur

Connectez-vous au serveur et crÃ©ez la structure :

```bash
ssh user@agartha.cc

# CrÃ©er le dossier de dÃ©ploiement
sudo mkdir -p /opt/dispatch
sudo chown $USER:$USER /opt/dispatch
```

### Ã‰tape 2 : Configurer les secrets

CrÃ©ez le fichier `.env` avec les secrets de production :

```bash
cd /opt/dispatch

# CrÃ©er le fichier .env
nano .env
```

Copiez le contenu de [`.env.production.template`](.env.production.template) et remplacez les valeurs :

```bash
# GÃ©nÃ©rer un SECRET_KEY fort (64 caractÃ¨res)
python3 -c "import secrets; print(secrets.token_hex(32))"

# GÃ©nÃ©rer un mot de passe PostgreSQL fort
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

**Exemple de `.env` configurÃ©** :
```env
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=a1b2c3d4e5f6... # 64 caractÃ¨res gÃ©nÃ©rÃ©s

POSTGRES_HOST=postgres
POSTGRES_DB=dispatch
POSTGRES_USER=dispatch_user
POSTGRES_PASSWORD=XyZ9... # Mot de passe gÃ©nÃ©rÃ©

SESSION_COOKIE_SECURE=true
SESSION_LIFETIME_MINUTES=480
```

**SÃ©curiser le fichier** :
```bash
chmod 600 .env
```

### Ã‰tape 3 : VÃ©rifier les certificats SSL

VÃ©rifiez que vos certificats SSL sont prÃ©sents :

```bash
ls -l /etc/ssl/certs/agartha.cc.crt
ls -l /etc/ssl/private/agartha.cc.key
```

Si vos certificats sont ailleurs, adaptez les chemins dans `nginx.conf` (lignes 57-58).

### Ã‰tape 4 : DÃ©ployer depuis Windows

Ouvrez PowerShell sur votre PC et lancez :

```powershell
cd C:\Users\nayso\Desktop\DispatchDockerWorking

# Premier dÃ©ploiement
.\deploy.ps1 -Server "user@agartha.cc" -FirstDeploy
```

Le script va :
- Cloner le repository depuis GitHub
- CrÃ©er la structure de dossiers
- Afficher les prochaines Ã©tapes

### Ã‰tape 5 : DÃ©marrer les services

Retournez sur le serveur et dÃ©marrez l'application :

```bash
ssh user@agartha.cc
cd /opt/dispatch

# DÃ©marrer tous les services
docker compose up -d

# VÃ©rifier que tout dÃ©marre correctement
docker compose ps
docker compose logs -f app
```

Attendez environ 30 secondes que tous les services dÃ©marrent.

### Ã‰tape 6 : VÃ©rifier l'application

Dans votre navigateur, accÃ©dez Ã  :
- **HTTPS** : https://agartha.cc
- **Health check** : https://agartha.cc/health

**Connexion initiale** :
- Compte cree via `BOOTSTRAP_ADMIN_USERNAME` / `BOOTSTRAP_ADMIN_PASSWORD` dans `.env`
- Le compte est force de changer son mot de passe a la premiere connexion

---

## ðŸ”„ Mises Ã  jour (routine)

Une fois le premier dÃ©ploiement effectuÃ©, les mises Ã  jour sont trÃ¨s simples.

### Workflow de mise Ã  jour

1. **Sur Windows** : DÃ©velopper et tester en local
2. **Commit et push** sur GitHub
3. **DÃ©ployer** avec le script

### Exemple complet

```powershell
# 1. Faire vos modifications en local
# ... Ã©diter les fichiers ...

# 2. Tester localement
docker compose up

# 3. Commit et push
git add .
git commit -m "feat: Nouvelle fonctionnalitÃ© X"
git push

# 4. DÃ©ployer en production
.\deploy.ps1 -Server "user@agartha.cc"
```

**C'est tout !** Le script s'occupe de :
- âœ… Backup automatique de la base de donnÃ©es
- âœ… Pull des derniers changements
- âœ… Rebuild du conteneur
- âœ… RedÃ©marrage avec ~30-60 secondes d'interruption
- âœ… VÃ©rification de santÃ©

### Options du script

```powershell
# DÃ©ploiement normal
.\deploy.ps1 -Server "user@agartha.cc"

# Sauter le backup (NON RECOMMANDÃ‰)
.\deploy.ps1 -Server "user@agartha.cc" -SkipBackup

# Premier dÃ©ploiement
.\deploy.ps1 -Server "user@agartha.cc" -FirstDeploy
```

---

## ðŸ” Gestion des secrets

### Qu'est-ce qu'un secret ?

Les **secrets** sont des informations sensibles :
- `SECRET_KEY` : ClÃ© de chiffrement des sessions
- `POSTGRES_PASSWORD` : Mot de passe de la base de donnÃ©es
- Certificats SSL
- API keys tierces

### OÃ¹ sont les secrets ?

| Environnement | Fichier | Contenu |
|---------------|---------|---------|
| **Local (dev)** | `.env` | Valeurs de test (`SECRET_KEY=dev`) |
| **GitHub** | âŒ Aucun | Code source uniquement |
| **Production** | `/opt/dispatch/.env` | Secrets forts gÃ©nÃ©rÃ©s |

### Pourquoi sÃ©parer ?

- âœ… Si quelqu'un accÃ¨de Ã  GitHub â†’ pas de mots de passe de prod
- âœ… Chaque environnement a ses propres secrets
- âœ… Si un secret fuite â†’ changer uniquement celui de prod

### Comment Ã§a fonctionne ?

Docker Compose lit automatiquement le fichier `.env` et injecte les variables dans les conteneurs. Transparent pour vous !

---

## ðŸ›  Commandes utiles

### Sur le serveur

```bash
# Se connecter
ssh user@agartha.cc
cd /opt/dispatch

# Voir les logs en temps rÃ©el
docker compose logs -f app
docker compose logs -f nginx
docker compose logs -f postgres

# Voir le status des conteneurs
docker compose ps

# RedÃ©marrer un service
docker compose restart app
docker compose restart nginx

# ArrÃªter tous les services
docker compose down

# DÃ©marrer tous les services
docker compose up -d

# Rebuild et redÃ©marrer
docker compose down && docker compose up -d --build

# Voir les ressources utilisÃ©es
docker stats
```

### Backup manuel de la base de donnÃ©es

```bash
# Sur le serveur
cd /opt/dispatch

# CrÃ©er un backup
docker compose exec postgres pg_dump -U dispatch_user dispatch > backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Lister les backups
ls -lh backups/
```

### Restaurer une base de donnÃ©es

```bash
# Sur le serveur
cd /opt/dispatch

# Restaurer depuis un backup
docker compose exec -T postgres psql -U dispatch_user dispatch < backups/backup_20250110_143000.sql
```

---

## ðŸ©º DÃ©pannage

### L'application ne dÃ©marre pas

```bash
# VÃ©rifier les logs
docker compose logs app

# VÃ©rifier les variables d'environnement
docker compose exec app env | grep FLASK

# VÃ©rifier que le fichier .env existe
ls -la /opt/dispatch/.env

# RedÃ©marrer proprement
docker compose down
docker compose up -d
```

### Erreur de connexion PostgreSQL

```bash
# VÃ©rifier que PostgreSQL est dÃ©marrÃ©
docker compose ps postgres

# VÃ©rifier les logs PostgreSQL
docker compose logs postgres

# Se connecter manuellement
docker compose exec postgres psql -U dispatch_user dispatch
```

### Nginx ne dÃ©marre pas (certificats SSL)

```bash
# VÃ©rifier les certificats
docker compose exec nginx ls -l /etc/ssl/certs/
docker compose exec nginx ls -l /etc/ssl/private/

# Tester la config Nginx
docker compose exec nginx nginx -t

# Voir les logs Nginx
docker compose logs nginx
```

### L'application est lente

```bash
# Voir la consommation de ressources
docker stats

# Augmenter le nombre de workers Gunicorn
nano .env
# Modifier: GUNICORN_WORKERS=2 (et garder REDIS_URL actif)
docker compose restart app

# VÃ©rifier le pool de connexions
# Dans .env: DB_POOL_MAX=30
```

---

## â® Rollback (revenir en arriÃ¨re)

Si un dÃ©ploiement pose problÃ¨me, vous pouvez revenir Ã  la version prÃ©cÃ©dente.

### MÃ©thode 1 : Rollback rapide

```bash
ssh user@agartha.cc
cd /opt/dispatch

# Voir les derniers commits
git log --oneline -10

# Revenir au commit prÃ©cÃ©dent
git reset --hard HEAD~1  # ou git reset --hard <COMMIT_ID>

# Rebuild et redÃ©marrer
docker compose down
docker compose up -d --build
```

### MÃ©thode 2 : Restaurer la base de donnÃ©es

Si la base de donnÃ©es a aussi besoin d'Ãªtre restaurÃ©e :

```bash
# 1. ArrÃªter l'application
docker compose down

# 2. Restaurer le backup
docker compose up -d postgres  # DÃ©marrer seulement PostgreSQL
sleep 5  # Attendre le dÃ©marrage

docker compose exec -T postgres psql -U dispatch_user dispatch < backups/backup_DERNIERE_VERSION_OK.sql

# 3. Revenir au bon commit
git reset --hard <COMMIT_OK>

# 4. RedÃ©marrer tout
docker compose down
docker compose up -d --build
```

---

## ðŸ“Š Monitoring (optionnel)

### Backups automatiques quotidiens

Ajouter un cron job sur le serveur :

```bash
ssh user@agartha.cc
crontab -e

# Ajouter cette ligne (backup quotidien Ã  3h du matin)
0 3 * * * cd /opt/dispatch && docker compose exec -T postgres pg_dump -U dispatch_user dispatch > backups/backup_$(date +\%Y\%m\%d).sql
```

### Rotation des backups (garder 30 jours)

```bash
# Ajouter aussi dans le cron
0 4 * * * find /opt/dispatch/backups/ -name "backup_*.sql" -mtime +30 -delete
```

### Alertes email en cas de crash (optionnel)

Installer et configurer `systemd` pour recevoir des alertes.

---

## ðŸ“ Checklist de dÃ©ploiement

Avant votre premier dÃ©ploiement, vÃ©rifiez :

- [ ] SSH fonctionne : `ssh user@agartha.cc`
- [ ] Docker installÃ© : `docker --version`
- [ ] Docker Compose installÃ© : `docker compose version`
- [ ] Certificats SSL prÃ©sents et chemins corrects dans `nginx.conf`
- [ ] Fichier `.env` crÃ©Ã© sur le serveur avec secrets forts
- [ ] Permissions sur `.env` : `chmod 600 .env`
- [ ] Nom de domaine pointe vers l'IP du serveur
- [ ] Ports 80 et 443 ouverts dans le firewall
- [ ] Script `deploy.ps1` adaptÃ© avec le bon serveur

---

## ðŸŽ¯ RÃ©sumÃ© rapide

### Premier dÃ©ploiement
```powershell
.\deploy.ps1 -Server "user@agartha.cc" -FirstDeploy
```

### Mises Ã  jour quotidiennes
```powershell
git add .
git commit -m "Description"
git push
.\deploy.ps1 -Server "user@agartha.cc"
```

### Voir les logs
```bash
ssh user@agartha.cc
cd /opt/dispatch
docker compose logs -f app
```

---

## ðŸ“ž Support

En cas de problÃ¨me :
1. Consultez les logs : `docker compose logs app`
2. VÃ©rifiez le status : `docker compose ps`
3. Testez le health check : `curl https://agartha.cc/health`

---

**Temps d'interruption estimÃ© lors des mises Ã  jour** : ~30-60 secondes

**FrÃ©quence des backups automatiques** : Quotidiens Ã  3h du matin

**DurÃ©e de conservation des backups** : 30 jours

