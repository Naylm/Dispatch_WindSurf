# 🚀 Guide de Démarrage Rapide - Docker Compose

## 📦 Prérequis

- [Docker](https://www.docker.com/get-started) (version 20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (version 2.0+)
- 2 GB de RAM disponible
- Ports libres : 80 (HTTP), 5432 (PostgreSQL)

## ⚡ Démarrage en 3 étapes

### 1️⃣ Configurer les variables d'environnement

```bash
# Copier le fichier d'exemple
cp .env.example .env

# Générer une clé secrète sécurisée
python -c "import secrets; print(secrets.token_hex(32))"

# Éditer .env et remplacer SECRET_KEY par la clé générée
nano .env  # ou notepad .env sous Windows
```

**Important** : Changez aussi `POSTGRES_PASSWORD` en production !

### 2️⃣ Lancer les conteneurs

```bash
# Construire et démarrer tous les services
docker-compose up -d

# Vérifier que tout fonctionne
docker-compose ps
```

Vous devriez voir 3 conteneurs :
- ✅ `dispatch_postgres` (base de données)
- ✅ `dispatch_manager` (application Flask)
- ✅ `dispatch_nginx` (reverse proxy)

### 3️⃣ Accéder à l'application

Ouvrez votre navigateur : **http://localhost**

Identifiants par défaut :
- Admin : `admin` / `admin`
- Tech : `tech1` / `tech1`

🎉 **C'est tout !** L'application est prête.

---

## 📊 Commandes utiles

### Voir les logs en temps réel
```bash
# Tous les services
docker-compose logs -f

# Un service spécifique
docker-compose logs -f app
docker-compose logs -f postgres
docker-compose logs -f nginx
```

### Arrêter l'application
```bash
# Arrêter sans supprimer les données
docker-compose stop

# Arrêter et supprimer les conteneurs (les données restent dans les volumes)
docker-compose down

# ⚠️ ATTENTION : Supprimer TOUT (conteneurs + volumes + données)
docker-compose down -v
```

### Redémarrer après modifications
```bash
# Si vous modifiez le code Python
docker-compose restart app

# Si vous modifiez nginx.conf
docker-compose restart nginx

# Si vous modifiez Dockerfile ou docker-compose.yml
docker-compose up -d --build
```

### Accéder à la base de données
```bash
# Via Docker exec
docker exec -it dispatch_postgres psql -U dispatch_user -d dispatch

# Ou activer pgAdmin (décommenter dans docker-compose.yml)
# Puis accéder à http://localhost:5050
```

### Sauvegarder la base de données
```bash
# Backup
docker exec dispatch_postgres pg_dump -U dispatch_user dispatch > backup_$(date +%Y%m%d).sql

# Restore
docker exec -i dispatch_postgres psql -U dispatch_user dispatch < backup_20250126.sql
```

---

## 🔧 Personnalisation

### Changer le nombre de workers Gunicorn
```bash
# Dans .env
GUNICORN_WORKERS=2
```

### Activer HTTPS avec certificat SSL
1. Placez vos certificats dans `./ssl/`
2. Décommentez les lignes HTTPS dans `docker-compose.yml`
3. Modifiez `nginx.conf` pour activer le port 443

### Activer pgAdmin (interface web PostgreSQL)
Décommentez la section `pgadmin` dans `docker-compose.yml` puis :
```bash
docker-compose up -d pgadmin
```
Accédez à http://localhost:5050 (admin@dispatch.local / admin)

---

## 🐛 Dépannage

### L'application ne démarre pas
```bash
# Vérifier les logs
docker-compose logs app

# Vérifier que PostgreSQL est prêt
docker-compose logs postgres | grep "ready to accept connections"
```

### Port 80 déjà utilisé
Modifiez dans `docker-compose.yml` :
```yaml
nginx:
  ports:
    - "8080:80"  # Utiliser le port 8080 au lieu de 80
```

### Réinitialiser complètement
```bash
docker-compose down -v
docker-compose up -d --build
```

---

## 📚 Documentation complète

Consultez [README.md](README.md) pour :
- Architecture détaillée
- Variables d'environnement complètes
- Fonctionnalités avancées
- Monitoring et performance
- Sécurité en production

---

## 💡 Prochaines étapes

1. ✅ Changez les mots de passe par défaut
2. ✅ Configurez la SECRET_KEY
3. ✅ Créez vos techniciens et utilisateurs
4. ✅ Configurez les sites, priorités et statuts
5. ✅ Importez vos données existantes (si applicable)
6. 📖 Explorez le Wiki pour documenter vos procédures

**Bon dispatch ! 🎯**
