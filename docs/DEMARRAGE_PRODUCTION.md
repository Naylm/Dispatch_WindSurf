# 🚀 Guide de Démarrage - Mode Production

## ✅ Pré-requis

- Python 3.7+
- Environnement virtuel activé (`venv`)
- Fichier `.env` configuré
- Base de données `dispatch.db` présente

---

## 🎯 Démarrage Rapide

### Option 1 : Script BAT (Recommandé - Windows)
```bash
.\DEMARRER.bat
```

### Option 2 : Avec Backup Automatique
```bash
.\DEMARRER_AVEC_BACKUP.bat
```

### Option 3 : Commande Python Directe
```bash
python app.py
```

---

## ⚙️ Configuration `.env`

Vérifiez que votre fichier `.env` contient :

```ini
# Flask
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=7f3a8b2c9d1e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a

# Base de données
DATABASE_PATH=dispatch.db

# Serveur
HOST=0.0.0.0
PORT=5000
DEBUG=False
```

---

## 🔧 Vérifications au Démarrage

L'application effectue automatiquement :

1. ✅ Vérification de l'intégrité de la base de données
2. ✅ Création des tables manquantes
3. ✅ Initialisation des données par défaut
4. ✅ Configuration du mode WAL pour SQLite
5. ✅ Optimisation du cache (64MB)

---

## 📊 Indicateurs de Démarrage Réussi

Vous devriez voir dans la console :

```
⚠️  WARNING: SECRET_KEY chargée depuis .env
🔧 Vérification de l'intégrité de la base de données...
✅ Tables existantes vérifiées : 25
📊 Base de données prête - 0 tables créées, 25 tables vérifiées
 * Running on http://0.0.0.0:5000
```

---

## 🌐 Accès à l'Application

Une fois démarré, accédez à :

**URL** : http://localhost:5000

**Identifiants par défaut** :
- Username : `melvin`
- Password : `admin`

---

## ⚠️ Problèmes Courants

### 1. Port 5000 déjà utilisé
```bash
# Trouver le processus
netstat -ano | findstr :5000

# Tuer le processus
taskkill /PID <PID> /F
```

### 2. SECRET_KEY manquante
```
⚠️  WARNING: SECRET_KEY non définie dans .env
```
**Solution** : Copiez la clé générée dans votre `.env`

### 3. Base de données verrouillée
```
sqlite3.OperationalError: database is locked
```
**Solution** : 
- Attendez quelques secondes
- Redémarrez l'application
- Vérifiez qu'aucune autre instance ne tourne

### 4. Module manquant
```
ModuleNotFoundError: No module named 'flask'
```
**Solution** :
```bash
pip install -r requirements.txt
```

---

## 🔄 Arrêt de l'Application

### Arrêt Normal
Appuyez sur `CTRL + C` dans la console

### Arrêt Forcé (Windows)
```bash
# Trouver le processus Python
tasklist | findstr python

# Tuer le processus
taskkill /IM python.exe /F
```

---

## 📝 Maintenance

### Backup de la Base de Données
```bash
python backup_database.py
```

### Vider le Wiki
```bash
.\VIDER_WIKI.bat
```

### Vérifier l'intégrité
```bash
python ensure_db_integrity.py
```

---

## 🎯 Performance Attendue

Avec la configuration actuelle :

| Métrique | Valeur |
|----------|--------|
| Utilisateurs simultanés | **10** ✅ |
| Latence moyenne | < 100ms |
| Temps de démarrage | < 5s |
| Mémoire utilisée | < 500MB |
| CPU moyen | < 30% |

---

## 📞 Support

En cas de problème :

1. Vérifiez le fichier `AUDIT_OPTIMISATIONS.md`
2. Consultez les logs de la console
3. Vérifiez le fichier `.env`
4. Redémarrez l'application

---

## ✨ Optimisations Actives

- ✅ Mode WAL pour SQLite
- ✅ Cache 64MB
- ✅ Timeout 30s
- ✅ SocketIO optimisé
- ✅ Debug désactivé
- ✅ Secret key sécurisée

**L'application est optimisée pour 10 techniciens connectés en permanence.**

---

**Dernière mise à jour** : 17 Novembre 2025  
**Version** : DispatchManager V1.2 Optimized
