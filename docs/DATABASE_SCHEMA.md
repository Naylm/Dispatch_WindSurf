# 📊 Schéma PostgreSQL - Dispatch Manager

## 🗄️ Vue d'ensemble

La base de données PostgreSQL contient **16 tables** organisées en 3 catégories :

1. **Authentification & Utilisateurs** (2 tables)
2. **Gestion des Incidents** (6 tables)
3. **Wiki / Base de Connaissances** (6 tables)
4. **Configuration** (2 tables supplémentaires)

---

## 📋 Tables détaillées

### 1. AUTHENTIFICATION & UTILISATEURS

#### `users` - Administrateurs
Gère les comptes administrateurs de l'application.

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Identifiant unique |
| `username` | VARCHAR(255) | UNIQUE, NOT NULL | Nom d'utilisateur |
| `password` | VARCHAR(255) | NOT NULL | Mot de passe hashé |
| `role` | VARCHAR(50) | NOT NULL | Rôle (admin/user) |
| `force_password_reset` | INTEGER | DEFAULT 0 | Flag de réinitialisation forcée (0/1) |

**Compte par défaut** : `admin` / `admin`

---

#### `techniciens` - Techniciens support
Gère les comptes des techniciens qui traitent les incidents.

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Identifiant unique |
| `prenom` | VARCHAR(255) | UNIQUE, NOT NULL | Prénom (utilisé comme username) |
| `password` | VARCHAR(255) | | Mot de passe hashé |
| `role` | VARCHAR(50) | DEFAULT 'technicien' | Rôle du technicien |
| `actif` | INTEGER | DEFAULT 1 | Statut actif (1) ou désactivé (0) |
| `force_password_reset` | INTEGER | DEFAULT 0 | Flag de réinitialisation forcée |

---

### 2. GESTION DES INCIDENTS

#### `incidents` - Tickets support

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Identifiant unique |
| `numero` | VARCHAR(255) | NOT NULL | Numéro du ticket |
| `site` | VARCHAR(255) | NOT NULL | Site concerné |
| `sujet` | VARCHAR(255) | NOT NULL | Catégorie |
| `urgence` | VARCHAR(255) | NOT NULL | Priorité |
| `collaborateur` | VARCHAR(255) | NOT NULL | Technicien assigné |
| `etat` | VARCHAR(255) | DEFAULT 'Affecté' | Statut actuel |
| `notes` | TEXT | | Notes du technicien |
| `note_dispatch` | TEXT | | Note de l'admin |
| `valide` | INTEGER | DEFAULT 0 | Validation (0/1) |
| `date_affectation` | DATE | NOT NULL | Date d'affectation |
| `archived` | INTEGER | DEFAULT 0 | Archivé (0/1) |
| `localisation` | VARCHAR(255) | DEFAULT '' | Localisation |

---

#### `historique` - Historique des modifications

| Colonne | Type | Contraintes | Description |
|---------|------|-------------|-------------|
| `id` | SERIAL | PRIMARY KEY | Identifiant unique |
| `incident_id` | INTEGER | FK → incidents.id | Incident concerné |
| `champ` | VARCHAR(255) | NOT NULL | Nom du champ modifié |
| `ancienne_valeur` | TEXT | | Valeur avant |
| `nouvelle_valeur` | TEXT | | Valeur après |
| `modifie_par` | VARCHAR(255) | NOT NULL | Modificateur |
| `date_modification` | VARCHAR(255) | NOT NULL | Date/heure |

**Clé étrangère** : `ON DELETE CASCADE`

---

#### Autres tables de configuration

- **`sujets`** : Catégories d'incidents (Portables, PC Fixe, Réseau, etc.)
- **`priorites`** : Niveaux d'urgence avec couleurs (Basse, Moyenne, Haute, Critique)
- **`sites`** : Localisations (HD, HGRL, SJ, Periph)
- **`statuts`** : États des tickets avec catégories (en_cours, suspendu, traite)

---

### 3. WIKI / BASE DE CONNAISSANCES

#### `wiki_categories` - Catégories Wiki (niveau 1)
#### `wiki_subcategories` - Sous-catégories (niveau 2)
#### `wiki_articles` - Articles de documentation
#### `wiki_history` - Versionning des articles
#### `wiki_votes` - Système de like/dislike
#### `wiki_images` - Images uploadées

---

## 🔧 Migrations automatiques

Le script `ensure_db_integrity.py` s'exécute **automatiquement au démarrage** et :

✅ Crée toutes les tables manquantes
✅ Ajoute les colonnes manquantes
✅ Insère les données par défaut
✅ Vérifie l'intégrité du schéma

### Migrations incluses :
- Ajout de `force_password_reset` dans `users` et `techniciens`
- Ajout de `note_dispatch` dans `incidents`
- Ajout de `category` dans `statuts`

---

## 🧪 Vérification du schéma

```bash
# Vérifier le schéma complet
python verify_database.py

# Forcer la création/réparation
python ensure_db_integrity.py
```

---

## 🚀 Accès à la base

```bash
# Via Docker
docker-compose exec postgres psql -U dispatch_user -d dispatch

# Backup
docker exec dispatch_postgres pg_dump -U dispatch_user dispatch > backup.sql

# Restore
docker exec -i dispatch_postgres psql -U dispatch_user dispatch < backup.sql
```

---

**Version** : 2.0
**PostgreSQL** : 15+
**Dernière mise à jour** : 2025-01-26
