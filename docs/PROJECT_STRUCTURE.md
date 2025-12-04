# Structure du projet Dispatch Manager

**Dernière mise à jour** : 2025-11-24

---

## 📂 Organisation des dossiers

```
DispatchDockerWorking/
│
├── 📄 Fichiers essentiels (racine)
├── 📁 maintenance/          # Scripts de maintenance
├── 📁 docs/                 # Documentation complète
├── 📁 templates/            # Templates HTML Jinja2
├── 📁 static/               # Assets statiques (CSS, JS, images)
├── 📁 scripts/              # Scripts utilitaires
└── 📁 archive/              # Fichiers obsolètes (non tracké Git)
```

---

## 🗂️ Détails par dossier

### 📄 Racine (14 fichiers essentiels)

| Fichier | Description |
|---------|-------------|
| `app.py` | ⭐ Application Flask principale (56 KB) |
| `db_config.py` | Configuration PostgreSQL avec wrapper SQLite-compatible |
| `wiki_routes_v2.py` | Routes pour le système Wiki |
| `ensure_db_integrity.py` | Vérification intégrité base de données |
| `requirements.txt` | Dépendances Python |
| `Dockerfile` | Image Docker de l'application |
| `docker-compose.yml` | Orchestration 3 containers (app, postgres, nginx) |
| `nginx.conf` | Configuration reverse proxy |
| `.dockerignore` | Exclusions pour build Docker |
| `.gitignore` | Exclusions Git |
| `.env.example` | Template variables d'environnement |
| `README.md` | ⭐ Documentation principale |
| `QUICK_START.md` | ⭐ Guide de démarrage rapide |
| `wiki-home.md` | Page d'accueil du Wiki |

---

### 📁 maintenance/

Scripts organisés par catégorie :

#### migrations/ (5 fichiers)
Scripts de migration et optimisation base de données

```bash
migrate_sqlite_to_postgres.py    # Migration SQLite → PostgreSQL
apply_indexes.py                  # Application des indexes de performance
apply_password_reset_migration.py # Migration colonne force_password_reset
add_indexes.sql                   # Définition des indexes PostgreSQL
add_password_reset_column.sql     # Schema migration password reset
```

**Utilisation** :
```bash
docker exec dispatch_manager python maintenance/migrations/migrate_sqlite_to_postgres.py
```

#### admin/ (3 fichiers)
Scripts d'administration des utilisateurs

```bash
reset_admin_password.py           # Réinitialiser mot de passe admin → melvin/admin
reset_technicien_passwords.py     # Réinitialiser mots de passe techniciens → prénom/minuscules
diagnostic_techniciens.py         # Diagnostic complet des techniciens
```

**Utilisation** :
```bash
docker exec dispatch_manager python maintenance/admin/reset_admin_password.py
```

#### tests/ (2 fichiers)
Scripts de test de l'application

```bash
test_login.py                     # Tests de connexion (Python + requests)
test_login_simple.sh              # Tests de connexion (bash + curl)
```

---

### 📁 docs/

Documentation complète organisée en 4 catégories :

#### deployment/ (3 fichiers)
Guides de déploiement et Docker

```
DEPLOY_GUIDE.md           # Guide de déploiement
DEPLOYMENT_GUIDE.md       # Guide de déploiement complet
DOCKER_README.md          # Documentation Docker
```

#### security/ (3 fichiers)
Documentation sécurité et authentification

```
AUTHENTICATION_FIXES.md          # Corrections système authentification
IDENTIFIANTS_DEFAUT.md           # ⭐ Liste complète identifiants par défaut
SECURITY_AUDIT_CHANGELOG.md      # Changelog audit sécurité
```

#### changelog/ (2 fichiers)
Historique des modifications

```
MOVED_FORCE_RESET_TO_TECHNICIENS.md  # Migration fonctionnalité reset
README_AUDIT.md                       # Rapport d'audit
```

#### guides/ (2 fichiers)
Guides techniques

```
DB_CONTEXT_MANAGER_GUIDE.md      # Guide gestion connexions DB
MIGRATION_POSTGRES.md             # Guide migration PostgreSQL
```

#### Autres fichiers (10+)
Documentation diverse à la racine de docs/

```
AUDIT_OPTIMISATIONS.md
CHANGELOG.md
CLEANUP_REPORT.md         # ⭐ Rapport de nettoyage du projet
DEMARRAGE_PRODUCTION.md
DEMARRAGE_RAPIDE.md
GUIDE_DEMARRAGE.md
PERSISTANCE_DONNEES.md
README.md
RESOLUTION_ERREUR_PORT.md
RESUME_MODIFICATIONS.md
WIKI_MODIFICATION_CATEGORIES.md
WIKI_VIDE_INFO.md
```

---

### 📁 templates/ (26 fichiers)

Templates HTML Jinja2 pour l'application :

#### Pages principales
```
home.html                 # Dashboard principal
home_content.html         # Contenu dashboard (mode colonnes)
login.html                # Page de connexion
configuration.html        # Configuration système (admin)
techniciens.html          # ⭐ Gestion des techniciens + force reset
```

#### Gestion incidents
```
add.html                  # Ajout incident
incident_detail.html      # Détail incident
```

#### Système Wiki
```
wiki_v2.html              # Interface Wiki v2
wiki_categories.html      # Gestion catégories Wiki
wiki_articles.html        # Liste articles Wiki
wiki_article_detail.html  # Détail article Wiki
wiki_create_article.html  # Création article
wiki_edit_article.html    # Édition article
```

#### Authentification & Sécurité
```
change_password_forced.html   # ⭐ Changement mot de passe forcé
reset_password.html           # Réinitialisation mot de passe
```

#### Autres templates (composants, modals, etc.)

---

### 📁 static/

Assets statiques de l'application :

#### css/ (3 fichiers)
```
style_modern.css          # ⭐ Styles principaux (avec anti-caret)
style.css                 # Styles de base
emoji_picker.css          # Styles picker emoji
```

#### js/ (1 fichier)
```
emoji_picker.js           # Sélecteur d'emoji pour Wiki
```

#### img/ (9 fichiers)
```
favicon-16x16.png
favicon-32x32.png
favicon.ico
android-chrome-192x192.png
android-chrome-512x512.png
apple-touch-icon.png
site.webmanifest
browserconfig.xml
mstile-150x150.png
```

---

### 📁 scripts/

Scripts utilitaires :

```
start_with_backup.py      # Démarrage avec backup auto
wsgi.py                   # Configuration WSGI
README.md                 # Documentation scripts
DEMARRER.bat              # Démarrage Windows
DEMARRER_AVEC_BACKUP.bat  # Démarrage + backup Windows
VIDER_WIKI.bat            # Vider base Wiki Windows
```

---

### 📁 archive/ (non tracké Git)

Fichiers obsolètes archivés pour référence :

#### old_backups/
```
dispatch.db.backup        # Ancien backup SQLite (110 KB)
dispatch.db-shm           # Fichier temporaire SQLite
dispatch.db-wal           # Fichier WAL SQLite
deploy.sh.old             # Ancien script de déploiement
```

#### old_sqlite_scripts/
```
ensure_db_integrity_sqlite.py.bak
backup_database.py
clear_wiki_categories.py
migrate_db.py
tech.py
web.config
```

---

## 🔑 Fichiers clés à connaître

### Pour démarrer rapidement
1. 📖 [QUICK_START.md](QUICK_START.md) - Guide de démarrage
2. 🔑 [docs/security/IDENTIFIANTS_DEFAUT.md](docs/security/IDENTIFIANTS_DEFAUT.md) - Identifiants de connexion

### Pour comprendre l'architecture
3. 📖 [README.md](README.md) - Documentation complète
4. 🏗️ [docs/guides/DB_CONTEXT_MANAGER_GUIDE.md](docs/guides/DB_CONTEXT_MANAGER_GUIDE.md) - Architecture DB

### Pour le déploiement
5. 🚀 [docs/deployment/DEPLOYMENT_GUIDE.md](docs/deployment/DEPLOYMENT_GUIDE.md) - Guide complet
6. 🐳 [docs/deployment/DOCKER_README.md](docs/deployment/DOCKER_README.md) - Documentation Docker

### Pour la maintenance
7. 🔧 [docs/CLEANUP_REPORT.md](docs/CLEANUP_REPORT.md) - Rapport de nettoyage
8. 🔒 [docs/security/AUTHENTICATION_FIXES.md](docs/security/AUTHENTICATION_FIXES.md) - Correctifs auth

---

## 🚀 Commandes rapides

### Démarrage
```bash
docker compose up -d
```

### Logs
```bash
docker logs dispatch_manager -f
```

### Accès application
```
http://localhost/login
```

### Connexion admin
```
Username: melvin
Password: admin
```

### Connexion technicien
```
Username: Hugo
Password: hugo
```

### Scripts de maintenance
```bash
# Réinitialiser mots de passe
docker exec dispatch_manager python maintenance/admin/reset_admin_password.py
docker exec dispatch_manager python maintenance/admin/reset_technicien_passwords.py

# Diagnostic techniciens
docker exec dispatch_manager python maintenance/admin/diagnostic_techniciens.py
```

---

## 📊 Statistiques du projet

- **Langage principal** : Python (Flask)
- **Base de données** : PostgreSQL 15
- **Templates** : 26 fichiers HTML (Jinja2)
- **Reverse proxy** : Nginx
- **Containers Docker** : 3 (app, postgres, nginx)
- **Documentation** : 20+ fichiers Markdown

---

**Dernière réorganisation** : 2025-11-24
**Voir** : [docs/CLEANUP_REPORT.md](docs/CLEANUP_REPORT.md) pour les détails
