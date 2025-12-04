# 📚 Guide de Contexte du Projet - DispatchDockerWorking

> **Documentation de référence pour comprendre rapidement le projet lors d'une nouvelle session de développement**

## 🎯 Vue d'ensemble

**DispatchDockerWorking** est une application web de gestion d'incidents (ticketing) développée avec Flask et PostgreSQL, déployée via Docker Compose.

### Technologies principales
- **Backend** : Flask (Python 3.11)
- **Base de données** : PostgreSQL 15 (migration depuis SQLite terminée)
- **WebSocket** : Flask-SocketIO pour les mises à jour en temps réel
- **Frontend** : HTML/CSS/JavaScript (Bootstrap 5)
- **Déploiement** : Docker Compose avec Nginx comme reverse proxy
- **Authentification** : Sessions Flask avec hashage de mots de passe (Werkzeug)

---

## 📁 Structure du Répertoire

```
DispatchDockerWorking/
├── app.py                    # ⭐ APPLICATION PRINCIPALE - Point d'entrée Flask
├── db_config.py              # Configuration PostgreSQL avec wrapper SQLite-compatible
├── ensure_db_integrity.py    # Initialisation/vérification de la base de données
├── notification_helpers.py   # Système de notifications WebSocket
├── wiki_routes_v2.py         # Routes pour la base de connaissances (Wiki)
├── utils_stability.py        # Utilitaires de stabilité
│
├── dispatch.ps1              # ⭐ Script PowerShell principal (équivalent Makefile)
├── Makefile                  # Script Make pour Linux/Mac
├── docker-compose.yml        # ⭐ Configuration Docker Compose
├── Dockerfile                # Image Docker de l'application
├── nginx.conf                # Configuration Nginx
├── requirements.txt          # Dépendances Python
│
├── templates/                # Templates Jinja2 (HTML)
│   ├── home.html             # Page principale (dashboard)
│   ├── techniciens.html      # Gestion des techniciens
│   ├── login.html            # Page de connexion
│   └── ...
│
├── static/                   # Fichiers statiques (CSS, JS, images)
│   ├── css/
│   ├── js/
│   └── img/
│
├── scripts/                  # Scripts utilitaires
│   ├── debug_login.py        # Diagnostic des problèmes de connexion
│   ├── reset_admin_password.py # Réinitialisation mot de passe admin
│   ├── verify_database.py    # Vérification de la base de données
│   ├── start.bat / start.sh  # Scripts de démarrage
│   └── ...
│
├── docs/                     # Documentation
│   ├── DATABASE_SCHEMA.md    # Schéma de la base de données
│   ├── DEFAULT_DATA.md       # Données par défaut
│   ├── TROUBLESHOOTING.md    # Guide de dépannage
│   ├── migrations/           # Documentation des migrations
│   └── ...
│
├── maintenance/              # Scripts de maintenance
│   ├── migrations/           # Scripts de migration
│   └── admin/                # Scripts d'administration
│
└── data/                     # Données persistantes (créé par Docker)
    └── backups/              # Backups de la base de données
```

---

## 🔑 Fichiers Clés à Comprendre

### 1. `app.py` - Application Principale
- **Rôle** : Point d'entrée Flask, contient toutes les routes
- **Sections importantes** :
  - Routes d'authentification (`/login`, `/logout`)
  - Routes de gestion des incidents (`/`, `/add`, `/edit_incident`, etc.)
  - Routes de gestion des techniciens (`/techniciens`, `/toggle_technicien`)
  - Routes de configuration (`/configuration`)
  - Routes API (`/api/home-content`, etc.)
- **Note** : Utilise PostgreSQL via `db_config.py`

### 2. `db_config.py` - Configuration Base de Données
- **Rôle** : Gère la connexion PostgreSQL avec wrapper compatible SQLite
- **Fonction principale** : `get_db()` retourne une connexion PostgreSQL
- **Variables d'environnement** :
  - `POSTGRES_HOST` (défaut: "postgres")
  - `POSTGRES_PORT` (défaut: "5432")
  - `POSTGRES_DB` (défaut: "dispatch")
  - `POSTGRES_USER` (défaut: "dispatch_user")
  - `POSTGRES_PASSWORD` (défaut: "dispatch_pass")

### 3. `docker-compose.yml` - Configuration Docker
- **Services** :
  - `postgres` : Base de données PostgreSQL
  - `app` : Application Flask
  - `nginx` : Reverse proxy
- **Volumes** :
  - `postgres_data` : Données PostgreSQL persistantes
  - `dispatch_uploads` : Fichiers uploadés (Wiki)
  - `dispatch_data` : Données de l'application

### 4. `dispatch.ps1` - Script PowerShell Principal
- **Rôle** : Script d'administration (équivalent Makefile pour Windows)
- **Commandes principales** :
  - `.\dispatch.ps1 init` : Installation complète
  - `.\dispatch.ps1 up` : Démarrer les services
  - `.\dispatch.ps1 down` : Arrêter les services
  - `.\dispatch.ps1 logs` : Voir les logs
  - `.\dispatch.ps1 debug-login` : Diagnostiquer connexions
  - `.\dispatch.ps1 reset-admin` : Réinitialiser mot de passe admin

---

## 🗄️ Base de Données PostgreSQL

### Connexion
- **Host** : `postgres` (dans Docker) ou `localhost` (accès externe)
- **Port** : `5432`
- **Database** : `dispatch`
- **User** : `dispatch_user`
- **Password** : `dispatch_pass`

### Tables principales
- `incidents` : Tickets/incidents
- `techniciens` : Comptes techniciens
- `users` : Comptes administrateurs
- `historique` : Historique des modifications
- `priorites`, `sites`, `statuts`, `sujets` : Tables de configuration
- `wiki_articles`, `wiki_categories` : Base de connaissances

### Volume Docker
- **Nom** : `dispatchdockerworking_postgres_data`
- **Emplacement** : Géré par Docker Desktop (volume local)

---

## 🚀 Commandes Essentielles

### Démarrage
```powershell
# Windows
.\dispatch.ps1 init      # Première installation
.\dispatch.ps1 up       # Démarrer

# Linux/Mac
make init
make up
```

### Développement
```powershell
.\dispatch.ps1 logs          # Voir tous les logs
.\dispatch.ps1 logs-app      # Logs application uniquement
.\dispatch.ps1 shell         # Shell interactif dans le conteneur
.\dispatch.ps1 ps            # État des conteneurs
```

### Maintenance
```powershell
.\dispatch.ps1 backup        # Sauvegarder la base
.\dispatch.ps1 debug-login  # Diagnostiquer problèmes de connexion
.\dispatch.ps1 reset-admin   # Réinitialiser mot de passe admin
```

---

## 🔐 Authentification

### Types d'utilisateurs
1. **Admin** (table `users`)
   - Accès complet : gestion incidents, techniciens, configuration
   - Identifiants par défaut : Voir `docs/DEFAULT_DATA.md`

2. **Technicien** (table `techniciens`)
   - Accès limité : voir/modifier ses incidents assignés
   - Création via interface admin (`/techniciens`)

### Sécurité
- Mots de passe hashés avec Werkzeug (pbkdf2 ou scrypt)
- Protection CSRF activée (Flask-WTF)
- Sessions Flask avec expiration (8 heures)

---

## 🎨 Interface Utilisateur

### Vue Admin
- **Route** : `/`
- **Fonctionnalités** :
  - Colonnes par technicien (drag & drop)
  - Filtres par statut, priorité, site
  - Statistiques en temps réel
  - Gestion complète des incidents

### Vue Technicien
- **Route** : `/` (vue différente selon le rôle)
- **Fonctionnalités** :
  - Cartes d'incidents assignés
  - Modification de statut
  - Notes et localisation
  - Base de connaissances (Wiki)

---

## 🔄 Workflow de Développement

### Modifier le code
1. Modifier les fichiers (app.py, templates, etc.)
2. Redémarrer le conteneur : `.\dispatch.ps1 restart`
3. Voir les logs : `.\dispatch.ps1 logs-app`

### Ajouter une fonctionnalité
1. Créer/modifier les routes dans `app.py`
2. Créer/modifier les templates dans `templates/`
3. Ajouter le CSS/JS dans `static/` si nécessaire
4. Tester et redémarrer

### Migrations base de données
- Scripts dans `maintenance/migrations/`
- Migration SQLite → PostgreSQL déjà effectuée
- Modifications de schéma : utiliser `ensure_db_integrity.py`

---

## 📝 Conventions de Code

### Routes Flask
- Format : `/resource` ou `/resource/action/<id>`
- Méthodes : `GET` pour affichage, `POST` pour modifications
- Protection : Vérifier `session["role"]` pour les routes admin

### Base de données
- Utiliser `get_db()` de `db_config.py`
- **IMPORTANT** : Fermer les connexions avec `db.close()`
- Requêtes : Utiliser `?` comme placeholder (converti automatiquement en `%s` pour PostgreSQL)

### Templates
- Héritage : Utiliser `base.html` si disponible
- Variables : Passées depuis les routes Flask
- Filtres Jinja2 : `format_date`, `contrast_color` (définis dans app.py)

---

## 🐛 Dépannage Rapide

### Problème de connexion
```powershell
.\dispatch.ps1 debug-login
```

### Base de données inaccessible
```powershell
.\dispatch.ps1 logs-db
.\dispatch.ps1 shell-db
```

### Application ne démarre pas
```powershell
.\dispatch.ps1 logs-app
.\dispatch.ps1 rebuild
```

### Mot de passe admin oublié
```powershell
.\dispatch.ps1 reset-admin
```

### Plus d'infos
Voir `docs/TROUBLESHOOTING.md`

---

## 📚 Documentation Complémentaire

- **README.md** : Documentation principale
- **QUICK_START.md** : Guide de démarrage rapide
- **PROJECT_STRUCTURE.md** : Structure détaillée du projet
- **docs/DATABASE_SCHEMA.md** : Schéma complet de la base de données
- **docs/TROUBLESHOOTING.md** : Guide de dépannage détaillé
- **docs/migrations/MIGRATION_REPORT.md** : Rapport de migration SQLite → PostgreSQL

---

## 🔗 Points d'Entrée Importants

### Pour comprendre le flux d'authentification
1. `app.py` → Route `/login` (ligne ~741)
2. Vérifie `users` puis `techniciens`
3. Crée session Flask avec `session["user"]`, `session["role"]`

### Pour comprendre la gestion des incidents
1. `app.py` → Route `/` (ligne ~147)
2. Récupère incidents depuis PostgreSQL
3. Affiche via `templates/home.html`

### Pour comprendre les notifications temps réel
1. `notification_helpers.py` : Fonctions d'émission
2. `app.py` : Utilise `socketio.emit()` dans les routes
3. `templates/home.html` : JavaScript écoute les événements SocketIO

---

## ⚠️ Notes Importantes

1. **PostgreSQL est utilisé** : Plus de SQLite (migration terminée)
2. **dispatch.ps1 doit rester à la racine** : C'est le script principal d'administration
3. **Les scripts utilitaires sont dans `scripts/`** : debug_login.py, reset_admin_password.py, etc.
4. **La documentation est dans `docs/`** : DATABASE_SCHEMA.md, TROUBLESHOOTING.md, etc.
5. **Les fichiers temporaires sont ignorés** : dispatch.db, sqlite_counts.json, etc. (voir .gitignore)

---

## 🎯 Checklist pour Nouvelle Session

Quand vous reprenez le projet sur un nouvel ordinateur :

1. ✅ Lire ce fichier (`PROJECT_CONTEXT.md`)
2. ✅ Vérifier que Docker est installé
3. ✅ Cloner le repo : `git clone https://github.com/Naylm/DispatchDockerWorking.git`
4. ✅ Lancer : `.\dispatch.ps1 init` puis `.\dispatch.ps1 up`
5. ✅ Accéder : http://localhost
6. ✅ Vérifier les logs : `.\dispatch.ps1 logs-app`

---

**Dernière mise à jour** : Après nettoyage et organisation du répertoire (2025-01-26)
**Version** : 2.0 (PostgreSQL)

