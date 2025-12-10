# Guide de Déploiement - Optimisations Performance

## 🎯 Objectif

Déployer les améliorations de performance pour supporter **50+ utilisateurs simultanés** (vs 3-5 avant).

---

## ✅ Améliorations Appliquées

### Phase 1 : Correctifs Critiques
- ✅ Connection pooling PostgreSQL (5-20 connexions)
- ✅ Workers Gunicorn multiples (1 → 4)
- ✅ Exports PDF/Excel asynchrones
- ✅ Gestion automatique des connexions (flask.g)

### Phase 2 : Optimisations Hautes
- ✅ Cache données de référence (TTL 5 min)
- ✅ Requêtes SQL statistiques optimisées (4 → 1 requête)
- ✅ Cache de templates Jinja activé en production

### Phase 3 : Index SQL
- ✅ 25+ index ajoutés pour optimiser les requêtes
- ✅ Index fulltext pour recherche Wiki
- ✅ Index composites pour requêtes complexes

---

## 📋 Checklist de Déploiement

### Étape 1 : Backup de la Base de Données ⚠️

**IMPORTANT : Toujours faire un backup avant toute migration !**

```bash
# Via Docker
docker-compose exec postgres pg_dump -U dispatch_user dispatch > backup_$(date +%Y%m%d_%H%M%S).sql

# Ou via Makefile
make db-backup
```

**Stockez le backup dans un endroit sûr !**

---

### Étape 2 : Arrêter les Containers

```bash
docker-compose down
```

---

### Étape 3 : Vérifier le Fichier .env

Créez ou mettez à jour votre fichier `.env` avec ces valeurs :

```env
# Flask
FLASK_ENV=production
SECRET_KEY=CHANGEZ_CETTE_CLE_EN_PRODUCTION_UTILISEZ_secrets_token_hex

# PostgreSQL
DB_TYPE=postgresql
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=dispatch
POSTGRES_USER=dispatch_user
POSTGRES_PASSWORD=CHANGEZ_CE_MOT_DE_PASSE

# Connection Pooling (NOUVEAU)
DB_POOL_MIN=5
DB_POOL_MAX=20

# Gunicorn Workers (MODIFIÉ)
GUNICORN_WORKERS=4

# CSRF Protection
WTF_CSRF_ENABLED=true
```

**⚠️ Générer une SECRET_KEY sécurisée** :
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

### Étape 4 : Rebuild les Containers

```bash
# Build sans cache pour forcer la reconstruction
docker-compose build --no-cache

# Démarrer les services
docker-compose up -d
```

---

### Étape 5 : Vérifier le Démarrage

#### 5.1. Vérifier les logs de l'application

```bash
docker-compose logs -f app
```

**Cherchez ces messages** :
```
✓ Connection pool initialisé: 5-20 connexions
```

#### 5.2. Vérifier que les services sont UP

```bash
docker-compose ps
```

Tous les services doivent être **Up (healthy)** :
- dispatch_postgres
- dispatch_manager
- dispatch_nginx

#### 5.3. Tester l'accès web

Ouvrez votre navigateur : http://localhost

Vous devriez voir la page de login.

---

### Étape 6 : Appliquer les Index SQL

**IMPORTANT : Cette étape améliore les performances de 10-100x !**

#### Option A : Via Script Python (Recommandé)

```bash
# Entrer dans le container
docker-compose exec app bash

# Lancer le script
python maintenance/migrations/apply_performance_indexes.py

# Sortir du container
exit
```

#### Option B : Via psql Direct

```bash
# Copier le fichier SQL dans le container
docker cp maintenance/migrations/add_performance_indexes.sql dispatch_postgres:/tmp/

# Se connecter à PostgreSQL
docker-compose exec postgres psql -U dispatch_user -d dispatch

# Dans psql, exécuter :
\i /tmp/add_performance_indexes.sql

# Quitter
\q
```

**Résultat attendu** :
```
✅ Migration terminée:
   - Succès: 40+
   - Erreurs: 0

📈 Statistiques des index:
   - incidents: 12 index
   - wiki_articles: 8 index
   - techniciens: 4 index
   - historique: 3 index
```

---

### Étape 7 : Tests de Validation

#### 7.1. Test de Login
1. Aller sur http://localhost
2. Login : admin / admin (ou vos credentials)
3. Vérifier que la page d'accueil charge en < 1 seconde

#### 7.2. Test d'Export Asynchrone
1. Aller sur "Exporter" (bouton en haut)
2. Sélectionner des techniciens
3. Cliquer "Exporter PDF" ou "Exporter Excel"
4. **Vérifier** :
   - Page de statut avec loader s'affiche immédiatement
   - Barre de progression à 0% puis 100%
   - Téléchargement automatique du fichier
5. **Pendant l'export** :
   - Ouvrir un nouvel onglet
   - Vérifier que la page d'accueil reste responsive
   - **SUCCÈS** : L'export ne bloque plus les autres utilisateurs !

#### 7.3. Test de Performance SQL
```bash
# Se connecter à PostgreSQL
docker-compose exec postgres psql -U dispatch_user -d dispatch

# Vérifier les index
SELECT tablename, indexname FROM pg_indexes WHERE tablename = 'incidents';

# Test de performance d'une requête
EXPLAIN ANALYZE SELECT * FROM incidents WHERE archived=0 ORDER BY id ASC;
```

**Résultat attendu** : Temps d'exécution < 10ms

#### 7.4. Test du Cache
```bash
# Logs de l'application
docker-compose logs -f app

# Recharger la page d'accueil 2 fois
# Vous ne devriez voir qu'UNE seule requête pour priorites/sites/statuts
# La deuxième fois = cache hit
```

---

## 📊 Métriques de Monitoring

### Vérifier les Connexions PostgreSQL

```bash
docker-compose exec postgres psql -U dispatch_user -d dispatch -c "
SELECT count(*) as active_connections
FROM pg_stat_activity
WHERE datname='dispatch';
"
```

**Attendu** : < 20 connexions (limite du pool)

---

### Vérifier l'Utilisation CPU/RAM

```bash
docker stats dispatch_manager
```

**Attendu avec 4 workers** :
- CPU : 30-50% (vs 60-80% avant)
- RAM : 400-600MB (vs 200-400MB avant)

---

### Tester la Charge

#### Test avec Apache Bench (optionnel)

```bash
# Installer ab
sudo apt-get install apache2-utils  # Linux
brew install apache2  # macOS

# Test : 100 requêtes, 20 simultanées
ab -n 100 -c 20 -C "session=VOTRE_SESSION_COOKIE" http://localhost/

# Résultat attendu :
# - Requests per second: > 50/sec
# - Time per request: < 400ms
# - Failed requests: 0
```

---

## 🔧 Troubleshooting

### Problème : "Pool de connexions épuisé"

**Symptôme** : Erreur dans les logs
```
✗ Erreur récupération connexion depuis pool: Pool exhausted
```

**Solution** :
```env
# Dans .env, augmenter la limite
DB_POOL_MAX=30
```

Puis rebuild : `docker-compose up -d --force-recreate app`

---

### Problème : Exports ne se terminent pas

**Symptôme** : Page de statut reste bloquée à "En cours..."

**Diagnostic** :
```bash
# Vérifier les logs
docker-compose logs -f app | grep export
```

**Solutions** :
1. Vérifier que wkhtmltopdf est installé :
   ```bash
   docker-compose exec app which wkhtmltopdf
   ```

2. Vérifier les permissions :
   ```bash
   docker-compose exec app ls -la /app/static/uploads
   ```

3. Redémarrer l'app :
   ```bash
   docker-compose restart app
   ```

---

### Problème : Cache pas invalidé après modification

**Symptôme** : Changements dans configuration pas visibles

**Solution** :
1. Vérifier que `invalidate_reference_cache()` est appelée
2. Forcer invalidation manuelle :
   ```bash
   docker-compose restart app
   ```

---

### Problème : Templates pas en cache

**Symptôme** : Templates recompilés à chaque requête

**Vérification** :
```bash
# Logs de l'app
docker-compose logs app | grep "TEMPLATES_AUTO_RELOAD"
```

**Solution** :
Vérifier que `FLASK_ENV=production` dans `.env`

---

## 🚀 Optimisations Supplémentaires (Optionnel)

### Si vous avez besoin de plus de 50 utilisateurs

#### 1. Augmenter les Workers

```env
# Dans .env
GUNICORN_WORKERS=8

# Ajuster les ressources Docker
# Dans docker-compose.yml
resources:
  limits:
    cpus: '4.0'
    memory: 4G
```

#### 2. Ajouter Redis pour Sessions

```bash
# Installer Flask-Session
pip install Flask-Session redis

# Configurer dans app.py
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_REDIS'] = redis.from_url('redis://redis:6379/0')
```

#### 3. Activer HTTPS avec Certbot

```bash
# Installer Certbot
sudo apt-get install certbot

# Obtenir certificat
sudo certbot certonly --standalone -d votre-domaine.com

# Configurer dans docker-compose.yml
# Décommenter les lignes HTTPS dans nginx.conf
```

---

## 📈 Résultats Attendus

| Métrique | Avant | Après | Gain |
|----------|-------|-------|------|
| **Utilisateurs simultanés** | 3-5 | **50+** | **+1000%** |
| **Workers** | 1 | **4** | +400% |
| **Temps page accueil** | 300-500ms | **50-100ms** | -70% |
| **Requêtes DB/page** | 10-15 | **2-3** | -80% |
| **Temps export PDF** | 10-30s bloquant | **Async** | ∞ |
| **Index SQL** | 8 | **30+** | +275% |
| **Cache hit ratio** | 0% | **95%+** | ∞ |

---

## 📝 Logs Importants à Surveiller

### Au Démarrage

```
✓ Connection pool initialisé: 5-20 connexions
INFO:werkzeug: * Running on http://0.0.0.0:5000
```

### En Production

```bash
# Surveiller les erreurs
docker-compose logs -f app | grep -i error

# Surveiller les exports
docker-compose logs -f app | grep export

# Surveiller les connexions DB
docker-compose logs -f app | grep pool
```

---

## 🎓 Formation Utilisateurs

### Nouvelle Fonctionnalité : Exports Asynchrones

**Expliquez aux utilisateurs** :
1. Les exports ne bloquent plus le système
2. Une page de statut s'affiche pendant la génération
3. Le téléchargement démarre automatiquement
4. Ils peuvent continuer à travailler pendant l'export

---

## ✅ Checklist Finale

- [ ] Backup base de données effectué
- [ ] Fichier .env configuré avec SECRET_KEY unique
- [ ] Containers rebuild (`docker-compose build --no-cache`)
- [ ] Services démarrés (`docker-compose up -d`)
- [ ] Logs vérifiés (connection pool initialisé)
- [ ] Index SQL appliqués
- [ ] Test de login réussi
- [ ] Test d'export asynchrone réussi
- [ ] Monitoring configuré (optionnel)
- [ ] Utilisateurs informés des changements

---

## 📞 Support

Si vous rencontrez des problèmes :

1. Vérifier les logs : `docker-compose logs -f`
2. Vérifier le fichier [PERFORMANCE_IMPROVEMENTS.md](PERFORMANCE_IMPROVEMENTS.md)
3. Consulter le [README.md](README.md) principal

---

**Bonne mise en production ! 🚀**
