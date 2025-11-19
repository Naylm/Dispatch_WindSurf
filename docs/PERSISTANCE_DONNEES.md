# 🔒 Guide de Persistance des Données - DispatchManager V1.2

## 📋 Vue d'ensemble

Ce document explique comment **toutes vos données sont sauvegardées et persistent** lors des redémarrages, mises à jour ou problèmes du système.

## ✅ Garanties de Persistance

### 🎯 Données Persistées Automatiquement

Toutes les données suivantes sont **automatiquement et définitivement sauvegardées** dans la base de données SQLite (`dispatch.db`) :

#### 📝 **Tickets et Incidents**
- ✓ Tous les tickets créés, modifiés ou supprimés
- ✓ Historique complet des modifications
- ✓ Notes et localisations
- ✓ États et validations

#### 👥 **Techniciens**
- ✓ Liste complète des techniciens
- ✓ Rôles et permissions
- ✓ États actif/inactif
- ✓ Mots de passe (hashés de manière sécurisée)

#### ⚙️ **Configurations**
- ✓ Sujets personnalisés
- ✓ Priorités et leurs couleurs
- ✓ Sites et leurs couleurs
- ✓ Statuts personnalisés

#### 📚 **Wiki V2**
- ✓ Catégories et sous-catégories
- ✓ Articles avec tout leur contenu
- ✓ Historique des modifications d'articles
- ✓ Likes/Dislikes des utilisateurs
- ✓ Compteurs de vues
- ✓ Images uploadées et leurs métadonnées

#### 👤 **Utilisateurs**
- ✓ Comptes utilisateurs
- ✓ Rôles et permissions
- ✓ Authentification sécurisée

---

## 🔧 Système de Persistance

### 1. **Vérification Automatique au Démarrage**

À chaque démarrage de l'application, le script `ensure_db_integrity.py` :

1. ✅ Vérifie que toutes les tables nécessaires existent
2. ✅ Crée automatiquement les tables manquantes
3. ✅ Initialise les données par défaut si nécessaire
4. ✅ Valide l'intégrité de la base de données
5. ✅ Active le mode WAL (Write-Ahead Logging) pour les performances

**Résultat** : Même après une mise à jour ou un crash, toutes vos données sont préservées !

### 2. **Mode WAL (Write-Ahead Logging)**

La base de données utilise le mode WAL qui offre :

- 🚀 **Performances améliorées** : Écritures plus rapides
- 🔒 **Meilleure sécurité** : Moins de risques de corruption
- 📊 **Lectures concurrentes** : Plusieurs utilisateurs simultanés
- 💾 **Persistance garantie** : Les commits sont immédiats

### 3. **Commits Systématiques**

Chaque opération de modification (ajout, suppression, mise à jour) :

1. Est exécutée dans une transaction
2. Est immédiatement committée (`db.commit()`)
3. Est donc **définitivement sauvegardée** sur le disque

**Code de protection transactionnelle utilisé** :
```python
try:
    db.execute("BEGIN IMMEDIATE")
    db.execute("UPDATE incidents SET ...")
    db.commit()
except sqlite3.OperationalError:
    db.rollback()
```

---

## 💾 Système de Backup Automatique

### Script de Backup : `backup_database.py`

#### **Créer un backup manuel**
```bash
python backup_database.py create
```

#### **Lister tous les backups**
```bash
python backup_database.py list
```

#### **Restaurer un backup**
```bash
python backup_database.py restore dispatch_backup_20231117_143000.db.zip
```

### Caractéristiques du système de backup

- 📦 **Compression automatique** : Les backups sont compressés en ZIP
- 🗂️ **Gestion intelligente** : Conservation des 10 derniers backups
- 🔒 **Sécurité** : Backup de sécurité avant restauration
- 📅 **Horodatage** : Noms de fichiers avec date et heure
- 💾 **Économie d'espace** : Suppression automatique des vieux backups

### Recommandations de Backup

| Fréquence | Commande | Quand |
|-----------|----------|-------|
| **Quotidien** | `python backup_database.py` | Chaque soir |
| **Avant maj** | `python backup_database.py` | Avant toute mise à jour |
| **Hebdomadaire** | `python backup_database.py` | Chaque dimanche |

---

## 🛡️ Protection contre la Perte de Données

### Ce qui est protégé :

✅ **Redémarrage du serveur** → Toutes les données persistent  
✅ **Crash de l'application** → Aucune perte (transactions)  
✅ **Mise à jour du code** → Données préservées  
✅ **Coupure de courant** → Mode WAL protège les données  
✅ **Erreur utilisateur** → Backups disponibles  

### Ce qui n'est PAS persisté :

❌ **Sessions utilisateurs** → Nécessite une nouvelle connexion après redémarrage  
❌ **Uploads en cours** → Doivent être complétés avant arrêt  

---

## 📂 Fichiers Importants

| Fichier | Description | Persistance |
|---------|-------------|-------------|
| `dispatch.db` | **Base de données principale** | ✅ TOUTES les données |
| `dispatch.db-wal` | Fichier WAL (temporaire) | ⚠️ Temporaire |
| `dispatch.db-shm` | Shared memory (temporaire) | ⚠️ Temporaire |
| `backups/` | **Dossier de sauvegardes** | ✅ Backups compressés |
| `static/uploads/wiki/` | **Images Wiki uploadées** | ✅ Fichiers permanents |

---

## 🔍 Vérification de l'Intégrité

### Vérifier manuellement l'intégrité
```bash
python ensure_db_integrity.py
```

### Résultat attendu :
```
🔍 Vérification de l'intégrité de la base de données...

============================================================
📊 RÉSUMÉ DE LA VÉRIFICATION DE LA BASE DE DONNÉES
============================================================

✓ 14 table(s) vérifiée(s) (déjà existantes):
   • users
   • techniciens
   • incidents
   • historique
   • sujets
   • priorites
   • sites
   • statuts
   • wiki_categories
   • wiki_subcategories
   • wiki_articles
   • wiki_history
   • wiki_votes
   • wiki_images

🔒 Intégrité de la base: ok
📁 Fichier: C:\...\dispatch.db
💾 Taille: 96.00 KB

✅ La base de données est prête et toutes les données seront persistées!
============================================================
```

---

## 🚨 Procédures d'Urgence

### En cas de problème

1. **Base de données corrompue** :
   ```bash
   python backup_database.py list
   python backup_database.py restore [fichier_backup]
   ```

2. **Tables manquantes** :
   ```bash
   python ensure_db_integrity.py
   ```
   Le script recrée automatiquement les tables manquantes.

3. **Perte de données récentes** :
   - Restaurer le dernier backup
   - Les backups sont dans `backups/`
   - Triés par date (plus récent = plus grand nombre)

---

## 📝 Checklist de Sécurité

Avant toute opération critique :

- [ ] Vérifier que `dispatch.db` existe
- [ ] Créer un backup manuel
- [ ] Vérifier l'espace disque disponible
- [ ] Tester la restauration d'un backup (optionnel)

---

## 🎯 Résumé

### ✅ Ce que vous devez savoir :

1. **Toutes vos données sont automatiquement sauvegardées** dans `dispatch.db`
2. **Aucune action manuelle n'est requise** pour la persistance normale
3. **Les backups réguliers sont recommandés** mais pas obligatoires
4. **En cas de problème**, vous pouvez restaurer un backup
5. **Le système vérifie l'intégrité** à chaque démarrage

### 🔒 Garantie :

**Après un redémarrage, vous retrouverez exactement :**
- Tous vos tickets et incidents
- Tous vos techniciens
- Toutes vos configurations (sujets, sites, priorités, statuts)
- Tous vos articles Wiki
- Tous les historiques et modifications
- Toutes vos images uploadées

**RIEN ne sera perdu !** 🎉

---

## 📞 Support

En cas de question ou problème :
1. Vérifier ce document
2. Lancer `python ensure_db_integrity.py`
3. Consulter les logs de l'application
4. Vérifier la taille de `dispatch.db` (ne doit pas être 0)

---

**Dernière mise à jour** : 17 Novembre 2024  
**Version** : 1.2
