# 🔧 Guide de dépannage - Dispatch Manager

## 🚫 Problèmes de connexion

### Symptôme : "Impossible de se connecter avec n'importe quel compte"

#### **Solution 1 : Diagnostic complet**

```powershell
# Via PowerShell
.\dispatch.ps1 debug-login

# Ou via Docker directement
docker-compose exec app python debug_login.py
```

Ce script affiche :
- ✅ Liste de tous les comptes (admin + techniciens)
- ✅ État des mots de passe (hashé ou non)
- ✅ Test automatique des mots de passe courants
- ✅ Suggestions de correction

#### **Solution 2 : Réinitialiser le mot de passe admin**

```powershell
# Via PowerShell
.\dispatch.ps1 reset-admin

# Ou via Docker
docker-compose exec app python reset_admin_password.py
```

**Résultat** : Crée ou réinitialise le compte admin avec :
- Username: `admin`
- Password: `admin`

#### **Solution 3 : Vérifier que l'application est démarrée**

```powershell
# Vérifier l'état
.\dispatch.ps1 status

# Voir les logs
.\dispatch.ps1 logs-app
```

---

## 🗄️ Problèmes de base de données

### Symptôme : "Table xxx does not exist"

#### **Solution : Forcer la création/réparation du schéma**

```powershell
# Via conteneur
docker-compose exec app python ensure_db_integrity.py

# Vérifier le schéma
docker-compose exec app python verify_database.py
```

### Symptôme : "Connection refused" PostgreSQL

#### **Vérifications :**

```powershell
# Le conteneur PostgreSQL est-il démarré ?
docker-compose ps postgres

# Voir les logs PostgreSQL
.\dispatch.ps1 logs-db

# Redémarrer PostgreSQL
docker-compose restart postgres
```

---

## 🐳 Problèmes Docker

### Symptôme : "Port 80 already in use"

**Solution** : Changer le port dans [docker-compose.yml](docker-compose.yml#L92)

```yaml
nginx:
  ports:
    - "8080:80"  # Au lieu de 80:80
```

Puis accéder à : http://localhost:8080

### Symptôme : "Cannot connect to Docker daemon"

**Solutions** :
1. Démarrer Docker Desktop
2. Vérifier que Docker est en cours : `docker version`
3. Redémarrer Docker Desktop

---

## 🔐 Problèmes de sécurité

### Symptôme : "CSRF token missing"

**Cause** : Cookies désactivés ou navigateur en mode privé

**Solution** :
1. Activer les cookies
2. Utiliser mode normal (pas incognito)
3. Vider le cache navigateur

### Symptôme : "Votre mot de passe doit être réinitialisé"

**Cause** : Mot de passe non hashé en base

**Solution** : Utiliser le script de reset

```powershell
.\dispatch.ps1 reset-admin
```

---

## 📊 Problèmes de données

### Symptôme : "Aucun statut/sujet disponible"

**Cause** : Données par défaut non insérées

**Solution** :

```powershell
# Réinitialiser les données par défaut
docker-compose exec app python ensure_db_integrity.py

# Vérifier les données
docker-compose exec postgres psql -U dispatch_user -d dispatch -c "
  SELECT 'Sujets' as table, COUNT(*) FROM sujets
  UNION SELECT 'Statuts', COUNT(*) FROM statuts
  UNION SELECT 'Priorités', COUNT(*) FROM priorites;
"
```

**Résultat attendu** :
- Sujets : 12
- Statuts : 9
- Priorités : 4

---

## 🌐 Problèmes réseau

### Symptôme : "502 Bad Gateway"

**Causes possibles** :
1. Application Flask non démarrée
2. Nginx ne peut pas communiquer avec Flask

**Diagnostic** :

```powershell
# Vérifier que l'app Flask répond
docker-compose exec app curl -f http://localhost:5000/

# Logs de l'application
.\dispatch.ps1 logs-app

# Redémarrer les services
docker-compose restart app nginx
```

### Symptôme : "Connection timeout"

**Solution** : Vérifier le réseau Docker

```powershell
# Lister les réseaux
docker network ls | Select-String "dispatch"

# Inspecter le réseau
docker network inspect dispatchdockerworking_dispatch_network
```

---

## 🔄 Réinitialisation complète

### Option 1 : Reset complet (GARDE LES DONNÉES)

```powershell
# Arrêter
.\dispatch.ps1 down

# Reconstruire
.\dispatch.ps1 rebuild
```

### Option 2 : Reset TOTAL (SUPPRIME TOUT)

```powershell
# ⚠️ ATTENTION : Supprime TOUTES les données
.\dispatch.ps1 clean

# Réinstaller
.\dispatch.ps1 init
```

---

## 📝 Commandes de diagnostic utiles

### Vérifier la base de données

```powershell
# Shell PostgreSQL
docker-compose exec postgres psql -U dispatch_user -d dispatch

# Lister les tables
\dt

# Compter les utilisateurs
SELECT COUNT(*) FROM users;

# Voir les admins
SELECT username, role FROM users;

# Voir les techniciens
SELECT prenom, role, actif FROM techniciens;
```

### Vérifier les logs

```powershell
# Tous les logs
.\dispatch.ps1 logs

# Seulement l'application
.\dispatch.ps1 logs-app

# Seulement PostgreSQL
.\dispatch.ps1 logs-db

# Seulement Nginx
.\dispatch.ps1 logs-nginx
```

### Accéder au conteneur

```powershell
# Shell dans le conteneur Flask
.\dispatch.ps1 shell

# Shell PostgreSQL
.\dispatch.ps1 shell-db
```

---

## 🆘 Checklist de dépannage

Suivez ces étapes dans l'ordre :

- [ ] **1. Docker est-il démarré ?**
  ```powershell
  docker version
  ```

- [ ] **2. Les conteneurs tournent-ils ?**
  ```powershell
  .\dispatch.ps1 ps
  ```

- [ ] **3. La base de données répond-elle ?**
  ```powershell
  docker-compose exec postgres pg_isready -U dispatch_user
  ```

- [ ] **4. L'application Flask répond-elle ?**
  ```powershell
  docker-compose exec app curl -f http://localhost:5000/
  ```

- [ ] **5. Le compte admin existe-t-il ?**
  ```powershell
  .\dispatch.ps1 debug-login
  ```

- [ ] **6. Les données par défaut sont-elles présentes ?**
  ```powershell
  docker-compose exec app python verify_database.py
  ```

---

## 💡 Problèmes fréquents et solutions rapides

| Problème | Solution rapide |
|----------|----------------|
| Impossible de se connecter | `.\dispatch.ps1 reset-admin` |
| Erreur de base de données | `docker-compose exec app python ensure_db_integrity.py` |
| Port 80 occupé | Modifier `docker-compose.yml` → `8080:80` |
| 502 Bad Gateway | `docker-compose restart app nginx` |
| Données manquantes | `docker-compose exec app python ensure_db_integrity.py` |

---

## 📞 Support

### Logs à fournir en cas de problème :

```powershell
# Capturer tous les logs
.\dispatch.ps1 logs > logs_dispatch.txt

# Vérifier la configuration
.\dispatch.ps1 status > status_dispatch.txt

# Diagnostiquer les comptes
docker-compose exec app python debug_login.py > debug_login.txt
```

---

**Dernière mise à jour** : 2025-01-26
