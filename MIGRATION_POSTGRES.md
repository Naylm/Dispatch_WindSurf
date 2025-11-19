# Migration vers PostgreSQL

## Vue d'ensemble

DispatchDocker utilise maintenant **PostgreSQL** au lieu de SQLite pour une meilleure scalabilité, concurrence et fiabilité en production.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────┐
│   Nginx     │────▶│  Flask App   │────▶│ PostgreSQL│
│   (port 80) │     │  (port 5000) │     │ (port 5432)│
└─────────────┘     └──────────────┘     └───────────┘
```

## Démarrage rapide

### 1. Première installation (base vierge)

```bash
# Lancer tous les services
docker compose up --build

# L'application crée automatiquement :
# - La base PostgreSQL
# - Toutes les tables
# - Un compte admin/admin par défaut
```

Accès : http://localhost  
Login : `admin` / `admin`

### 2. Migration depuis SQLite existant

Si tu as déjà un fichier `dispatch.db` avec des données :

```bash
# 1. Démarrer PostgreSQL seul
docker compose up -d postgres

# 2. Attendre que PostgreSQL soit prêt (5-10 secondes)
docker compose logs postgres

# 3. Lancer le script de migration
docker compose run --rm app python migrate_sqlite_to_postgres.py

# 4. Démarrer tous les services
docker compose up -d
```

Le script copie automatiquement :
- ✅ Tous les utilisateurs et techniciens
- ✅ Tous les incidents et historiques
- ✅ Toutes les configurations (sites, priorités, statuts, sujets)
- ✅ Tous les articles Wiki et métadonnées

## Configuration

### Variables d'environnement

Dans `docker-compose.yml` ou fichier `.env` :

```yaml
# PostgreSQL
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=dispatch
POSTGRES_USER=dispatch_user
POSTGRES_PASSWORD=dispatch_pass  # ⚠️ Changer en production !
```

### Sécurité

**⚠️ IMPORTANT** : Change le mot de passe PostgreSQL en production :

```yaml
environment:
  - POSTGRES_PASSWORD=un_mot_de_passe_fort_et_unique
```

## Avantages PostgreSQL vs SQLite

| Critère | SQLite | PostgreSQL |
|---------|--------|------------|
| **Concurrence** | Verrous fichier, 1 writer | Multi-utilisateurs simultanés |
| **Transactions** | Limitées | ACID complètes |
| **Performance** | Bonne (petite échelle) | Excellente (grande échelle) |
| **Backup** | Copie fichier | pg_dump / réplication |
| **Types de données** | Basiques | Avancés (JSON, arrays, etc.) |
| **Scalabilité** | Limitée | Horizontale + verticale |

## Opérations courantes

### Backup de la base

```bash
# Backup complet
docker compose exec postgres pg_dump -U dispatch_user dispatch > backup_$(date +%Y%m%d).sql

# Restaurer un backup
docker compose exec -T postgres psql -U dispatch_user dispatch < backup_20251119.sql
```

### Accéder à PostgreSQL

```bash
# Console psql
docker compose exec postgres psql -U dispatch_user -d dispatch

# Commandes utiles :
# \dt          - Lister les tables
# \d+ incidents - Décrire une table
# \q           - Quitter
```

### Réinitialiser la base

```bash
# ⚠️ ATTENTION : Supprime toutes les données !
docker compose down -v
docker compose up --build
```

## Dépannage

### Erreur de connexion PostgreSQL

```
psycopg2.OperationalError: could not connect to server
```

**Solution** : Attendre que PostgreSQL soit prêt

```bash
docker compose logs postgres
# Attendre : "database system is ready to accept connections"
```

### Tables manquantes

```bash
# Recréer les tables
docker compose exec app python ensure_db_integrity.py
```

### Performances lentes

```bash
# Vérifier les connexions actives
docker compose exec postgres psql -U dispatch_user -d dispatch -c "SELECT count(*) FROM pg_stat_activity;"

# Augmenter les workers Gunicorn (docker-compose.yml)
environment:
  - GUNICORN_WORKERS=2  # ou plus selon CPU
```

## Fichiers modifiés

- `db_config.py` : Connexion PostgreSQL avec wrapper compatible SQLite
- `ensure_db_integrity.py` : Création des tables PostgreSQL
- `migrate_sqlite_to_postgres.py` : Script de migration
- `docker-compose.yml` : Service PostgreSQL + variables
- `requirements.txt` : Ajout de psycopg2-binary

## Support

Pour toute question ou problème :
1. Consulter les logs : `docker compose logs app`
2. Vérifier PostgreSQL : `docker compose logs postgres`
3. Ouvrir une issue sur GitHub

---

**Note** : L'ancien fichier `dispatch.db` (SQLite) est conservé en backup automatique sous `ensure_db_integrity_sqlite.py.bak`.
