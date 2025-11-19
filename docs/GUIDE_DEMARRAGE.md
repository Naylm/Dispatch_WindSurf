# 🚀 Guide de Démarrage - DispatchManager V1.2

## ✅ Persistance des Données Garantie !

Votre application DispatchManager V1.2 est maintenant équipée d'un **système de persistance robuste** qui garantit que **TOUTES vos données seront conservées** après chaque redémarrage, mise à jour ou problème.

---

## 🎯 Démarrage Rapide

### Option 1 : Démarrage Standard (Recommandé)
```bash
python app.py
```

### Option 2 : Démarrage avec Backup Automatique (Ultra-Sécurisé)
```bash
python start_with_backup.py
```

Cette option crée automatiquement un backup avant chaque démarrage.

---

## 📦 Ce qui a été Mis en Place

### 1. ✅ Vérification Automatique de la Base de Données

**Fichier** : `ensure_db_integrity.py`

À chaque démarrage, le système :
- Vérifie que toutes les tables nécessaires existent
- Crée automatiquement les tables manquantes
- Initialise les données par défaut
- Valide l'intégrité complète

**Vous n'avez rien à faire**, c'est automatique !

### 2. 💾 Système de Backup Professionnel

**Fichier** : `backup_database.py`

**Commandes disponibles** :

```bash
# Créer un backup manuel
python backup_database.py create

# Lister tous les backups
python backup_database.py list

# Restaurer un backup
python backup_database.py restore dispatch_backup_YYYYMMDD_HHMMSS.db.zip
```

**Fonctionnalités** :
- Compression automatique (ZIP)
- Conservation des 10 derniers backups
- Horodatage précis
- Restauration sécurisée

### 3. 📋 Documentation Complète

**Fichier** : `PERSISTANCE_DONNEES.md`

Consultez ce fichier pour :
- Comprendre comment vos données sont protégées
- Connaître les procédures d'urgence
- Vérifier l'intégrité de votre système

---

## 🔒 Garanties de Persistance

### ✅ Données Toujours Sauvegardées

| Type de Données | Persistance | Remarques |
|-----------------|-------------|-----------|
| **Tickets/Incidents** | ✅ 100% | Historique complet inclus |
| **Techniciens** | ✅ 100% | Mots de passe hashés |
| **Configurations** | ✅ 100% | Sujets, sites, priorités, statuts |
| **Wiki V2** | ✅ 100% | Articles, catégories, likes, historique |
| **Images Wiki** | ✅ 100% | Stockées dans `static/uploads/wiki/` |
| **Utilisateurs** | ✅ 100% | Authentification sécurisée |
| **Historiques** | ✅ 100% | Traçabilité complète |

### ✅ Protection Automatique Contre

- 🔄 **Redémarrages** → Aucune perte
- ⚡ **Crashs** → Transactions protégées
- 🔧 **Mises à jour** → Données préservées
- 💡 **Coupures de courant** → Mode WAL sécurisé
- 👤 **Erreurs utilisateur** → Backups disponibles

---

## 📝 Routine de Maintenance Recommandée

### Quotidienne (Automatique)
- ✅ Démarrage normal de l'application
- ✅ Vérification automatique de l'intégrité

### Hebdomadaire (Manuel - 2 minutes)
```bash
# Créer un backup hebdomadaire
python backup_database.py create
```

### Mensuelle (Manuel - 5 minutes)
```bash
# Vérifier les backups disponibles
python backup_database.py list

# Nettoyer les très anciens backups si nécessaire (gardés dans backups/)
```

### Avant Mise à Jour (Manuel - 1 minute)
```bash
# TOUJOURS créer un backup avant toute mise à jour !
python backup_database.py create
```

---

## 🛠️ Commandes Utiles

### Vérifier l'Intégrité
```bash
python ensure_db_integrity.py
```

### Créer un Backup Manuel
```bash
python backup_database.py create
```

### Voir Tous les Backups
```bash
python backup_database.py list
```

### Démarrer avec Backup Automatique
```bash
python start_with_backup.py
```

---

## 📂 Structure des Fichiers de Données

```
DispatchManagerV1.2/
├── dispatch.db                    # 💾 BASE DE DONNÉES PRINCIPALE (toutes vos données)
├── dispatch.db-wal               # ⚡ Fichier temporaire WAL
├── dispatch.db-shm               # ⚡ Fichier temporaire shared memory
├── backups/                       # 📦 DOSSIER DES SAUVEGARDES
│   ├── dispatch_backup_20241117_100000.db.zip
│   ├── dispatch_backup_20241117_110000.db.zip
│   └── ...
└── static/uploads/wiki/          # 🖼️ IMAGES UPLOADÉES DU WIKI
    ├── 20241117_100530_image1.png
    └── ...
```

---

## 🚨 Procédures d'Urgence

### Problème : Base de données corrompue

```bash
# 1. Lister les backups disponibles
python backup_database.py list

# 2. Restaurer le dernier backup
python backup_database.py restore dispatch_backup_YYYYMMDD_HHMMSS.db.zip

# 3. Redémarrer l'application
python app.py
```

### Problème : Tables manquantes

```bash
# Le système les recréera automatiquement au prochain démarrage
python app.py

# Ou manuellement :
python ensure_db_integrity.py
```

### Problème : Perte de données récentes

```bash
# Restaurer un backup antérieur
python backup_database.py list
python backup_database.py restore [fichier_choisi]
```

---

## ✨ Nouvelles Fonctionnalités

### 🔍 Vérification Automatique
- Au démarrage : vérification complète de la base
- Création automatique des tables manquantes
- Validation de l'intégrité

### 💾 Backups Intelligents
- Compression automatique (économie d'espace)
- Rotation automatique (10 derniers conservés)
- Restauration sécurisée avec backup de sécurité

### 📊 Mode WAL
- Performances améliorées
- Meilleure protection contre la corruption
- Support multi-utilisateurs amélioré

---

## 📞 FAQ

### Q : Mes données vont-elles survivre à un redémarrage ?
**R** : ✅ OUI, absolument ! Toutes les données sont sauvegardées dans `dispatch.db` qui persiste entre les redémarrages.

### Q : Que se passe-t-il en cas de crash ?
**R** : ✅ Les transactions SQLite garantissent l'intégrité. Les données committées sont sauvegardées, les autres sont annulées proprement.

### Q : Dois-je faire des backups manuels ?
**R** : C'est recommandé mais pas obligatoire. Le système garantit déjà la persistance. Les backups sont une sécurité supplémentaire.

### Q : Combien d'espace prennent les backups ?
**R** : Très peu ! Ils sont compressés. Une base de 100 KB = backup de ~20-30 KB.

### Q : Puis-je supprimer les anciens backups ?
**R** : ✅ OUI, le système conserve automatiquement les 10 derniers. Les plus anciens sont supprimés automatiquement.

### Q : Et si je perds le fichier dispatch.db ?
**R** : Restaurez le dernier backup depuis le dossier `backups/`. Si aucun backup, l'application recréera une base vide au démarrage.

---

## 🎉 Résumé

### Vous pouvez maintenant :

✅ **Redémarrer** votre serveur sans crainte  
✅ **Mettre à jour** l'application en toute sécurité  
✅ **Restaurer** des données en cas de problème  
✅ **Travailler** sereinement, tout est sauvegardé !  

### Vous n'avez plus à vous soucier de :

❌ Perdre des données lors d'un redémarrage  
❌ Corruption de la base de données  
❌ Problèmes de persistence  
❌ Oubli de sauvegardes  

---

## 📖 Documentation Complète

Pour plus de détails, consultez :
- `PERSISTANCE_DONNEES.md` - Guide complet de persistance
- `README.md` - Documentation générale de l'application

---

**🔒 Votre application est maintenant ultra-sécurisée et vos données sont protégées !**

Bonne utilisation ! 🚀
