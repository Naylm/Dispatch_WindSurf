# 🚢 DispatchDocker

> Plateforme de gestion d'incidents, de techniciens et de base de connaissances prête à être déployée en production via Docker & Nginx.

[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org)
[![Flask](https://img.shields.io/badge/Flask-2.x-green.svg)](https://flask.palletsprojects.com)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-realtime-purple.svg)](https://socket.io)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Sommaire

1. [Introduction](#introduction)
2. [Architecture Docker](#architecture-docker)
3. [Prérequis](#prérequis)
4. [Installation & Démarrage](#installation--démarrage)
5. [Volumes & Persistance](#volumes--persistance)
6. [Variables d'environnement](#variables-denvironnement)
7. [Fonctionnalités clés](#fonctionnalités-clés)
8. [Maintenance et mises à jour](#maintenance-et-mises-à-jour)
9. [Dépannage](#dépannage)
10. [Ressources complémentaires](#ressources-complémentaires)

---

## Introduction

DispatchDocker est la version containerisée du Dispatch Manager :

- **Backend** : Flask + Socket.IO (temps réel) + **PostgreSQL**
- **Frontend** : UI moderne responsive avec mode sombre, sidebar permanente et dashboard en colonnes
- **Wiki** : système collaboratif (catégories/sous-catégories illimitées, historique, likes/dislikes)
- **Temps réel** : notifications Socket.IO pour la vie des tickets (assignation, suppression, stats…)

Le but est d'avoir un **stack Docker reproductible** : une commande `docker compose up` suffit pour déployer l'application derrière un Nginx reverse proxy.

> **🆕 Nouveauté** : Migration de SQLite vers PostgreSQL pour une meilleure scalabilité et concurrence. Voir [MIGRATION_POSTGRES.md](MIGRATION_POSTGRES.md) pour les détails.

---

## Architecture Docker

```text
dispatch-docker/
├── Dockerfile            # Image Flask/Gunicorn/Eventlet
├── docker-compose.yml    # Orchestration multi-conteneurs (3 services)
├── nginx.conf            # Reverse proxy & assets
├── db_config.py          # Configuration PostgreSQL
├── app.py …              # Code Flask
└── static/, templates/   # UI, CSS, JS
```

`docker-compose.yml` lance **trois services** :

| Service | Rôle | Ports | Volumes |
|---------|------|-------|---------|
| `postgres` | Base de données PostgreSQL 15 | interne 5432 | `postgres_data:/var/lib/postgresql/data` |
| `app`   | Flask + Gunicorn + Eventlet | interne 5000 | `dispatch_uploads:/app/static/uploads` |
| `nginx` | Reverse proxy + static uploads | 80 (host) | `./nginx.conf:/etc/nginx/nginx.conf:ro` + `dispatch_uploads:/var/www/uploads` |

Le trafic passe uniquement par Nginx (port 80). Les conteneurs Flask et PostgreSQL restent isolés.

---

## Prérequis

- Docker Engine **24+** & Docker Compose Plugin **2.20+**
- Git
- (Optionnel) `dispatch.db` existant pour retrouver vos données historiques

Vérifier les versions :

```bash
docker --version
docker compose version
```

---

## Installation & Démarrage

```bash
git clone https://github.com/Naylm/DispatchDocker.git
cd DispatchDocker

# 1) Arrêter toute ancienne stack
docker compose down --remove-orphans

# 2) Lancer (build + run)
docker compose up --build

# Option : mode détaché
docker compose up -d --build
```

> L’application est disponible sur [http://localhost](http://localhost)

### Arrêter les conteneurs

```bash
docker compose down
```

---

## Volumes & Persistance

| Élément | Chemin hôte | Chemin conteneur | Description |
|---------|-------------|------------------|-------------|
| Base SQLite | `./dispatch.db` | `/app/data/dispatch.db` | Base existante réutilisée telle quelle |
| Uploads (images wiki, pièces jointes) | `dispatch_uploads` (volume Docker) | `/app/static/uploads` & `/var/www/uploads` | Partagé entre Flask et Nginx |

💡 **Important** : le fichier `dispatch.db` doit se trouver à la racine du projet. Au premier démarrage, `ensure_db_integrity.py` crée les tables manquantes, les colonnes (ex : `statuts.category`) et un compte `admin/admin` si besoin.

---

## Variables d'environnement

Le `docker-compose.yml` définit les variables essentielles :

```yaml
environment:
  - FLASK_ENV=production
  - SECRET_KEY=${SECRET_KEY:-change_me_in_production_please}
  - GUNICORN_WORKERS=1
```

Pour surcharger, créez un fichier `.env` (non versionné) au même niveau que `docker-compose.yml` :

```env
SECRET_KEY=une_vraie_clé_random
GUNICORN_WORKERS=2
```

**Astuce** : utilisez `python - <<<'import secrets;print(secrets.token_hex(32))'` pour générer une clé secrète.

---

## Fonctionnalités clés

### Incidents & Techniciens

- Dashboard admin en colonnes (auto-fit responsive)
- Assignation, changement de statut, copie rapide du numéro
- Statistiques en temps réel (En cours / Suspendus / Transférés / Traités)
- Activation/désactivation des techniciens sans perdre leurs tickets

### Wiki collaboratif V2

- Catégories & sous-catégories imbriquées
- Articles Markdown + preview + drag & drop d’images
- Historique complet, likes/dislikes, tags
- Droits ouverts : admins ET techniciens peuvent tout gérer

### UI & UX

- Mode sombre cohérent (notes, badges, inputs)
- Sidebar permanente (admin / technicien) + raccourcis externes
- Composants réactifs (animations, hover states)
- Formulaires modernisés (sélecteurs, modales, etc.)

### Sécurité & robustesse

- SQLite optimisé (WAL, PRAGMA, timeouts, transactions `BEGIN IMMEDIATE`)
- Socket.IO configuré pour 10 utilisateurs concurrents (Eventlet, ping tuning)
- Nginx reverse proxy + healthchecks Docker pour s’assurer du bon démarrage

---

## Maintenance et mises à jour

### Mettre à jour l’image

```bash
git pull origin main
docker compose down
docker compose up --build
```

### Sauvegarder la base PostgreSQL

```bash
# Backup complet
docker compose exec postgres pg_dump -U dispatch_user dispatch > backup_$(date +%Y%m%d).sql

# Restaurer un backup
docker compose exec -T postgres psql -U dispatch_user dispatch < backup_20251119.sql
```

### Nettoyer les volumes (uploads)

```bash
docker volume ls
docker volume rm dispatchdockerdocker_dispatch_uploads   # si besoin
```

---

## Dépannage

### Problèmes fréquents

- **`no configuration file provided: not found`** — lancer `docker compose` depuis le dossier contenant `docker-compose.yml`.
- **`psycopg2.OperationalError: could not connect`** — attendre que PostgreSQL soit prêt (10-15s au premier démarrage) : `docker compose logs postgres`.
- **CSS qui saute / sidebar blanche** — vérifier `nginx.conf` : seule la route `/static/uploads/` doit pointer vers `/var/www/uploads/`.
- **500 au login** — utiliser le compte initial `admin` / `admin` ou vérifier les logs : `docker compose logs app`.
- **Port 80 occupé** — `netstat -ano | findstr :80` puis `taskkill /PID &lt;id&gt; /F` (Windows) ou `sudo lsof -i :80` (Linux/macOS).

### Logs utiles

```bash
docker compose logs -f postgres  # Logs PostgreSQL
docker compose logs -f app        # Logs Flask
docker compose logs -f nginx      # Logs Nginx
```

---

## Ressources complémentaires

- **`MIGRATION_POSTGRES.md`** : guide complet de migration SQLite → PostgreSQL
- `DEPLOY_GUIDE.md` : étapes de déploiement détaillées (reverse proxy externe, SSL, etc.)
- `DOCKER_README.md` : notes supplémentaires sur les images & optimisations
- `docs/` & `wiki-home.md` : documentation fonctionnelle & procédures internes
- `DispatchManagerV1.3.wiki/` : dépôt wiki Git (submodule) contenant les pages officielles

---

## Auteur & Licence

- **Auteur** : [Naylm](https://github.com/Naylm)
- **Licence** : MIT — libre utilisation/modification tant que la licence est incluse

> Besoin d’aide ou envie de contribuer ? Ouvrez une issue sur GitHub ou contactez directement Naylm.

---

Merci d’utiliser **DispatchDocker**. Bon déploiement ! 🚀
