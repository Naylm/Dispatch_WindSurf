# Guide de DÃ©ploiement - Optimisations Performance

## ðŸŽ¯ Objectif

DÃ©ployer les amÃ©liorations de performance pour supporter **50+ utilisateurs simultanÃ©s** (vs 3-5 avant).

---

## âœ… AmÃ©liorations AppliquÃ©es

### Phase 1 : Correctifs Critiques
- âœ… Connection pooling PostgreSQL (5-20 connexions)
- âœ… Workers Gunicorn multiples (1 â†’ 4)
- âœ… Exports PDF/Excel asynchrones
- âœ… Gestion automatique des connexions (flask.g)

### Phase 2 : Optimisations Hautes
- âœ… Cache donnÃ©es de rÃ©fÃ©rence (TTL 5 min)
- âœ… RequÃªtes SQL statistiques optimisÃ©es (4 â†’ 1 requÃªte)
- âœ… Cache de templates Jinja activÃ© en production

### Phase 3 : Index SQL
- âœ… 25+ index ajoutÃ©s pour optimiser les requÃªtes
- âœ… Index fulltext pour recherche Wiki
- âœ… Index composites pour requÃªtes complexes

---

## ðŸ“‹ Checklist de DÃ©ploiement

### Ã‰tape 1 : Backup de la Base de DonnÃ©es âš ï¸

**IMPORTANT : Toujours faire un backup avant toute migration !**

```bash
# Via Docker
docker-compose exec postgres pg_dump -U dispatch_user dispatch > backup_$(date +%Y%m%d_%H%M%S).sql

# Ou via Makefile
make db-backup
```

**Stockez le backup dans un endroit sÃ»r !**

---

### Ã‰tape 2 : ArrÃªter les Containers

```bash
docker-compose down
```

---

### Ã‰tape 3 : VÃ©rifier le Fichier .env

CrÃ©ez ou mettez Ã  jour votre fichier `.env` avec ces valeurs :

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

# Gunicorn Workers (MODIFIÃ‰)
GUNICORN_WORKERS=4

# CSRF Protection
WTF_CSRF_ENABLED=true
```

**âš ï¸ GÃ©nÃ©rer une SECRET_KEY sÃ©curisÃ©e** :
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

### Ã‰tape 4 : Rebuild les Containers

```bash
# Build sans cache pour forcer la reconstruction
docker-compose build --no-cache

# DÃ©marrer les services
docker-compose up -d
```

---

### Ã‰tape 5 : VÃ©rifier le DÃ©marrage

#### 5.1. VÃ©rifier les logs de l'application

```bash
docker-compose logs -f app
```

**Cherchez ces messages** :
```
âœ“ Connection pool initialisÃ©: 5-20 connexions
```

#### 5.2. VÃ©rifier que les services sont UP

```bash
docker-compose ps
```

Tous les services doivent Ãªtre **Up (healthy)** :
- dispatch_postgres
- dispatch_manager
- dispatch_nginx

#### 5.3. Tester l'accÃ¨s web

Ouvrez votre navigateur : http://localhost

Vous devriez voir la page de login.

---

### Ã‰tape 6 : Appliquer les Index SQL

**IMPORTANT : Cette Ã©tape amÃ©liore les performances de 10-100x !**

#### Option A : Via Script Python (RecommandÃ©)

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

# Se connecter Ã  PostgreSQL
docker-compose exec postgres psql -U dispatch_user -d dispatch

# Dans psql, exÃ©cuter :
\i /tmp/add_performance_indexes.sql

# Quitter
\q
```

**RÃ©sultat attendu** :
```
âœ… Migration terminÃ©e:
   - SuccÃ¨s: 40+
   - Erreurs: 0

ðŸ“ˆ Statistiques des index:
   - incidents: 12 index
   - wiki_articles: 8 index
   - techniciens: 4 index
   - historique: 3 index
```

---

### Ã‰tape 7 : Tests de Validation

#### 7.1. Test de Login
1. Aller sur http://localhost
2. Login : compte bootstrap configure dans `.env` (ou vos credentials)
3. VÃ©rifier que la page d'accueil charge en < 1 seconde

#### 7.2. Test d'Export Asynchrone
1. Aller sur "Exporter" (bouton en haut)
2. SÃ©lectionner des techniciens
3. Cliquer "Exporter PDF" ou "Exporter Excel"
4. **VÃ©rifier** :
   - Page de statut avec loader s'affiche immÃ©diatement
   - Barre de progression Ã  0% puis 100%
   - TÃ©lÃ©chargement automatique du fichier
5. **Pendant l'export** :
   - Ouvrir un nouvel onglet
   - VÃ©rifier que la page d'accueil reste responsive
   - **SUCCÃˆS** : L'export ne bloque plus les autres utilisateurs !

#### 7.3. Test de Performance SQL
```bash
# Se connecter Ã  PostgreSQL
docker-compose exec postgres psql -U dispatch_user -d dispatch

# VÃ©rifier les index
SELECT tablename, indexname FROM pg_indexes WHERE tablename = 'incidents';

# Test de performance d'une requÃªte
EXPLAIN ANALYZE SELECT * FROM incidents WHERE archived=0 ORDER BY id ASC;
```

**RÃ©sultat attendu** : Temps d'exÃ©cution < 10ms

#### 7.4. Test du Cache
```bash
# Logs de l'application
docker-compose logs -f app

# Recharger la page d'accueil 2 fois
# Vous ne devriez voir qu'UNE seule requÃªte pour priorites/sites/statuts
# La deuxiÃ¨me fois = cache hit
```

---

## ðŸ“Š MÃ©triques de Monitoring

### VÃ©rifier les Connexions PostgreSQL

```bash
docker-compose exec postgres psql -U dispatch_user -d dispatch -c "
SELECT count(*) as active_connections
FROM pg_stat_activity
WHERE datname='dispatch';
"
```

**Attendu** : < 20 connexions (limite du pool)

---

### VÃ©rifier l'Utilisation CPU/RAM

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

# Test : 100 requÃªtes, 20 simultanÃ©es
ab -n 100 -c 20 -C "session=VOTRE_SESSION_COOKIE" http://localhost/

# RÃ©sultat attendu :
# - Requests per second: > 50/sec
# - Time per request: < 400ms
# - Failed requests: 0
```

---

## ðŸ”§ Troubleshooting

### ProblÃ¨me : "Pool de connexions Ã©puisÃ©"

**SymptÃ´me** : Erreur dans les logs
```
âœ— Erreur rÃ©cupÃ©ration connexion depuis pool: Pool exhausted
```

**Solution** :
```env
# Dans .env, augmenter la limite
DB_POOL_MAX=30
```

Puis rebuild : `docker-compose up -d --force-recreate app`

---

### ProblÃ¨me : Exports ne se terminent pas

**SymptÃ´me** : Page de statut reste bloquÃ©e Ã  "En cours..."

**Diagnostic** :
```bash
# VÃ©rifier les logs
docker-compose logs -f app | grep export
```

**Solutions** :
1. VÃ©rifier que wkhtmltopdf est installÃ© :
   ```bash
   docker-compose exec app which wkhtmltopdf
   ```

2. VÃ©rifier les permissions :
   ```bash
   docker-compose exec app ls -la /app/static/uploads
   ```

3. RedÃ©marrer l'app :
   ```bash
   docker-compose restart app
   ```

---

### ProblÃ¨me : Cache pas invalidÃ© aprÃ¨s modification

**SymptÃ´me** : Changements dans configuration pas visibles

**Solution** :
1. VÃ©rifier que `invalidate_reference_cache()` est appelÃ©e
2. Forcer invalidation manuelle :
   ```bash
   docker-compose restart app
   ```

---

### ProblÃ¨me : Templates pas en cache

**SymptÃ´me** : Templates recompilÃ©s Ã  chaque requÃªte

**VÃ©rification** :
```bash
# Logs de l'app
docker-compose logs app | grep "TEMPLATES_AUTO_RELOAD"
```

**Solution** :
VÃ©rifier que `FLASK_ENV=production` dans `.env`

---

## ðŸš€ Optimisations SupplÃ©mentaires (Optionnel)

### Si vous avez besoin de plus de 50 utilisateurs

#### 1. Augmenter les Workers

```env
# Dans .env
GUNICORN_WORKERS=2

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
# DÃ©commenter les lignes HTTPS dans nginx.conf
```

---

## ðŸ“ˆ RÃ©sultats Attendus

| MÃ©trique | Avant | AprÃ¨s | Gain |
|----------|-------|-------|------|
| **Utilisateurs simultanÃ©s** | 3-5 | **50+** | **+1000%** |
| **Workers** | 1 | **4** | +400% |
| **Temps page accueil** | 300-500ms | **50-100ms** | -70% |
| **RequÃªtes DB/page** | 10-15 | **2-3** | -80% |
| **Temps export PDF** | 10-30s bloquant | **Async** | âˆž |
| **Index SQL** | 8 | **30+** | +275% |
| **Cache hit ratio** | 0% | **95%+** | âˆž |

---

## ðŸ“ Logs Importants Ã  Surveiller

### Au DÃ©marrage

```
âœ“ Connection pool initialisÃ©: 5-20 connexions
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

## ðŸŽ“ Formation Utilisateurs

### Nouvelle FonctionnalitÃ© : Exports Asynchrones

**Expliquez aux utilisateurs** :
1. Les exports ne bloquent plus le systÃ¨me
2. Une page de statut s'affiche pendant la gÃ©nÃ©ration
3. Le tÃ©lÃ©chargement dÃ©marre automatiquement
4. Ils peuvent continuer Ã  travailler pendant l'export

---

## âœ… Checklist Finale

- [ ] Backup base de donnÃ©es effectuÃ©
- [ ] Fichier .env configurÃ© avec SECRET_KEY unique
- [ ] Containers rebuild (`docker-compose build --no-cache`)
- [ ] Services dÃ©marrÃ©s (`docker-compose up -d`)
- [ ] Logs vÃ©rifiÃ©s (connection pool initialisÃ©)
- [ ] Index SQL appliquÃ©s
- [ ] Test de login rÃ©ussi
- [ ] Test d'export asynchrone rÃ©ussi
- [ ] Monitoring configurÃ© (optionnel)
- [ ] Utilisateurs informÃ©s des changements

---

## ðŸ“ž Support

Si vous rencontrez des problÃ¨mes :

1. VÃ©rifier les logs : `docker-compose logs -f`
2. VÃ©rifier le fichier [PERFORMANCE_IMPROVEMENTS.md](PERFORMANCE_IMPROVEMENTS.md)
3. Consulter le [README.md](README.md) principal

---

**Bonne mise en production ! ðŸš€**

