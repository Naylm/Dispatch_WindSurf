# 📊 Données par défaut - Dispatch Manager

Ce document liste toutes les données insérées automatiquement lors de la création de la base PostgreSQL.

---

## 👤 Utilisateurs

### Table `users`
| Username | Password | Role | Note |
|----------|----------|------|------|
| `admin` | `admin` | admin | ⚠️ **Changer en production !** |

### Table `techniciens`
Aucun technicien créé par défaut. À configurer via l'interface admin.

---

## 📋 Sujets (12 catégories)

### Table `sujets`
Liste complète des catégories d'incidents disponibles :

1. **Portables** - Problèmes de PC portables
2. **PC Fixe** - Problèmes de PC fixes
3. **Imprimantes - impressions** - Problèmes d'impression
4. **Réseau** - Connectivité, WiFi, câblage
5. **Matériel** - Hardware divers
6. **Logiciel** - Applications, logiciels
7. **Téléphonie** - Téléphones fixes/mobiles
8. **Messagerie** - Email, Outlook, Exchange
9. **Applications métiers** - ERP, CRM, etc.
10. **Sécurité** - Antivirus, pare-feu, accès
11. **Accès / Droits** - Permissions, comptes
12. **Autre** - Autres demandes

---

## ⚡ Priorités (4 niveaux)

### Table `priorites`
| Nom | Couleur | Niveau | Utilisation |
|-----|---------|--------|-------------|
| **Basse** | 🟢 #28a745 | 1 | Demandes non urgentes |
| **Moyenne** | 🟡 #ffc107 | 2 | Demandes standard |
| **Haute** | 🟠 #fd7e14 | 3 | Nécessite intervention rapide |
| **Critique** | 🔴 #dc3545 | 4 | Urgence absolue, impact majeur |

---

## 🏢 Sites (4 localisations)

### Table `sites`
| Nom | Couleur | Description |
|-----|---------|-------------|
| **HD** | 🔵 #007bff | Hôpital principal |
| **HGRL** | 🟣 #6f42c1 | Hôpital HGRL |
| **SJ** | 🔴 #e83e8c | Site SJ |
| **Periph** | 🔷 #17a2b8 | Sites périphériques |

---

## 🔄 Statuts (9 statuts organisés en 4 catégories)

### Table `statuts`

#### 1️⃣ EN COURS (3 statuts)
Tickets actifs en cours de traitement.

| Nom | Couleur | Code |
|-----|---------|------|
| **Affecté** | 🔵 #007bff | Vient d'être assigné |
| **En cours de préparation** | 🔷 #0dcaf0 | Préparation en cours |
| **En intervention** | 🟢 #20c997 | Technicien sur place |

#### 2️⃣ SUSPENDU (2 statuts)
Tickets en pause temporaire.

| Nom | Couleur | Code |
|-----|---------|------|
| **Suspendu** | 🟠 #fd7e14 | En attente / Bloqué |
| **Intervention programmée** | 🟡 #ffc107 | RDV planifié |

#### 3️⃣ TRANSFÉRÉ (2 statuts)
Tickets transférés à d'autres services.

| Nom | Couleur | Code |
|-----|---------|------|
| **Transféré** | 🟣 #6f42c1 | Transféré à autre équipe |
| **En réservation** | 🔴 #d63384 | Matériel en commande |

#### 4️⃣ TRAITÉ (2 statuts)
Tickets terminés.

| Nom | Couleur | Code |
|-----|---------|------|
| **Traité** | 🟢 #28a745 | Résolu et fermé |
| **Clôturé** | 🟢 #198754 | Archivé définitivement |

---

## 📖 Wiki (Vide par défaut)

Les tables suivantes sont créées mais vides :
- `wiki_categories` - Catégories à créer manuellement
- `wiki_subcategories` - Sous-catégories à créer
- `wiki_articles` - Articles de documentation
- `wiki_history` - Historique des modifications
- `wiki_votes` - Votes (like/dislike)
- `wiki_images` - Images uploadées

---

## 🔧 Personnalisation

### Ajouter des données
Toutes ces données peuvent être modifiées via l'interface web :
- **Admin** → Configuration → Ajouter/Modifier/Supprimer

### Ajouter des données via SQL
```sql
-- Ajouter un sujet
INSERT INTO sujets (nom) VALUES ('Nouveau sujet');

-- Ajouter une priorité
INSERT INTO priorites (nom, couleur, niveau)
VALUES ('Urgent', '#ff0000', 5);

-- Ajouter un site
INSERT INTO sites (nom, couleur)
VALUES ('Nouveau site', '#0000ff');

-- Ajouter un statut
INSERT INTO statuts (nom, couleur, category)
VALUES ('En attente pièce', '#ffa500', 'suspendu');
```

---

## 📊 Statistiques des données par défaut

| Catégorie | Nombre d'entrées | Personnalisable |
|-----------|------------------|-----------------|
| Utilisateurs | 1 admin | ✅ Oui |
| Techniciens | 0 | ✅ Oui (via interface) |
| Sujets | 12 | ✅ Oui |
| Priorités | 4 | ✅ Oui |
| Sites | 4 | ✅ Oui |
| Statuts | 9 | ✅ Oui |
| **TOTAL** | **30 entrées** | |

---

## 🚀 Vérification des données

### Vérifier que les données sont présentes

```sql
-- Compter les sujets
SELECT COUNT(*) FROM sujets;
-- Résultat attendu: 12

-- Compter les statuts
SELECT COUNT(*) FROM statuts;
-- Résultat attendu: 9

-- Compter les priorités
SELECT COUNT(*) FROM priorites;
-- Résultat attendu: 4

-- Compter les sites
SELECT COUNT(*) FROM sites;
-- Résultat attendu: 4
```

### Via Docker

```bash
# Vérifier les sujets
docker-compose exec postgres psql -U dispatch_user -d dispatch -c "SELECT nom FROM sujets ORDER BY nom;"

# Vérifier les statuts avec catégories
docker-compose exec postgres psql -U dispatch_user -d dispatch -c "SELECT nom, category FROM statuts ORDER BY category, nom;"
```

---

## ⚠️ Important - Sécurité

### Changer le mot de passe admin

**IMMÉDIATEMENT après le premier démarrage** :

1. Se connecter avec `admin` / `admin`
2. Aller dans le profil
3. Changer le mot de passe
4. Activer la réinitialisation forcée si nécessaire

### Commande SQL directe

```sql
-- Générer un hash bcrypt du nouveau mot de passe via Python
-- puis :
UPDATE users
SET password = 'scrypt:...'
WHERE username = 'admin';
```

---

**Version** : 2.0
**Dernière mise à jour** : 2025-01-26
**Fichier source** : [ensure_db_integrity.py](ensure_db_integrity.py)
