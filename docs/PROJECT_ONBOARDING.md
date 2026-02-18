# 🚀 Guide d'Intégration Rapide - Dispatch Manager

Ce guide permet à un nouveau développeur de comprendre le projet en **60 minutes maximum**.

---

## 1. Premier Contact (5 minutes)

### Lire ces fichiers dans l'ordre :

1. **[README.md](README.md)** - Vue d'ensemble et installation
2. **[QUICK_START.md](QUICK_START.md)** - Démarrage rapide (si existe)
3. **[docker-compose.yml](docker-compose.yml)** - Architecture des conteneurs
4. **[app.py](app.py)** (lignes 1-100) - Point d'entrée Flask

### Questions à se poser :

- ✅ Quel est le but du projet ? → Gestion d'incidents IT + Wiki collaboratif
- ✅ Quelles sont les 3 fonctionnalités principales ? → Incidents, Wiki, Notifications temps réel
- ✅ Comment démarrer l'application ? → `docker compose up -d`
- ✅ Où sont les données stockées ? → Volumes Docker (postgres_data, dispatch_uploads)

---

## 2. Exploration de l'Architecture (15 minutes)

### Architecture Système

```
┌─────────┐        ┌────────┐       ┌──────────┐       ┌────────────┐
│ Client  │──HTTP──│ Nginx  │──────→│  Flask   │──────→│ PostgreSQL │
│(Browser)│  :80   │(Alpine)│       │(Gunicorn)│       │     15     │
└─────────┘        └────────┘       └──────────┘       └────────────┘
                        │                 │
                        │              Socket.IO
                        ↓              (temps réel)
                   /static/uploads/
                   (images wiki)
```

### Conteneurs Docker

| Conteneur | Image | Rôle | Port |
|-----------|-------|------|------|
| `dispatch_postgres` | postgres:15-alpine | Base de données | 5432 (interne) |
| `dispatch_manager` | custom (Dockerfile) | Application Flask | 5000 (interne) |
| `dispatch_nginx` | nginx:alpine | Reverse proxy | 80 (public) |

### Volumes Docker (Données Persistantes)

| Volume | Contenu | Emplacement |
|--------|---------|-------------|
| `postgres_data` | Tables, index, données SQL | `/var/lib/postgresql/data` |
| `dispatch_uploads` | Images wiki uploadées | `/app/static/uploads` |
| `dispatch_data` | Backups, configuration | `/app/data` |

### Fichiers Clés

| Fichier | Rôle | À lire ? |
|---------|------|----------|
| [app.py](app.py) | Application principale Flask (1600+ lignes) | ⭐ OUI |
| [db_config.py](db_config.py) | Configuration PostgreSQL + wrapper | ⭐ OUI |
| [wiki_routes_v2.py](wiki_routes_v2.py) | Routes Wiki V2 | Si besoin wiki |
| [notification_helpers.py](notification_helpers.py) | Notifications Socket.IO | Si besoin temps réel |
| [docker-compose.yml](docker-compose.yml) | Orchestration conteneurs | ⭐ OUI |
| [nginx.conf](nginx.conf) | Configuration reverse proxy | Si besoin nginx |
| [ensure_db_integrity.py](ensure_db_integrity.py) | Init base de données | Si migration/debug |

### Structure Base de Données

Lire : [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md)

**Tables principales :**

- `users` : Utilisateurs et authentification (admin, technicien)
- `incidents` : Tickets/incidents avec statuts
- `wiki_articles` : Base de connaissances (Markdown)
- `wiki_categories` : Catégories/sous-catégories (hiérarchie)

---

## 3. Premiers Tests (10 minutes)

### Démarrer l'application

```bash
cd DispatchDockerWorking
docker compose up -d
docker compose logs -f app
```

**Attendre 10-15 secondes** pour l'initialisation PostgreSQL.

### Accéder à l'interface

- **URL** : http://localhost
- **Login** : `admin`
- **Password** : `admin`

### Tester les fonctionnalités

1. **Créer un incident**
   - Menu : "Ajouter un incident"
   - Remplir : Site, Type, Description, Priorité
   - Observer : Notification temps réel

2. **Assigner à un technicien**
   - Dashboard admin → Menu déroulant technicien
   - Observer : Synchronisation instantanée

3. **Créer un article wiki**
   - Menu Wiki → Nouvelle catégorie
   - Créer article avec Markdown
   - Uploader une image (drag & drop)

4. **Observer notifications temps réel**
   - Ouvrir 2 onglets (admin + technicien)
   - Changer statut dans un onglet
   - Observer mise à jour dans l'autre

---

## 4. Modification du Code (20 minutes)

### Workflow de développement

```bash
# 1. Modifier le code source
nano app.py  # ou votre éditeur

# 2. Redémarrer le conteneur
docker compose restart app

# 3. Vérifier les logs
docker compose logs -f app

# 4. Tester dans le navigateur
# Ouvrir http://localhost
```

### Points d'entrée pour modifications courantes

#### ✏️ Ajouter une nouvelle page

**Étapes :**
1. Créer template dans `templates/nouvelle_page.html`
2. Ajouter route dans `app.py` :
   ```python
   @app.route('/nouvelle-page')
   @login_required
   def nouvelle_page():
       return render_template('nouvelle_page.html')
   ```
3. Redémarrer : `docker compose restart app`

#### 🎨 Modifier le CSS

**Étapes :**
1. Éditer `static/css/style.css` ou `static/css/style_modern.css`
2. Vider cache navigateur : `Ctrl+F5` (Windows) ou `Cmd+Shift+R` (Mac)
3. Pas besoin de redémarrer Docker

#### 🗄️ Modifier la base de données

**Étapes :**
1. Créer script migration dans `maintenance/migrations/nouvelle_migration.py`
2. Tester avec `psql` :
   ```bash
   docker exec -it dispatch_postgres psql -U dispatch_user dispatch
   # Tester requêtes SQL
   ```
3. Appliquer migration :
   ```bash
   docker compose exec app python maintenance/migrations/nouvelle_migration.py
   ```

#### 🔌 Ajouter une route API

**Exemple :**
```python
# Dans app.py
@app.route('/api/incidents/<int:incident_id>', methods=['GET'])
@login_required
def get_incident_api(incident_id):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM incidents WHERE id = %s', (incident_id,))
    incident = cur.fetchone()
    cur.close()
    conn.close()

    if not incident:
        return jsonify({'error': 'Incident not found'}), 404

    return jsonify({
        'id': incident['id'],
        'site': incident['site'],
        'description': incident['description']
    })
```

---

## 5. Debugging (15 minutes)

### Logs utiles

```bash
# Logs application Flask (erreurs Python, routes)
docker compose logs -f app

# Logs base de données (requêtes SQL)
docker compose logs -f postgres

# Logs nginx (requêtes HTTP)
docker compose logs -f nginx

# Tous les logs
docker compose logs -f

# Filtrer par terme
docker compose logs -f app | grep ERROR
```

### Accès direct à la base de données

```bash
# Ouvrir psql
docker exec -it dispatch_postgres psql -U dispatch_user dispatch

# Commandes SQL utiles
\dt                          # Lister tables
\d users                     # Décrire table users
SELECT COUNT(*) FROM incidents;
SELECT * FROM users LIMIT 5;
\q                           # Quitter
```

### Vérifier l'état des conteneurs

```bash
# État des services
docker compose ps

# Processus en cours
docker compose top

# Ressources utilisées
docker stats dispatch_postgres dispatch_manager dispatch_nginx

# Health checks
docker inspect dispatch_postgres | grep -A 10 "Health"
```

### Debugger une erreur 500

1. **Voir les logs Flask** :
   ```bash
   docker compose logs --tail=100 app
   ```

2. **Vérifier la base de données** :
   ```bash
   docker compose exec app python ensure_db_integrity.py
   ```

3. **Tester connexion PostgreSQL** :
   ```bash
   docker exec dispatch_postgres pg_isready -U dispatch_user
   ```

---

## 6. Documentation Avancée

### Pour aller plus loin

| Document | Sujet |
|----------|-------|
| [docs/GUIDE_IMPLEMENTATION.md](docs/GUIDE_IMPLEMENTATION.md) | Guide d'implémentation détaillé |
| [docs/deployment/DEPLOY_GUIDE.md](docs/deployment/DEPLOY_GUIDE.md) | Déploiement production (SSL, domaine) |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Résolution de problèmes courants |
| [docs/DATABASE_SCHEMA.md](docs/DATABASE_SCHEMA.md) | Schéma base de données complet |
| [maintenance/README.md](maintenance/README.md) | Scripts de maintenance |

### Cas d'usage avancés

| Besoin | Documentation |
|--------|---------------|
| Migrer depuis SQLite | [docs/guides/MIGRATION_POSTGRES.md](docs/guides/MIGRATION_POSTGRES.md) |
| Backup/Restore | [docs/PERSISTANCE_DONNEES.md](docs/PERSISTANCE_DONNEES.md) |
| Notifications temps réel | [docs/README_NOTIFICATIONS.md](docs/README_NOTIFICATIONS.md) |
| Gestion DB avancée | [docs/guides/DB_CONTEXT_MANAGER_GUIDE.md](docs/guides/DB_CONTEXT_MANAGER_GUIDE.md) |

---

## 7. Checklist de Compréhension

Vous devriez être capable de :

### Opérations de base
- [ ] Démarrer/arrêter l'application Docker
- [ ] Accéder à l'interface et se connecter (admin/admin)
- [ ] Consulter les logs des 3 conteneurs
- [ ] Identifier où sont stockées les données persistantes

### Architecture
- [ ] Expliquer l'architecture (3 conteneurs + 3 volumes)
- [ ] Décrire le flux d'une requête HTTP (Browser → Nginx → Flask → PostgreSQL)
- [ ] Comprendre le rôle de chaque conteneur

### Développement
- [ ] Localiser les fichiers de configuration clés (app.py, docker-compose.yml, nginx.conf)
- [ ] Modifier un template HTML et voir le résultat
- [ ] Créer une nouvelle route Flask
- [ ] Éditer du CSS et rafraîchir le navigateur

### Base de données
- [ ] Faire un backup de la base de données
- [ ] Accéder à psql pour exécuter du SQL
- [ ] Lister les tables et comprendre leur rôle

### Debugging
- [ ] Consulter les logs pour diagnostiquer une erreur
- [ ] Vérifier l'état des conteneurs
- [ ] Redémarrer un conteneur spécifique

---

## 8. Ressources Supplémentaires

### Technologies utilisées

| Technologie | Version | Documentation |
|-------------|---------|---------------|
| Flask | 2.3.3 | https://flask.palletsprojects.com/ |
| PostgreSQL | 15 | https://www.postgresql.org/docs/15/ |
| Socket.IO | 5.3.4 | https://python-socketio.readthedocs.io/ |
| Docker Compose | 3.8 | https://docs.docker.com/compose/ |
| Nginx | Alpine | https://nginx.org/en/docs/ |
| Gunicorn | 21.2.0 | https://docs.gunicorn.org/ |

### Commandes Docker utiles

```bash
# Reconstruire les images
docker compose build --no-cache

# Supprimer tout et recommencer
docker compose down -v  # ⚠️ DANGER : Supprime les données
docker compose up --build

# Inspecter un volume
docker volume inspect dispatchdockerworking_postgres_data

# Backup complet
docker exec dispatch_postgres pg_dump -U dispatch_user dispatch > backup_$(date +%Y%m%d).sql

# Restaurer backup
docker exec -i dispatch_postgres psql -U dispatch_user dispatch < backup_20241204.sql
```

### Contact & Support

- **Issues GitHub** : https://github.com/Naylm/DispatchDockerWorking/issues
- **Documentation** : Dossier `docs/`
- **Auteur** : [Naylm](https://github.com/Naylm)

---

## 🎯 Résumé de Compréhension

Après avoir suivi ce guide, vous maîtrisez :

1. ✅ **Architecture** : 3 conteneurs Docker (PostgreSQL + Flask + Nginx)
2. ✅ **Données** : 3 volumes Docker pour persistance (postgres_data, dispatch_uploads, dispatch_data)
3. ✅ **Développement** : Workflow de modification + redémarrage
4. ✅ **Debugging** : Logs, psql, inspecteur Docker
5. ✅ **Fonctionnalités** : Incidents, Wiki, Notifications temps réel

**Temps total pour maîtriser les bases : ~60 minutes**

---

**Bon développement !** 🚀

_Généré avec ❤️ pour faciliter l'intégration des nouveaux développeurs_
