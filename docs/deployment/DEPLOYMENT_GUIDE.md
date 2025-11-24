# Guide de Déploiement - Dispatch Manager (Version Sécurisée)

**Date**: 24 Novembre 2025
**Version**: 2.0 (Post-Audit de Sécurité)

---

## 🎯 Résumé des Améliorations

### ✅ Corrections Appliquées

| Catégorie | Amélioration | Fichiers Modifiés |
|-----------|-------------|-------------------|
| **Sécurité CSRF** | Protection Flask-WTF ajoutée | `requirements.txt`, `app.py` |
| **Authentification** | Mots de passe hashés obligatoires | `app.py` (lignes 673-717) |
| **SECRET_KEY** | Obligatoire en production | `app.py` (lignes 27-41) |
| **Uploads** | Validation magic bytes, UUID, sans SVG | `wiki_routes_v2.py` |
| **SQL/Auth** | Comparaisons exactes (pas LOWER) | `app.py` (lignes 153, 204, 904, 978) |
| **Performance** | 7 indexes base de données | `add_indexes.sql` |
| **Connexions DB** | Context manager disponible | `db_config.py` (ligne 179) |
| **Docker** | Version pinnée, workers configurables | `Dockerfile` |
| **Nginx** | Headers OWASP, cache optimisé | `nginx.conf` |

---

## 📋 Checklist de Déploiement

### Étape 1: Configuration des Variables d'Environnement

**⚠️ CRITIQUE**: Le fichier `.env` a été créé mais contient des placeholders.

#### 1.1 Générer SECRET_KEY

Depuis le container ou une machine avec Python :
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copiez le résultat et remplacez `CHANGE_ME_GENERATE_WITH_PYTHON_SECRETS` dans `.env`

#### 1.2 Générer POSTGRES_PASSWORD

```bash
python -c "import secrets; print(secrets.token_hex(16))"
```

Remplacez le mot de passe PostgreSQL dans `.env`

#### 1.3 Vérifier le fichier .env

Le fichier `.env` doit ressembler à :
```env
SECRET_KEY=a1b2c3d4e5f6...64_caractères_hexadécimaux
POSTGRES_PASSWORD=f6e5d4c3b2a1...32_caractères_hexadécimaux
GUNICORN_WORKERS=4
WTF_CSRF_ENABLED=true
```

### Étape 2: Arrêter les Containers Existants

```bash
docker-compose down
```

### Étape 3: Rebuild avec No-Cache

```bash
docker-compose build --no-cache
```

**Raisons du rebuild**:
- Nouvelle dépendance: Flask-WTF==1.2.1
- Dockerfile modifié (version pinnée, workers configurables)
- nginx.conf modifié (headers sécurité)

**Temps estimé**: 3-5 minutes

### Étape 4: Démarrer les Containers

```bash
docker-compose up -d
```

### Étape 5: Vérifier les Logs

```bash
# Vérifier que l'app démarre correctement
docker logs dispatch_manager -f

# Ctrl+C pour sortir, puis vérifier PostgreSQL
docker logs dispatch_postgres

# Vérifier Nginx
docker logs dispatch_nginx
```

**Erreurs attendues** :
- ❌ Si SECRET_KEY non définie en production: `RuntimeError: ERREUR CRITIQUE: SECRET_KEY doit être définie`
- ✅ Si tout OK: `🚀 Note editing system initialized`

### Étape 6: Appliquer les Indexes

```bash
docker exec -it dispatch_manager python apply_indexes.py
```

**Sortie attendue** :
```
Connexion à la base de données: postgres:5432/dispatch
Connexion établie avec succès!

Création des indexes de performance...
✓ Exécuté: CREATE INDEX IF NOT EXISTS idx_incidents_collaborateur...
✓ Exécuté: CREATE INDEX IF NOT EXISTS idx_incidents_archived...
...
============================================================
Indexes créés:
============================================================
  • incidents                      → idx_incidents_archived
  • incidents                      → idx_incidents_collaborateur
  • incidents                      → idx_incidents_collab_archived
  • incidents                      → idx_incidents_date_affectation
  • incidents                      → idx_incidents_etat
  • techniciens                    → idx_techniciens_prenom
  • users                          → idx_users_username

✓ Indexes appliqués avec succès!
```

### Étape 7: Tester l'Application

#### 7.1 Test de Connectivité
```bash
curl http://localhost/health
# Devrait retourner: healthy
```

#### 7.2 Vérifier les Headers de Sécurité
```bash
curl -I http://localhost/
```

**Headers attendus** :
```
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

#### 7.3 Test de Connexion

1. Ouvrir http://localhost dans le navigateur
2. Essayer de se connecter avec un compte admin
3. **⚠️ IMPORTANT**: Si vous aviez des mots de passe en clair, la connexion échouera

**Message d'erreur attendu** :
> "Votre mot de passe doit être réinitialisé. Contactez l'administrateur."

#### 7.4 Réinitialiser les Mots de Passe (si nécessaire)

```bash
docker exec -it dispatch_manager python
```

Puis dans Python :
```python
from werkzeug.security import generate_password_hash
from db_config import get_db

db = get_db()

# Pour un user admin
password_hash = generate_password_hash("nouveau_mot_de_passe_admin")
db.execute("UPDATE users SET password=? WHERE username='admin'", (password_hash,))
db.commit()

# Pour un technicien
password_hash = generate_password_hash("nouveau_mot_de_passe_tech")
db.execute("UPDATE techniciens SET password=? WHERE prenom='Hugo'", (password_hash,))
db.commit()

db.close()
exit()
```

---

## 🔍 Vérifications Post-Déploiement

### Check 1: Performance des Requêtes

```bash
docker exec -it dispatch_postgres psql -U dispatch_user -d dispatch
```

```sql
-- Vérifier que les indexes sont utilisés
EXPLAIN ANALYZE SELECT * FROM incidents WHERE collaborateur='Hugo' AND archived=0;

-- Devrait montrer "Index Scan" au lieu de "Seq Scan"
```

### Check 2: Nombre de Connexions

```sql
-- Surveiller les connexions actives
SELECT count(*), state FROM pg_stat_activity
WHERE datname = 'dispatch'
GROUP BY state;
```

**Attendu** : Environ 4-8 connexions (selon GUNICORN_WORKERS)

### Check 3: Workers Gunicorn

```bash
docker exec -it dispatch_manager ps aux | grep gunicorn
```

**Attendu** : 4 workers + 1 master process

---

## ⚠️ Problèmes Connus et Solutions

### Problème 1: RuntimeError SECRET_KEY

**Symptôme** :
```
RuntimeError: ERREUR CRITIQUE: SECRET_KEY doit être définie en production!
```

**Solution** :
1. Vérifier que le fichier `.env` existe
2. Vérifier que `SECRET_KEY` n'est pas vide
3. Rebuild: `docker-compose down && docker-compose up -d`

### Problème 2: "Votre mot de passe doit être réinitialisé"

**Cause** : Mot de passe en clair détecté

**Solution** : Voir section 7.4 ci-dessus

### Problème 3: CSRF Token Missing

**Symptôme** : Erreurs 400 sur les formulaires POST

**Cause** : WTF_CSRF_ENABLED=true mais tokens non ajoutés aux formulaires

**Solution Temporaire** :
Dans `.env`, mettre :
```env
WTF_CSRF_ENABLED=false
```

**Solution Permanente** : Ajouter les tokens CSRF aux templates (future phase)

### Problème 4: Upload d'Images Échoue

**Symptôme** : "Le contenu du fichier ne correspond pas à une image valide"

**Cause** : Validation des magic bytes activée

**Solution** : Vérifier que les fichiers sont de vrais PNG/JPG/GIF/WEBP (pas de faux extensions)

---

## 📊 Monitoring

### Métriques à Surveiller

#### Performance
```bash
# Temps de réponse moyen
docker logs dispatch_nginx | grep "request_time" | tail -100

# Requêtes lentes PostgreSQL
docker exec -it dispatch_postgres psql -U dispatch_user -d dispatch -c "
SELECT query, calls, mean_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;"
```

#### Sécurité
```bash
# Tentatives de connexion échouées
docker logs dispatch_manager | grep "Échec de connexion"

# Requêtes bloquées par CSRF
docker logs dispatch_manager | grep "CSRF"
```

---

## 🔄 Rollback (si nécessaire)

Si des problèmes critiques surviennent :

### Option 1: Rollback Git
```bash
git checkout HEAD~1
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Option 2: Désactiver Temporairement les Nouvelles Fonctionnalités

Dans `.env` :
```env
WTF_CSRF_ENABLED=false
```

Dans `app.py` (commentaire temporaire) :
```python
# csrf = CSRFProtect(app)  # Désactivé temporairement
```

---

## 📝 Changelog Technique

### Fichiers Modifiés

1. **requirements.txt** - Ligne 3 ajoutée: `Flask-WTF==1.2.1`
2. **app.py**:
   - Import CSRFProtect (ligne 6)
   - SECRET_KEY obligatoire (lignes 27-50)
   - Auth sans mot de passe clair (lignes 673-717)
   - Comparaisons SQL exactes (lignes 153, 204, 904, 978)
3. **wiki_routes_v2.py**:
   - SVG retiré (ligne 12)
   - Validation magic bytes (lignes 16-43)
   - UUID pour noms fichiers (ligne 509)
4. **db_config.py**:
   - Context manager `get_db_context()` (lignes 179-200)
5. **Dockerfile**:
   - Version pinnée: `python:3.11.6-slim-bullseye` (ligne 2)
   - Workers configurables (lignes 51-59)
6. **nginx.conf**:
   - Headers OWASP (lignes 39-44)
   - Cache assets statiques (lignes 86-93)
7. **.env.example** - Toutes variables documentées

### Fichiers Créés

1. **add_indexes.sql** - Script SQL des indexes
2. **apply_indexes.py** - Script Python pour appliquer indexes
3. **DB_CONTEXT_MANAGER_GUIDE.md** - Guide context manager
4. **SECURITY_AUDIT_CHANGELOG.md** - Changelog détaillé audit
5. **DEPLOYMENT_GUIDE.md** - Ce guide
6. **.env** - Configuration environnement (à personnaliser!)

---

## ✅ Checklist Finale

- [ ] Variables .env configurées avec secrets uniques
- [ ] Docker rebuild terminé sans erreur
- [ ] Indexes appliqués avec succès
- [ ] Test de connexion OK
- [ ] Headers de sécurité présents
- [ ] Mots de passe réinitialisés (si nécessaire)
- [ ] Performance vérifiée
- [ ] Logs surveillés pendant 24h
- [ ] Backup base de données effectué

---

## 🆘 Support

En cas de problème :

1. **Vérifier les logs** : `docker logs dispatch_manager -f`
2. **Consulter** : `SECURITY_AUDIT_CHANGELOG.md`
3. **Context manager** : `DB_CONTEXT_MANAGER_GUIDE.md`
4. **Rollback** : Voir section ci-dessus

**Prochaines étapes recommandées** :
- Phase 2.3: Optimisation requêtes (JOINs, cache)
- Phase 3.1-3.2: Refactoring et gestion erreurs
- Ajout tokens CSRF dans templates
