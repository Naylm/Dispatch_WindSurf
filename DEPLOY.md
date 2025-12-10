# Guide de Déploiement - Dispatch Manager

Guide complet pour déployer Dispatch Manager sur un serveur Ubuntu en production avec mises à jour à chaud.

## 📋 Table des matières

- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Premier déploiement](#premier-déploiement)
- [Mises à jour](#mises-à-jour)
- [Gestion des secrets](#gestion-des-secrets)
- [Commandes utiles](#commandes-utiles)
- [Dépannage](#dépannage)
- [Rollback](#rollback)

---

## 🏗 Architecture

```
┌──────────────┐         ┌──────────┐         ┌────────────────┐
│              │  Push   │          │  Pull   │                │
│  PC Local    ├────────>│  GitHub  │<────────│ Serveur Ubuntu │
│  (Windows)   │         │          │         │    (Docker)    │
│              │         │          │         │                │
└──────────────┘         └──────────┘         └────────────────┘
       │                                               │
       │ .\deploy.ps1                                  │
       └───────────────────────────────────────────────┘
                        SSH
```

**Services déployés** :
- **PostgreSQL 15** : Base de données (port interne 5432)
- **Flask + Gunicorn** : Application web (port interne 5000)
- **Nginx** : Reverse proxy + HTTPS (ports 80/443)

---

## ✅ Prérequis

### Sur votre PC Windows

- [x] Git installé et configuré
- [x] PowerShell 5.1+ (inclus dans Windows 10/11)
- [x] Clé SSH configurée pour le serveur
- [x] Accès au repository GitHub

### Sur le serveur Ubuntu

- [x] Ubuntu 24.04 LTS
- [x] Docker et Docker Compose installés
- [x] Accès SSH avec clé publique
- [x] Nom de domaine configuré (ex: agartha.cc)
- [x] Certificats SSL présents
- [x] Ports 80 et 443 ouverts

**Vérifier Docker sur le serveur** :
```bash
ssh user@agartha.cc
docker --version
docker compose version
```

---

## 🚀 Premier déploiement

### Étape 1 : Préparer le serveur

Connectez-vous au serveur et créez la structure :

```bash
ssh user@agartha.cc

# Créer le dossier de déploiement
sudo mkdir -p /opt/dispatch
sudo chown $USER:$USER /opt/dispatch
```

### Étape 2 : Configurer les secrets

Créez le fichier `.env` avec les secrets de production :

```bash
cd /opt/dispatch

# Créer le fichier .env
nano .env
```

Copiez le contenu de [`.env.production.template`](.env.production.template) et remplacez les valeurs :

```bash
# Générer un SECRET_KEY fort (64 caractères)
python3 -c "import secrets; print(secrets.token_hex(32))"

# Générer un mot de passe PostgreSQL fort
python3 -c "import secrets; print(secrets.token_urlsafe(24))"
```

**Exemple de `.env` configuré** :
```env
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=a1b2c3d4e5f6... # 64 caractères générés

POSTGRES_HOST=postgres
POSTGRES_DB=dispatch
POSTGRES_USER=dispatch_user
POSTGRES_PASSWORD=XyZ9... # Mot de passe généré

SESSION_COOKIE_SECURE=true
SESSION_LIFETIME_MINUTES=480
```

**Sécuriser le fichier** :
```bash
chmod 600 .env
```

### Étape 3 : Vérifier les certificats SSL

Vérifiez que vos certificats SSL sont présents :

```bash
ls -l /etc/ssl/certs/agartha.cc.crt
ls -l /etc/ssl/private/agartha.cc.key
```

Si vos certificats sont ailleurs, adaptez les chemins dans `nginx.conf` (lignes 57-58).

### Étape 4 : Déployer depuis Windows

Ouvrez PowerShell sur votre PC et lancez :

```powershell
cd C:\Users\nayso\Desktop\DispatchDockerWorking

# Premier déploiement
.\deploy.ps1 -Server "user@agartha.cc" -FirstDeploy
```

Le script va :
- Cloner le repository depuis GitHub
- Créer la structure de dossiers
- Afficher les prochaines étapes

### Étape 5 : Démarrer les services

Retournez sur le serveur et démarrez l'application :

```bash
ssh user@agartha.cc
cd /opt/dispatch

# Démarrer tous les services
docker compose up -d

# Vérifier que tout démarre correctement
docker compose ps
docker compose logs -f app
```

Attendez environ 30 secondes que tous les services démarrent.

### Étape 6 : Vérifier l'application

Dans votre navigateur, accédez à :
- **HTTPS** : https://agartha.cc
- **Health check** : https://agartha.cc/health

**Connexion par défaut** :
- Username : `admin`
- Password : `admin`

⚠️ **IMPORTANT** : Changez le mot de passe admin immédiatement !

---

## 🔄 Mises à jour (routine)

Une fois le premier déploiement effectué, les mises à jour sont très simples.

### Workflow de mise à jour

1. **Sur Windows** : Développer et tester en local
2. **Commit et push** sur GitHub
3. **Déployer** avec le script

### Exemple complet

```powershell
# 1. Faire vos modifications en local
# ... éditer les fichiers ...

# 2. Tester localement
docker compose up

# 3. Commit et push
git add .
git commit -m "feat: Nouvelle fonctionnalité X"
git push

# 4. Déployer en production
.\deploy.ps1 -Server "user@agartha.cc"
```

**C'est tout !** Le script s'occupe de :
- ✅ Backup automatique de la base de données
- ✅ Pull des derniers changements
- ✅ Rebuild du conteneur
- ✅ Redémarrage avec ~30-60 secondes d'interruption
- ✅ Vérification de santé

### Options du script

```powershell
# Déploiement normal
.\deploy.ps1 -Server "user@agartha.cc"

# Sauter le backup (NON RECOMMANDÉ)
.\deploy.ps1 -Server "user@agartha.cc" -SkipBackup

# Premier déploiement
.\deploy.ps1 -Server "user@agartha.cc" -FirstDeploy
```

---

## 🔐 Gestion des secrets

### Qu'est-ce qu'un secret ?

Les **secrets** sont des informations sensibles :
- `SECRET_KEY` : Clé de chiffrement des sessions
- `POSTGRES_PASSWORD` : Mot de passe de la base de données
- Certificats SSL
- API keys tierces

### Où sont les secrets ?

| Environnement | Fichier | Contenu |
|---------------|---------|---------|
| **Local (dev)** | `.env` | Valeurs de test (`SECRET_KEY=dev`) |
| **GitHub** | ❌ Aucun | Code source uniquement |
| **Production** | `/opt/dispatch/.env` | Secrets forts générés |

### Pourquoi séparer ?

- ✅ Si quelqu'un accède à GitHub → pas de mots de passe de prod
- ✅ Chaque environnement a ses propres secrets
- ✅ Si un secret fuite → changer uniquement celui de prod

### Comment ça fonctionne ?

Docker Compose lit automatiquement le fichier `.env` et injecte les variables dans les conteneurs. Transparent pour vous !

---

## 🛠 Commandes utiles

### Sur le serveur

```bash
# Se connecter
ssh user@agartha.cc
cd /opt/dispatch

# Voir les logs en temps réel
docker compose logs -f app
docker compose logs -f nginx
docker compose logs -f postgres

# Voir le status des conteneurs
docker compose ps

# Redémarrer un service
docker compose restart app
docker compose restart nginx

# Arrêter tous les services
docker compose down

# Démarrer tous les services
docker compose up -d

# Rebuild et redémarrer
docker compose down && docker compose up -d --build

# Voir les ressources utilisées
docker stats
```

### Backup manuel de la base de données

```bash
# Sur le serveur
cd /opt/dispatch

# Créer un backup
docker compose exec postgres pg_dump -U dispatch_user dispatch > backups/backup_$(date +%Y%m%d_%H%M%S).sql

# Lister les backups
ls -lh backups/
```

### Restaurer une base de données

```bash
# Sur le serveur
cd /opt/dispatch

# Restaurer depuis un backup
docker compose exec -T postgres psql -U dispatch_user dispatch < backups/backup_20250110_143000.sql
```

---

## 🩺 Dépannage

### L'application ne démarre pas

```bash
# Vérifier les logs
docker compose logs app

# Vérifier les variables d'environnement
docker compose exec app env | grep FLASK

# Vérifier que le fichier .env existe
ls -la /opt/dispatch/.env

# Redémarrer proprement
docker compose down
docker compose up -d
```

### Erreur de connexion PostgreSQL

```bash
# Vérifier que PostgreSQL est démarré
docker compose ps postgres

# Vérifier les logs PostgreSQL
docker compose logs postgres

# Se connecter manuellement
docker compose exec postgres psql -U dispatch_user dispatch
```

### Nginx ne démarre pas (certificats SSL)

```bash
# Vérifier les certificats
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
# Modifier: GUNICORN_WORKERS=8
docker compose restart app

# Vérifier le pool de connexions
# Dans .env: DB_POOL_MAX=30
```

---

## ⏮ Rollback (revenir en arrière)

Si un déploiement pose problème, vous pouvez revenir à la version précédente.

### Méthode 1 : Rollback rapide

```bash
ssh user@agartha.cc
cd /opt/dispatch

# Voir les derniers commits
git log --oneline -10

# Revenir au commit précédent
git reset --hard HEAD~1  # ou git reset --hard <COMMIT_ID>

# Rebuild et redémarrer
docker compose down
docker compose up -d --build
```

### Méthode 2 : Restaurer la base de données

Si la base de données a aussi besoin d'être restaurée :

```bash
# 1. Arrêter l'application
docker compose down

# 2. Restaurer le backup
docker compose up -d postgres  # Démarrer seulement PostgreSQL
sleep 5  # Attendre le démarrage

docker compose exec -T postgres psql -U dispatch_user dispatch < backups/backup_DERNIERE_VERSION_OK.sql

# 3. Revenir au bon commit
git reset --hard <COMMIT_OK>

# 4. Redémarrer tout
docker compose down
docker compose up -d --build
```

---

## 📊 Monitoring (optionnel)

### Backups automatiques quotidiens

Ajouter un cron job sur le serveur :

```bash
ssh user@agartha.cc
crontab -e

# Ajouter cette ligne (backup quotidien à 3h du matin)
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

## 📝 Checklist de déploiement

Avant votre premier déploiement, vérifiez :

- [ ] SSH fonctionne : `ssh user@agartha.cc`
- [ ] Docker installé : `docker --version`
- [ ] Docker Compose installé : `docker compose version`
- [ ] Certificats SSL présents et chemins corrects dans `nginx.conf`
- [ ] Fichier `.env` créé sur le serveur avec secrets forts
- [ ] Permissions sur `.env` : `chmod 600 .env`
- [ ] Nom de domaine pointe vers l'IP du serveur
- [ ] Ports 80 et 443 ouverts dans le firewall
- [ ] Script `deploy.ps1` adapté avec le bon serveur

---

## 🎯 Résumé rapide

### Premier déploiement
```powershell
.\deploy.ps1 -Server "user@agartha.cc" -FirstDeploy
```

### Mises à jour quotidiennes
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

## 📞 Support

En cas de problème :
1. Consultez les logs : `docker compose logs app`
2. Vérifiez le status : `docker compose ps`
3. Testez le health check : `curl https://agartha.cc/health`

---

**Temps d'interruption estimé lors des mises à jour** : ~30-60 secondes

**Fréquence des backups automatiques** : Quotidiens à 3h du matin

**Durée de conservation des backups** : 30 jours
