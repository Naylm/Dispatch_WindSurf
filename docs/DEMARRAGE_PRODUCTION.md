# ðŸš€ Guide de DÃ©marrage - Mode Production

## âœ… PrÃ©-requis

- Python 3.7+
- Environnement virtuel activÃ© (`venv`)
- Fichier `.env` configurÃ©
- Base de donnÃ©es `dispatch.db` prÃ©sente

---

## ðŸŽ¯ DÃ©marrage Rapide

### Option 1 : Script BAT (RecommandÃ© - Windows)
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

## âš™ï¸ Configuration `.env`

VÃ©rifiez que votre fichier `.env` contient :

```ini
# Flask
FLASK_APP=app.py
FLASK_ENV=production
SECRET_KEY=7f3a8b2c9d1e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a

# Base de donnÃ©es
DATABASE_PATH=dispatch.db

# Serveur
HOST=0.0.0.0
PORT=5000
DEBUG=False
```

---

## ðŸ”§ VÃ©rifications au DÃ©marrage

L'application effectue automatiquement :

1. âœ… VÃ©rification de l'intÃ©gritÃ© de la base de donnÃ©es
2. âœ… CrÃ©ation des tables manquantes
3. âœ… Initialisation des donnÃ©es par dÃ©faut
4. âœ… Configuration du mode WAL pour SQLite
5. âœ… Optimisation du cache (64MB)

---

## ðŸ“Š Indicateurs de DÃ©marrage RÃ©ussi

Vous devriez voir dans la console :

```
âš ï¸  WARNING: SECRET_KEY chargÃ©e depuis .env
ðŸ”§ VÃ©rification de l'intÃ©gritÃ© de la base de donnÃ©es...
âœ… Tables existantes vÃ©rifiÃ©es : 25
ðŸ“Š Base de donnÃ©es prÃªte - 0 tables crÃ©Ã©es, 25 tables vÃ©rifiÃ©es
 * Running on http://0.0.0.0:5000
```

---

## ðŸŒ AccÃ¨s Ã  l'Application

Une fois dÃ©marrÃ©, accÃ©dez Ã  :

**URL** : http://localhost:5000

**Compte initial** :
- definir `BOOTSTRAP_ADMIN_USERNAME` et `BOOTSTRAP_ADMIN_PASSWORD` dans `.env`
- le compte est force de changer son mot de passe a la premiere connexion

---

## âš ï¸ ProblÃ¨mes Courants

### 1. Port 5000 dÃ©jÃ  utilisÃ©
```bash
# Trouver le processus
netstat -ano | findstr :5000

# Tuer le processus
taskkill /PID <PID> /F
```

### 2. SECRET_KEY manquante
```
âš ï¸  WARNING: SECRET_KEY non dÃ©finie dans .env
```
**Solution** : Copiez la clÃ© gÃ©nÃ©rÃ©e dans votre `.env`

### 3. Base de donnÃ©es verrouillÃ©e
```
sqlite3.OperationalError: database is locked
```
**Solution** : 
- Attendez quelques secondes
- RedÃ©marrez l'application
- VÃ©rifiez qu'aucune autre instance ne tourne

### 4. Module manquant
```
ModuleNotFoundError: No module named 'flask'
```
**Solution** :
```bash
pip install -r requirements.txt
```

---

## ðŸ”„ ArrÃªt de l'Application

### ArrÃªt Normal
Appuyez sur `CTRL + C` dans la console

### ArrÃªt ForcÃ© (Windows)
```bash
# Trouver le processus Python
tasklist | findstr python

# Tuer le processus
taskkill /IM python.exe /F
```

---

## ðŸ“ Maintenance

### Backup de la Base de DonnÃ©es
```bash
python backup_database.py
```

### Vider le Wiki
```bash
.\VIDER_WIKI.bat
```

### VÃ©rifier l'intÃ©gritÃ©
```bash
python ensure_db_integrity.py
```

---

## ðŸŽ¯ Performance Attendue

Avec la configuration actuelle :

| MÃ©trique | Valeur |
|----------|--------|
| Utilisateurs simultanÃ©s | **10** âœ… |
| Latence moyenne | < 100ms |
| Temps de dÃ©marrage | < 5s |
| MÃ©moire utilisÃ©e | < 500MB |
| CPU moyen | < 30% |

---

## ðŸ“ž Support

En cas de problÃ¨me :

1. VÃ©rifiez le fichier `AUDIT_OPTIMISATIONS.md`
2. Consultez les logs de la console
3. VÃ©rifiez le fichier `.env`
4. RedÃ©marrez l'application

---

## âœ¨ Optimisations Actives

- âœ… Mode WAL pour SQLite
- âœ… Cache 64MB
- âœ… Timeout 30s
- âœ… SocketIO optimisÃ©
- âœ… Debug dÃ©sactivÃ©
- âœ… Secret key sÃ©curisÃ©e

**L'application est optimisÃ©e pour 10 techniciens connectÃ©s en permanence.**

---

**DerniÃ¨re mise Ã  jour** : 17 Novembre 2025  
**Version** : DispatchManager V1.2 Optimized

