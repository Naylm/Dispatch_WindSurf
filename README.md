# 🚢 DispatchDocker

> Plateforme de gestion d'incidents, de techniciens et de base de connaissances prête à être déployée en production via Docker & Nginx.

[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org)
[![Flask](https://img.shields.io/badge/Flask-2.x-green.svg)](https://flask.palletsprojects.com)
[![Socket.IO](https://img.shields.io/badge/Socket.IO-realtime-purple.svg)](https://socket.io)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15-blue.svg)](https://www.postgresql.org)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📋 Sommaire

1. [Introduction](#introduction)
2. [Architecture Docker](#architecture-docker)
3. [Prérequis](#prérequis)
4. [Installation & Démarrage](#installation--démarrage)
5. [Volumes & Persistance](#volumes--persistance)
6. [Variables d'environnement](#variables-denvironnement)
7. [Fonctionnalités clés](#fonctionnalités-clés)
8. [Nouvelles fonctionnalités](#nouvelles-fonctionnalités)
9. [Maintenance et mises à jour](#maintenance-et-mises-à-jour)
10. [Dépannage](#dépannage)
11. [Ressources complémentaires](#ressources-complémentaires)

---

## 🎯 Introduction

DispatchDocker est la version containerisée du Dispatch Manager, une plateforme complète de gestion d'incidents IT avec base de connaissances intégrée :

- **Backend** : Flask + Socket.IO (temps réel) + **PostgreSQL 15**
- **Frontend** : UI moderne responsive avec mode sombre, sidebar permanente et dashboard en colonnes
- **Wiki** : système collaboratif complet (catégories/sous-catégories illimitées, historique, likes/dislikes, upload d'images)
- **Temps réel** : notifications Socket.IO pour la vie des tickets (assignation, suppression, changements de statut, stats…)
- **Sécurité** : Protection CSRF complète, authentification robuste, gestion des sessions

Le but est d'avoir un **stack Docker reproductible** : une commande `docker compose up` suffit pour déployer l'application derrière un Nginx reverse proxy.

> **🆕 Nouveauté majeure** : Migration complète de SQLite vers PostgreSQL pour une meilleure scalabilité, concurrence et performances en production.

---

## 🏗️ Architecture Docker

```text
dispatch-docker/
├── Dockerfile            # Image Flask/Gunicorn/Eventlet
├── docker-compose.yml    # Orchestration multi-conteneurs (3 services)
├── nginx.conf            # Reverse proxy & assets
├── db_config.py          # Configuration PostgreSQL avec wrapper SQLite-compatible
├── app.py                # Application Flask principale
├── wiki_routes_v2.py     # Routes Wiki V2
├── notification_helpers.py # Système de notifications temps réel
├── utils_stability.py    # Utilitaires de stabilité
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

## 📦 Prérequis

- Docker Engine **24+** & Docker Compose Plugin **2.20+**
- Git
- (Optionnel) Base de données existante pour migration

Vérifier les versions :

```bash
docker --version
docker compose version
```

---

## 🚀 Installation & Démarrage

```bash
git clone https://github.com/Naylm/DispatchDockerWorking.git
cd DispatchDockerWorking

# 1) Arrêter toute ancienne stack éventuelle
docker compose down --remove-orphans

# 2) Lancer (build + run)
docker compose up --build

# Option : mode détaché (en arrière-plan)
docker compose up -d --build
```

> Une fois les conteneurs démarrés, l'application est accessible sur [http://localhost](http://localhost)

### Arrêter les conteneurs

```bash
docker compose down
```

### Compte par défaut

- **Username** : `admin`
- **Password** : `admin`

> ⚠️ **Important** : Changez le mot de passe par défaut en production !

---

## 💾 Volumes & Persistance

| Élément | Chemin hôte | Chemin conteneur | Description |
|---------|-------------|------------------|-------------|
| Base PostgreSQL | `postgres_data` (volume Docker) | `/var/lib/postgresql/data` | Données persistantes PostgreSQL |
| Uploads (images wiki, pièces jointes) | `dispatch_uploads` (volume Docker) | `/app/static/uploads` & `/var/www/uploads` | Partagé entre Flask et Nginx |
| Backups & Config | `dispatch_data` (volume Docker) | `/app/data` | Sauvegardes et configuration |

💡 **Important** : Au premier démarrage, `ensure_db_integrity.py` crée automatiquement :
- Toutes les tables nécessaires
- Les colonnes manquantes
- Un compte `admin/admin` si aucun utilisateur n'existe
- Les indexes de performance

### ⚠️ Préservation des Données PostgreSQL

Les données PostgreSQL sont stockées dans un **volume Docker** (`postgres_data`), **PAS dans le dépôt Git**.

**Opérations SÛRES** (ne touchent pas les données) :
- ✅ `git pull`, `git push`, `git clone`
- ✅ `docker compose restart`
- ✅ `docker compose up --build` (rebuild image)
- ✅ `docker compose down` (sans flag `-v`)

**Opérations DANGEREUSES** (effacent les données) :
- ❌ `docker compose down -v` (flag `-v` supprime les volumes)
- ❌ `docker volume rm postgres_data`

**Backup recommandé avant modifications importantes** :
```bash
docker exec dispatch_postgres pg_dump -U dispatch_user dispatch > backup.sql
```

---

## 🔐 Variables d'environnement

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

**Astuce** : utilisez `python -c "import secrets; print(secrets.token_hex(32))"` pour générer une clé secrète.

---

## ⭐ Fonctionnalités clés

### 📋 Gestion des Incidents & Techniciens

- **Dashboard admin** en colonnes (auto-fit responsive)
- **Vue technicien** avec cartes d'incidents
- **Assignation** rapide via menu déroulant
- **Changement de statut** en temps réel (synchronisé via Socket.IO)
- **Statistiques** en temps réel (En cours / Suspendus / Transférés / Traités)
- **Activation/désactivation** des techniciens sans perdre leurs tickets
- **Suppression** d'incidents avec synchronisation temps réel
- **Historique complet** des modifications
- **Export** Excel et PDF

### 📚 Wiki collaboratif V2

- **Catégories & sous-catégories** imbriquées (structure illimitée)
- **Articles Markdown** avec éditeur + preview côte à côte (40/60)
- **Upload d'images** par drag & drop avec validation
- **Historique complet** des modifications avec descriptions
- **Système de votes** (likes/dislikes) avec compteurs en temps réel
- **Tags** pour organisation
- **Recherche** dans les articles
- **Droits ouverts** : admins ET techniciens peuvent tout gérer
- **Dates** en timezone Europe/Paris (format JJ/MM/AAAA HH:MM)
- **Texte sélectionnable** pour copier/coller

### 🎨 Interface utilisateur

- **Mode sombre** cohérent (notes, badges, inputs)
- **Sidebar permanente** (admin / technicien) + raccourcis externes
- **Composants réactifs** (animations, hover states)
- **Formulaires modernisés** (sélecteurs, modales, etc.)
- **Design responsive** mobile/tablet/desktop
  - Vue technicien : 1 colonne (mobile), 2 colonnes (tablette), 3 colonnes (desktop)
  - Sidebar avec backdrop mobile-only
  - Bouton burger optimisé (44x44px sur mobile)
- **Badges de couleur** pour priorités et sites

### 🔔 Temps réel & Notifications

- **Synchronisation automatique** des changements de statut
- **Notifications instantanées** pour assignations, suppressions, mises à jour
- **Socket.IO** configuré pour 10 utilisateurs concurrents
- **Mises à jour en direct** sans rafraîchissement de page
- **Système de notifications** avec badges et alertes

### 🔒 Sécurité & robustesse

- **Protection CSRF** complète sur tous les formulaires
- **Authentification** robuste avec gestion des sessions
- **PostgreSQL** optimisé avec indexes de performance
- **Transactions** atomiques pour éviter les conflits
- **Gestion d'erreurs** complète avec logs détaillés
- **Nginx reverse proxy** + healthchecks Docker
- **Validation** des uploads (type, taille, contenu)

---

## 🆕 Nouvelles fonctionnalités

### ✨ Corrections Wiki (Décembre 2025)

- ✅ **Gestion CSRF** : Tous les formulaires (création, édition, suppression) protégés
- ✅ **Routes de suppression** : Support AJAX + formulaire classique avec gestion d'erreurs
- ✅ **Timezone** : Conversion automatique en Europe/Paris (JJ/MM/AAAA HH:MM)
- ✅ **Sélection de texte** : Texte des articles entièrement sélectionnable
- ✅ **Fonction vote** : Gestion CSRF et vérification Content-Type
- ✅ **Logs détaillés** : Traçabilité complète des opérations

### 🔄 Synchronisation temps réel

- ✅ **Changements de statut** : Synchronisation instantanée admin ↔ technicien
- ✅ **Suppression d'incidents** : Disparition en temps réel sur tous les écrans
- ✅ **Badges de statut** : Mise à jour automatique des couleurs
- ✅ **Compteurs** : Statistiques mises à jour en direct

### 📢 Système de notifications

- ✅ **Notifications d'assignation** : Alertes pour nouveaux tickets
- ✅ **Notifications de statut** : Alertes pour changements importants
- ✅ **Notifications urgentes** : Mise en évidence des tickets critiques
- ✅ **Badges de notification** : Compteur visuel des nouvelles notifications

### 🛡️ Améliorations de stabilité

- ✅ **Gestion des transactions** : Wrapper PostgreSQL avec gestion d'erreurs
- ✅ **Indexes de performance** : Optimisation des requêtes fréquentes
- ✅ **Gestion des conflits** : Détection et résolution automatique
- ✅ **Logs structurés** : Traçabilité complète pour le débogage

---

## 🔧 Maintenance et mises à jour

### Mettre à jour l'image

```bash
git pull origin master
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

### Vérifier l'intégrité de la base

```bash
docker compose exec app python ensure_db_integrity.py
```

---

## 🐛 Dépannage

### Problèmes fréquents

- **`no configuration file provided: not found`** — lancer `docker compose` depuis le dossier contenant `docker-compose.yml`.
- **`psycopg2.OperationalError: could not connect`** — attendre que PostgreSQL soit prêt (10-15s au premier démarrage) : `docker compose logs postgres`.
- **CSS qui saute / sidebar blanche** — vérifier `nginx.conf` : seule la route `/static/uploads/` doit pointer vers `/var/www/uploads/`.
- **500 au login** — utiliser le compte initial `admin` / `admin` ou vérifier les logs : `docker compose logs app`.
- **Port 80 occupé** — `netstat -ano | findstr :80` puis `taskkill /PID <id> /F` (Windows) ou `sudo lsof -i :80` (Linux/macOS).
- **Erreur CSRF 400** — vérifier que tous les formulaires contiennent `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.

### Logs utiles

```bash
docker compose logs -f postgres  # Logs PostgreSQL
docker compose logs -f app        # Logs Flask
docker compose logs -f nginx      # Logs Nginx
```

### Vérifier la santé des conteneurs

```bash
docker compose ps
docker compose top
```

---

## 📚 Ressources complémentaires

### Documentation principale

- **`docs/GUIDE_IMPLEMENTATION.md`** : Guide d'implémentation des nouvelles fonctionnalités
- **`docs/README_NOTIFICATIONS.md`** : Documentation du système de notifications
- **`docs/README_STABILITE.md`** : Améliorations de stabilité et performance
- **`docs/AMELIORATIONS_STABILITE.md`** : Détails des optimisations

### Guides techniques

- **`docs/guides/MIGRATION_POSTGRES.md`** : Guide complet de migration SQLite → PostgreSQL
- **`docs/guides/DB_CONTEXT_MANAGER_GUIDE.md`** : Guide d'utilisation du gestionnaire de contexte DB
- **`docs/deployment/DEPLOY_GUIDE.md`** : Étapes de déploiement détaillées (reverse proxy externe, SSL, etc.)
- **`docs/deployment/DOCKER_README.md`** : Notes supplémentaires sur les images & optimisations

### Documentation fonctionnelle

- **`docs/WIKI_VIDE_INFO.md`** : Configuration du Wiki vide
- **`docs/DEMARRAGE_RAPIDE.md`** : Guide de démarrage rapide
- **`docs/DEMARRAGE_PRODUCTION.md`** : Guide de démarrage en production
- **`PROJECT_STRUCTURE.md`** : Structure détaillée du projet

### Archives

- **`archives/`** : Documentation historique et patches

---

## 👤 Auteur & Licence

- **Auteur** : [Naylm](https://github.com/Naylm)
- **Licence** : MIT — libre utilisation/modification tant que la licence est incluse

> Besoin d'aide ou envie de contribuer ? Ouvrez une issue sur GitHub ou contactez directement Naylm.

---

## 🎉 Remerciements

Merci d'utiliser **DispatchDockerWorking**, la version Docker de Dispatch Manager prête pour la production. 

**Bon déploiement !** 🚀

---

## 📝 Changelog récent

### Version actuelle (Décembre 2024)

- ✅ Migration complète vers PostgreSQL
- ✅ Système de notifications en temps réel
- ✅ Corrections complètes du Wiki (CSRF, timezone, sélection texte)
- ✅ Synchronisation temps réel des incidents
- ✅ Améliorations de stabilité et performance
- ✅ Protection CSRF sur tous les formulaires
- ✅ Gestion d'erreurs améliorée avec logs détaillés
- ✅ **NEW** : Interface responsive complète (mobile/tablet/desktop)
- ✅ **NEW** : Vue technicien adaptative (1/2/3 colonnes selon écran)
- ✅ **NEW** : Sidebar mobile avec backdrop et bouton optimisé

Pour plus de détails, consultez `docs/CHANGELOG.md`.
